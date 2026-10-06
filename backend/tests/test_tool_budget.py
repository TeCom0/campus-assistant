"""Tests for the per-question tool-call budget in the agent node.

A fake model stands in for the real LLM, so these run without API calls.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent import graph
from app.config import MAX_TOOL_ROUNDS


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
