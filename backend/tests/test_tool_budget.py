"""Tests for the per-question tool-call budget in the agent node.

A fake model stands in for the real LLM, so these run without API calls.
"""

import asyncio

import groq
import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent import graph
from app.config import MAX_TOOL_ROUNDS

_REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
_REFUSED_DETAILS = {
    "message": "Tool choice is none, but model called a tool",
    "type": "invalid_request_error",
    "code": "tool_use_failed",
}


def _refused_400() -> groq.BadRequestError:
    """The error as recorded in faithfulness runs 1-2 (non-streamed call)."""
    response = httpx.Response(400, request=_REQUEST)
    return groq.BadRequestError(
        "Error code: 400", response=response, body={"error": _REFUSED_DETAILS}
    )


def _refused_in_stream() -> groq.APIError:
    """The same refusal as the SDK raises it from inside a stream (/chat)."""
    return groq.APIError(_REFUSED_DETAILS["message"], _REQUEST, body=_REFUSED_DETAILS)


def _tool_round(call_id: str) -> list:
    """One agent turn that calls a tool, plus the tool's result."""
    return [
        AIMessage(
            "", tool_calls=[{"id": call_id, "name": "search_documents", "args": {"query": "q"}}]
        ),
        ToolMessage(f"[{call_id}] passage from round {call_id}", tool_call_id=call_id),
    ]


class _FakeModel:
    """Records how it was bound and what it was sent, then returns a plain answer."""

    def __init__(self) -> None:
        self.bind_kwargs: dict | None = None
        self.sent: list | None = None

    def bind_tools(self, tools, **kwargs):
        self.bind_kwargs = kwargs
        return self

    def invoke(self, messages):
        self.sent = messages
        return AIMessage("an answer")


def _run_agent_node(monkeypatch, messages) -> _FakeModel:
    fake = _FakeModel()
    monkeypatch.setattr(graph, "get_agent_model", lambda: fake)
    graph._agent_node({"messages": messages})
    return fake


def test_counts_only_rounds_after_the_latest_question():
    messages = [
        HumanMessage("first question"),
        *_tool_round("a"),
        *_tool_round("b"),
        AIMessage("first answer"),
        HumanMessage("second question"),
        *_tool_round("c"),
    ]
    assert graph._tool_rounds_since_last_question(messages) == 1


def test_parallel_tool_calls_in_one_turn_count_as_one_round():
    parallel = AIMessage(
        "",
        tool_calls=[
            {"id": "a", "name": "search_documents", "args": {"query": "q1"}},
            {"id": "b", "name": "query_courses", "args": {"code": "ACC 2302"}},
        ],
    )
    assert graph._tool_rounds_since_last_question([HumanMessage("q"), parallel]) == 1


def test_tools_stay_callable_under_the_budget(monkeypatch):
    messages = [HumanMessage("q")]
    for i in range(MAX_TOOL_ROUNDS - 1):
        messages += _tool_round(str(i))

    fake = _run_agent_node(monkeypatch, messages)

    assert fake.bind_kwargs == {}
    assert graph.BUDGET_EXHAUSTED_NOTE not in fake.sent[0]["content"]


def test_final_call_has_no_tools_once_the_budget_is_used(monkeypatch):
    messages = [HumanMessage("q")]
    for i in range(MAX_TOOL_ROUNDS):
        messages += _tool_round(str(i))

    fake = _run_agent_node(monkeypatch, messages)

    assert fake.bind_kwargs is None  # bind_tools never called
    assert graph.BUDGET_EXHAUSTED_NOTE in fake.sent[0]["content"]
    sent = fake.sent[1:]  # everything after the system prompt
    assert not any(m.type == "tool" or (m.type == "ai" and m.tool_calls) for m in sent)
    for i in range(MAX_TOOL_ROUNDS):
        assert f"passage from round {i}" in sent[-1].content


def test_final_call_keeps_earlier_turns_and_the_question():
    messages = [
        HumanMessage("first question"),
        AIMessage("first answer"),
        HumanMessage("second question"),
        *_tool_round("a"),
    ]
    rewritten = graph._without_tool_calls(messages)

    assert [m.content for m in rewritten[:3]] == [
        "first question",
        "first answer",
        "second question",
    ]
    assert "passage from round a" in rewritten[3].content


# --- The forced answer when the model calls a tool anyway -------------------


class _ScriptedModel:
    """Plays back a script: an exception is raised, anything else is returned."""

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[list] = []

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _cited_round(call_id: str, markers: list[int]) -> list:
    """A tool round whose result carries citations, like search_documents'."""
    artifact = [{"marker": n, "source": "catalog", "pages": [n], "text": "t"} for n in markers]
    return [
        AIMessage(
            "", tool_calls=[{"id": call_id, "name": "search_documents", "args": {"query": "q"}}]
        ),
        ToolMessage("passages", tool_call_id=call_id, artifact=artifact),
    ]


def _budget_used() -> list:
    return [
        HumanMessage("How many courses can I take?"),
        *_cited_round("a", [1, 2]),
        *_cited_round("b", [3]),
        *_cited_round("c", [2, 4]),  # [2] again: a repeated passage keeps its marker
    ]


def _run_forced(monkeypatch, outcomes, language="en"):
    fake = _ScriptedModel(outcomes)
    monkeypatch.setattr(graph, "get_agent_model", lambda: fake)
    config = {"configurable": {"language": language}}
    response = graph._agent_node({"messages": _budget_used()}, config)["messages"][0]
    return fake, response


def test_recognizes_the_refusal_in_both_shapes():
    assert graph._is_refused_tool_call(_refused_400())
    assert graph._is_refused_tool_call(_refused_in_stream())


def test_other_errors_are_not_the_refusal():
    other_400 = groq.BadRequestError(
        "Error code: 400",
        response=httpx.Response(400, request=_REQUEST),
        body={"error": {"message": "context too long", "code": "context_length_exceeded"}},
    )
    assert not graph._is_refused_tool_call(other_400)
    assert not graph._is_refused_tool_call(groq.APIError("no body", _REQUEST, body=None))
    assert not graph._is_refused_tool_call(ValueError("tool_use_failed"))


def test_refused_once_then_answered_after_a_retry(monkeypatch):
    fake, response = _run_forced(monkeypatch, [_refused_in_stream(), AIMessage("5 courses [3]")])

    assert response.content == "5 courses [3]"
    assert not response.response_metadata.get("fallback")
    assert len(fake.calls) == 2
    assert graph.FORCED_RETRY_NOTE not in fake.calls[0][0]["content"]
    assert graph.FORCED_RETRY_NOTE in fake.calls[1][0]["content"]
    assert fake.calls[0][1:] == fake.calls[1][1:]  # same conversation, only the note changes


def test_refused_twice_gives_the_fallback_with_every_marker_once(monkeypatch):
    fake, response = _run_forced(monkeypatch, [_refused_400(), _refused_in_stream()])

    assert len(fake.calls) == 2  # never a third call
    assert response.response_metadata["fallback"] is True
    assert response.content == graph.FALLBACK_WITH_SOURCES["en"] + " [1] [2] [3] [4]"


def test_fallback_is_in_french_for_a_french_question(monkeypatch):
    _, response = _run_forced(monkeypatch, [_refused_400(), _refused_400()], language="fr")
    assert response.content.startswith(graph.FALLBACK_WITH_SOURCES["fr"])


def test_fallback_without_passages_says_so():
    messages = [HumanMessage("q"), *_tool_round("a")]  # results with no citations
    response = graph._fallback_answer(messages, None)
    assert response.content == graph.FALLBACK_NO_SOURCES["en"]


def test_fallback_ignores_passages_from_earlier_questions():
    messages = [
        HumanMessage("first question"),
        *_cited_round("a", [1]),
        AIMessage("first answer [1]"),
        HumanMessage("second question"),
        *_cited_round("b", [7]),
    ]
    assert graph._fallback_answer(messages, "en").content.endswith(": [7]")


def test_other_errors_in_the_forced_answer_still_raise(monkeypatch):
    with pytest.raises(RuntimeError):
        _run_forced(monkeypatch, [RuntimeError("Groq is down")])


def test_fallback_reaches_the_chat_stream_as_agent_text(monkeypatch):
    """/chat forwards "messages" stream chunks from the agent node as tokens.

    The fallback is built in code, not streamed by an LLM; LangGraph still
    emits it when the node returns, and the run ends normally (no exception,
    so /chat sends citations + done, not an error).
    """
    fake = _ScriptedModel([_refused_400(), _refused_400()])
    monkeypatch.setattr(graph, "get_agent_model", lambda: fake)

    async def collect() -> list[str]:
        texts = []
        async for mode, chunk in graph.build_graph().astream(
            {"messages": _budget_used()},
            config={"configurable": {"language": "en"}},
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                message, metadata = chunk
                if metadata.get("langgraph_node") == "agent" and message.content:
                    texts.append(message.content)
        return texts

    assert "".join(asyncio.run(collect())) == (
        graph.FALLBACK_WITH_SOURCES["en"] + " [1] [2] [3] [4]"
    )
