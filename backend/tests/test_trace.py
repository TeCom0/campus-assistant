"""Tests for the request-scoped trace behind the "Under the hood" panel
(app.agent.trace).

The guarantee that keeps the trace out of the evaluation: without
start_trace(), recording does nothing. And like the citation counter, the
trace must survive LangChain running each tool in a copied context.
"""

import contextvars
import threading
from typing import Annotated

from langchain_core.messages import AIMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.trace import (
    in_call_order,
    record_tool_step,
    snippet,
    start_trace,
    trace_steps,
)


def _fresh_context(fn, *args):
    # A context with no trace started, like an evaluation run's.
    return contextvars.Context().run(fn, *args)


def test_nothing_is_recorded_without_start_trace():
    def run():
        record_tool_step("search_documents", {"duration_ms": 12})
        return trace_steps()

    assert _fresh_context(run) is None


def test_steps_are_recorded_in_order_with_their_tool():
    start_trace()
    record_tool_step("search_documents", {"duration_ms": 12}, call_id="a")
    record_tool_step("query_courses", {"code": "ACC 2302"})

    assert trace_steps() == [
        {"tool": "search_documents", "call_id": "a", "duration_ms": 12},
        {"tool": "query_courses", "call_id": None, "code": "ACC 2302"},
    ]


def test_start_trace_isolates_requests_from_each_other():
    start_trace()
    record_tool_step("search_documents", {})

    start_trace()
    assert trace_steps() == []


def test_survives_copy_context_boundary_like_langchain_tool_execution():
    """LangChain runs each tool call via contextvars.copy_context().run(...).
    Steps recorded inside such a copy must be visible to the request (/chat)
    that started the trace."""
    start_trace()
    contextvars.copy_context().run(record_tool_step, "search_documents", {"n": 1})
    contextvars.copy_context().run(record_tool_step, "query_courses", {"n": 2})

    assert [step["n"] for step in trace_steps()] == [1, 2]


def test_trace_steps_returns_a_copy():
    start_trace()
    record_tool_step("search_documents", {})
    trace_steps().clear()

    assert len(trace_steps()) == 1


def test_in_call_order_sorts_by_the_models_ids_and_keeps_unknown_ids_last():
    steps = [{"call_id": "b"}, {"call_id": None}, {"call_id": "a"}, {"call_id": "zz"}]

    ordered = in_call_order(steps, ["a", "b"])

    assert [step["call_id"] for step in ordered] == ["a", "b", None, "zz"]


# Two tools for the parallel test: "slow" can only finish after "fast" has,
# so the finish order is the reverse of the model's order every time, with
# no sleep-based timing. If ToolNode ran them one after the other, "slow"
# would wait out its timeout first and the recorded order would not be reversed.
_fast_done = threading.Event()


@tool
def slow(tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """Finishes after fast."""
    _fast_done.wait(timeout=5)
    record_tool_step("slow", {}, call_id=tool_call_id)
    return "slow"


@tool
def fast(tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """Finishes first."""
    record_tool_step("fast", {}, call_id=tool_call_id)
    _fast_done.set()
    return "fast"


def test_parallel_tool_calls_come_back_in_the_models_order():
    _fast_done.clear()
    tool_node_graph = StateGraph(MessagesState)
    tool_node_graph.add_node("tools", ToolNode([slow, fast]))
    tool_node_graph.add_edge(START, "tools")
    calls = AIMessage(
        "",
        tool_calls=[
            {"id": "call_slow", "name": "slow", "args": {}},
            {"id": "call_fast", "name": "fast", "args": {}},
        ],
    )
    start_trace()
    tool_node_graph.compile().invoke({"messages": [calls]})

    recorded = trace_steps()
    # Ran in parallel, in ToolNode's own threads: recorded as they finished.
    assert [step["tool"] for step in recorded] == ["fast", "slow"]
    # Put back in the model's order by the ids ToolNode injected.
    model_order = [call["id"] for call in calls.tool_calls]
    assert [step["tool"] for step in in_call_order(recorded, model_order)] == ["slow", "fast"]


def test_snippet_skips_the_section_line_and_flattens_whitespace():
    text = "Section: Undergraduate Studies > Repeat Policy\nA student may repeat\n  a course."
    assert snippet(text) == "A student may repeat a course."


def test_snippet_keeps_a_first_line_that_is_not_a_section_line():
    assert snippet("Adding/Dropping Courses\nStudents in good standing") == (
        "Adding/Dropping Courses Students in good standing"
    )


def test_snippet_cuts_at_a_word_and_marks_the_cut():
    text = "Students in good academic standing, with no holds, may add courses online."
    cut = snippet(text, limit=40)

    assert cut == "Students in good academic standing…"
    assert len(cut) <= 41  # the limit, plus the "…"


def test_snippet_cuts_one_long_word_at_the_limit():
    assert snippet("x" * 50, limit=10) == "x" * 10 + "…"
