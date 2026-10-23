"""Tests for the request-scoped trace behind the "Under the hood" panel
(app.agent.trace).

The guarantee that keeps the trace out of the evaluation: without
start_trace(), recording does nothing. And like the citation counter, the
trace must survive LangChain running each tool in a copied context.
"""

import contextvars

from app.agent.trace import record_tool_step, snippet, start_trace, trace_steps


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
    record_tool_step("search_documents", {"duration_ms": 12})
    record_tool_step("query_courses", {"code": "ACC 2302"})

    assert trace_steps() == [
        {"tool": "search_documents", "duration_ms": 12},
        {"tool": "query_courses", "code": "ACC 2302"},
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
