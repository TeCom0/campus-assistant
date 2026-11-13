"""The gate as the last step of the graph. A fake model and a fake tool stand in, so these
make no LLM calls and need no database."""

import json
from pathlib import Path

import groq
import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.agent import graph
from app.agent.gate import (
    INVENTED_MARKER,
    NO_CITATION,
    NO_TOOL,
    NOT_FOUND_TEMPLATE,
    SCOPE_TEMPLATE,
    final_answer,
    gate_reason,
    is_gate_template,
    was_retried,
)
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.config import MAX_AGENT_STEPS, MAX_TOOL_ROUNDS

# In every rejected answer, so it's easy to check it isn't passed on.
REJECTED = "REJECTED-MODEL-TEXT"


@tool(response_format="content_and_artifact")
def _fake_search(query: str) -> tuple[str, list[dict]]:
    """Stands in for search_documents: always returns one passage, marker 1."""
    return "[1] a passage", [{"marker": 1, "source": "fake", "pages": [1], "text": "a passage"}]


def _search_turn(call_id: str = "c1") -> AIMessage:
    return AIMessage(
        "", tool_calls=[{"id": call_id, "name": "_fake_search", "args": {"query": "q"}}]
    )


class _ScriptedModel:
    """Returns the scripted replies in order, whatever it's sent (an exception is raised).

    Records each call: whether tools were bound, and the messages sent. A call past the
    last reply fails the test with an IndexError, so an extra call can't go unnoticed.
    """

    def __init__(self, *replies) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[bool, list]] = []

    def bind_tools(self, tools, **kwargs):
        return _Bound(self)

    def invoke(self, messages, *, bound: bool = False):
        self.calls.append((bound, messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class _Bound:
    def __init__(self, model: _ScriptedModel) -> None:
        self.model = model

    def invoke(self, messages):
        return self.model.invoke(messages, bound=True)


def _run_model(monkeypatch, *replies, language: str = "en") -> tuple[list, _ScriptedModel]:
    monkeypatch.setattr(graph, "TOOLS", [_fake_search])
    model = _ScriptedModel(*replies)
    monkeypatch.setattr(graph, "get_agent_model", lambda: model)
    result = graph.build_graph().invoke(
        {"messages": [HumanMessage("a question")]},
        config={"recursion_limit": MAX_AGENT_STEPS, "configurable": {"language": language}},
    )
    return result["messages"], model


def _run(monkeypatch, *replies, language: str = "en") -> list:
    return _run_model(monkeypatch, *replies, language=language)[0]


# --- Through the compiled graph ---------------------------------------------------


def test_an_answer_with_no_tool_call_is_replaced_by_the_scope_template(monkeypatch):
    messages = _run(monkeypatch, AIMessage("1 + 1 = 2."))
    assert final_answer(messages) == SCOPE_TEMPLATE["en"]
    assert gate_reason(messages) == NO_TOOL


def test_a_cited_answer_goes_through_unchanged(monkeypatch):
    messages = _run(monkeypatch, _search_turn(), AIMessage("68 credits [1]."))
    assert final_answer(messages) == "68 credits [1]."
    assert gate_reason(messages) is None
    assert messages[-1].content == "68 credits [1]."  # the gate added nothing


def test_an_answer_with_no_citation_is_replaced_if_the_retry_cites_nothing_either(monkeypatch):
    messages = _run(
        monkeypatch,
        _search_turn(),
        AIMessage("The catalog says 68 credits."),
        AIMessage("Still 68 credits, no marker."),
    )
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == NO_CITATION


def test_a_number_no_tool_returned_is_replaced_without_a_retry(monkeypatch):
    messages, model = _run_model(monkeypatch, _search_turn(), AIMessage("68 credits [7]."))
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == INVENTED_MARKER
    assert not was_retried(messages)
    assert len(model.calls) == 2


# --- The one retry ------------------------------------------------------------------


def test_no_citation_is_retried_once_and_a_cited_retry_goes_out(monkeypatch):
    messages, model = _run_model(
        monkeypatch,
        _search_turn(),
        AIMessage(f"{REJECTED} 68 credits."),
        AIMessage("68 credits [1]."),
    )
    assert final_answer(messages) == "68 credits [1]."
    assert gate_reason(messages) is None
    assert was_retried(messages)
    assert len(model.calls) == 3


def test_no_tool_is_never_retried(monkeypatch):
    # Only one reply: a retry would be a second call, and fail with an IndexError.
    messages, model = _run_model(monkeypatch, AIMessage("1 + 1 = 2."))
    assert final_answer(messages) == SCOPE_TEMPLATE["en"]
    assert not was_retried(messages)
    assert len(model.calls) == 1


def test_there_is_never_a_second_retry(monkeypatch):
    # A fourth reply is there to be taken: if a second retry ran, it would pass.
    messages, model = _run_model(
        monkeypatch,
        _search_turn(),
        AIMessage("No marker."),
        AIMessage("No marker again."),
        AIMessage("68 credits [1]."),
    )
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert len(model.calls) == 3
    assert model.replies == [AIMessage("68 credits [1].")]


def test_a_retried_answer_with_an_invented_marker_still_gets_the_template(monkeypatch):
    messages = _run(monkeypatch, _search_turn(), AIMessage("No marker."), AIMessage("68 [7]."))
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == INVENTED_MARKER


def test_the_retry_has_no_tools_no_tool_calls_and_the_same_results(monkeypatch):
    _, model = _run_model(
        monkeypatch, _search_turn(), AIMessage(f"{REJECTED} 68."), AIMessage("68 [1].")
    )
    bound, sent = model.calls[-1]
    assert not bound  # no tools bound, so no new search
    system, *conversation, note = sent
    assert all(m.type == "human" for m in conversation)  # no tool calls to imitate
    assert "[1] a passage" in conversation[-1].content
    assert REJECTED not in str(sent)  # the rejected answer isn't shown
    # The note is the last message, nearest the answer, and not in the system prompt.
    assert note.type == "human" and note.content == graph.CITATION_RETRY_LAST_NOTE
    assert system["content"].endswith(graph.BUDGET_EXHAUSTED_NOTE)
    assert graph.CITATION_RETRY_NOTE not in system["content"]


def test_the_previous_retry_input_differs_only_in_the_note():
    # Step 2 compares the two notes on the same searches: nothing else may differ.
    messages = [HumanMessage("q"), _search_turn(), _result_with_marker(1), AIMessage("No marker.")]
    system_new, *rest_new, _note = graph._retry_input(messages, "en")
    system_old, *rest_old = graph._retry_input_current(messages, "en")
    assert rest_new == rest_old
    assert system_old["content"] == system_new["content"] + "\n\n" + graph.CITATION_RETRY_NOTE


def test_a_tool_call_in_the_retry_leaves_the_template(monkeypatch):
    refused = groq.APIError(
        "Tool choice is none, but model called a tool",
        httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        body={"code": "tool_use_failed"},
    )
    messages, model = _run_model(monkeypatch, _search_turn(), AIMessage("No marker."), refused)
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == NO_CITATION
    assert len(model.calls) == 3  # one call for the retry, not the forced answer's two


def test_the_template_follows_the_runs_language(monkeypatch):
    messages = _run(monkeypatch, AIMessage("Bonjour !"), language="fr")
    assert final_answer(messages) == SCOPE_TEMPLATE["fr"]


def test_the_longest_run_fits_the_step_limit(monkeypatch):
    # Every tool round, the forced answer, both gates and the retry: GraphRecursionError if
    # it doesn't fit.
    rounds = [_search_turn(f"c{i}") for i in range(MAX_TOOL_ROUNDS)]
    messages = _run(monkeypatch, *rounds, AIMessage("No marker."), AIMessage("68 credits [1]."))
    assert final_answer(messages) == "68 credits [1]."
    assert was_retried(messages)


# --- The node on its own ----------------------------------------------------------


def _gate(*messages, language="en") -> dict:
    return graph._gate_node({"messages": list(messages)}, {"configurable": {"language": language}})


def _result_with_marker(marker: int) -> ToolMessage:
    return ToolMessage(
        f"[{marker}] a passage", tool_call_id="c1", artifact=[{"marker": marker, "source": "fake"}]
    )


def test_markers_from_an_earlier_question_dont_count():
    update = _gate(
        HumanMessage("first question"),
        _result_with_marker(1),
        AIMessage("68 credits [1]."),
        HumanMessage("second question"),
        AIMessage("Still 68 credits [1]."),
    )
    assert gate_reason(update["messages"]) == NO_TOOL


def test_an_earlier_answers_text_isnt_part_of_this_answer():
    update = _gate(
        HumanMessage("first question"),
        AIMessage("68 credits [1]."),
        HumanMessage("second question"),
        _result_with_marker(1),
        AIMessage("No citation in this one."),
    )
    assert gate_reason(update["messages"]) == NO_CITATION


def test_the_code_built_fallback_passes():
    update = _gate(
        HumanMessage("a question"),
        _result_with_marker(1),
        AIMessage("I couldn't finish this answer.", response_metadata={"fallback": True}),
    )
    assert update == {"messages": []}


def test_an_answer_that_passes_adds_nothing():
    update = _gate(HumanMessage("a question"), _result_with_marker(1), AIMessage("68 credits [1]."))
    assert update == {"messages": []}


def test_the_log_line_holds_only_the_reason(capsys):
    _gate(HumanMessage("my secret question"), AIMessage("the model's text"))
    out = capsys.readouterr().out
    assert out == f"[agent] gate replaced the answer: {NO_TOOL}\n"


# --- Reading the result, and history ----------------------------------------------


def test_final_answer_joins_the_agents_text_and_fixes_brackets():
    messages = [HumanMessage("q"), AIMessage("Searching. "), AIMessage("68 credits 【1】.")]
    assert final_answer(messages) == "Searching. 68 credits [1]."


def test_final_answer_gives_the_template_instead_of_the_rejected_text():
    messages = [
        AIMessage("the rejected text"),
        AIMessage("the template", response_metadata={"gate": NO_CITATION}),
    ]
    assert final_answer(messages) == "the template"


def test_after_a_retry_only_the_retry_and_its_check_count():
    first = [
        AIMessage("the rejected text"),
        AIMessage("the template", response_metadata={"gate": NO_CITATION}),
    ]
    passed = [*first, AIMessage("68 credits [1].", response_metadata={"retry": True})]
    assert final_answer(passed) == "68 credits [1]."
    assert gate_reason(passed) is None

    failed = [*passed, AIMessage("the template", response_metadata={"gate": INVENTED_MARKER})]
    assert final_answer(failed) == "the template"
    assert gate_reason(failed) == INVENTED_MARKER


@pytest.mark.parametrize("template", [*SCOPE_TEMPLATE.values(), *NOT_FOUND_TEMPLATE.values()])
def test_templates_are_recognised_and_left_out_of_history(template):
    assert is_gate_template(template)
    assert is_gate_template(f"  {template}\n")
    messages = build_input_messages(
        "next question",
        [{"role": "user", "content": "1 + 1?"}, {"role": "assistant", "content": template}],
    )
    assert messages == [
        {"role": "user", "content": "1 + 1?"},
        {"role": "user", "content": "next question"},
    ]


def test_a_real_answer_is_not_mistaken_for_a_template():
    assert not is_gate_template("I couldn't find this in the documents I have, but [1] says 68.")


# --- The retry leaves the off-topic set's outcome unchanged (A2.6b rule, offline) ----

GATE_CHECK_RUN = (
    Path(__file__).resolve().parents[2] / "eval/results/gate/2026-11-07_gate_check.jsonl"
)


def _offtopic_records() -> list[dict]:
    with GATE_CHECK_RUN.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    return [r for r in records if r["set"] == "offtopic"]


def test_the_saved_offtopic_set_ended_only_in_no_tool_or_a_pass():
    # The premise of the replay below: no off-topic answer could have been retried.
    records = _offtopic_records()
    assert len(records) == 12
    assert {r["gate"] for r in records} == {NO_TOOL, None}


@pytest.mark.parametrize("record", _offtopic_records(), ids=lambda r: r["id"])
def test_each_offtopic_outcome_is_unchanged_by_the_retry(monkeypatch, record):
    """Replays the saved outcome through the graph with the retry: the student gets the
    same text, with no retry and no extra model call. 0 LLM tokens.

    The model's own text wasn't saved for a replaced answer, only the template. It doesn't
    matter: with no tool call the gate never reads it, so a text with valid-looking markers
    stands in, the case most likely to slip through.
    """
    cards = record["cards"]

    @tool("search_documents", response_format="content_and_artifact")
    def saved_search(query: str) -> tuple[str, list[dict]]:
        """Returns the passages whose markers the saved answer cited."""
        return "passages", [{"marker": m, "source": "fake", "pages": [1]} for m in cards]

    monkeypatch.setattr(graph, "TOOLS", [saved_search])
    if record["gate"] == NO_TOOL:
        replies = [AIMessage("Paris [1][2].")]
    else:
        call = {"id": "c1", "name": "search_documents", "args": {"query": "q"}}
        replies = [AIMessage("", tool_calls=[call]), AIMessage(record["answer"])]
    model = _ScriptedModel(*replies)
    monkeypatch.setattr(graph, "get_agent_model", lambda: model)

    language = detect_language(record["question"])  # as /chat does
    messages = graph.build_graph().invoke(
        {"messages": [HumanMessage(record["question"])]},
        config={"recursion_limit": MAX_AGENT_STEPS, "configurable": {"language": language}},
    )["messages"]

    assert final_answer(messages) == record["answer"]
    assert gate_reason(messages) == record["gate"]
    assert not was_retried(messages)
    assert len(model.calls) == len(replies)
