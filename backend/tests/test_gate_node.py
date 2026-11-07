"""The gate as the last step of the graph. A fake model and a fake tool stand in, so these
make no LLM calls and need no database."""

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
)
from app.agent.history import build_input_messages
from app.config import MAX_AGENT_STEPS, MAX_TOOL_ROUNDS


@tool(response_format="content_and_artifact")
def _fake_search(query: str) -> tuple[str, list[dict]]:
    """Stands in for search_documents: always returns one passage, marker 1."""
    return "[1] a passage", [{"marker": 1, "source": "fake", "pages": [1], "text": "a passage"}]


def _search_turn(call_id: str = "c1") -> AIMessage:
    return AIMessage(
        "", tool_calls=[{"id": call_id, "name": "_fake_search", "args": {"query": "q"}}]
    )


class _ScriptedModel:
    """Returns the scripted messages in order, whatever it's sent."""

    def __init__(self, *replies: AIMessage) -> None:
        self.replies = list(replies)

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        return self.replies.pop(0)


def _run(monkeypatch, *replies: AIMessage, language: str = "en") -> list:
    monkeypatch.setattr(graph, "TOOLS", [_fake_search])
    model = _ScriptedModel(*replies)
    monkeypatch.setattr(graph, "get_agent_model", lambda: model)
    result = graph.build_graph().invoke(
        {"messages": [HumanMessage("a question")]},
        config={"recursion_limit": MAX_AGENT_STEPS, "configurable": {"language": language}},
    )
    return result["messages"]


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


def test_an_answer_with_no_citation_is_replaced(monkeypatch):
    messages = _run(monkeypatch, _search_turn(), AIMessage("The catalog says 68 credits."))
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == NO_CITATION


def test_a_number_no_tool_returned_is_replaced(monkeypatch):
    messages = _run(monkeypatch, _search_turn(), AIMessage("68 credits [7]."))
    assert final_answer(messages) == NOT_FOUND_TEMPLATE["en"]
    assert gate_reason(messages) == INVENTED_MARKER


def test_the_template_follows_the_runs_language(monkeypatch):
    messages = _run(monkeypatch, AIMessage("Bonjour !"), language="fr")
    assert final_answer(messages) == SCOPE_TEMPLATE["fr"]


def test_the_longest_run_fits_the_step_limit(monkeypatch):
    # Every tool round, the forced answer, and the gate: GraphRecursionError if it doesn't.
    rounds = [_search_turn(f"c{i}") for i in range(MAX_TOOL_ROUNDS)]
    messages = _run(monkeypatch, *rounds, AIMessage("68 credits [1]."))
    assert final_answer(messages) == "68 credits [1]."


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
