"""Tests for request-scoped citation numbering and filtering (app.agent.citations).

Simulates what happens when the agent makes multiple tool calls within one
answer: new passages continue the sequence rather than restarting at [1],
and a passage returned again keeps its first number -- the behavior the
/chat streaming design depends on for one marker per source.
"""

import contextvars

from app.agent.citations import (
    citation_number_for,
    cited_markers,
    keep_cited,
    reset_citation_counter,
)


def _numbers(keys) -> list[int]:
    return [citation_number_for(key)[0] for key in keys]


def test_new_passages_number_from_one():
    reset_citation_counter()
    assert _numbers(["a", "b", "c"]) == [1, 2, 3]


def test_second_tool_call_continues_the_sequence():
    reset_citation_counter()
    first = _numbers(["a", "b", "c"])
    second = _numbers(["d", "e"])

    assert first == [1, 2, 3]
    assert second == [4, 5]


def test_repeated_passage_keeps_its_first_number():
    # The duplicate-sources bug: 3 searches for "What is MTH 1305?" returned
    # chunk 1030 three times, numbered as 3 separate sources.
    reset_citation_counter()
    _numbers([("catalog", 1030), ("catalog", 759)])

    number, is_new = citation_number_for(("catalog", 1030))
    assert (number, is_new) == (1, False)
    # ...and the next new passage doesn't skip a number for the repeat.
    assert citation_number_for(("catalog", 444)) == (3, True)


def test_reset_isolates_requests_from_each_other():
    reset_citation_counter()
    _numbers(["a", "b", "c", "d"])

    # A new request must not see the previous request's numbers or passages.
    reset_citation_counter()
    assert citation_number_for("d") == (1, True)


def test_survives_copy_context_boundary_like_langchain_tool_execution():
    """LangChain runs each tool call via contextvars.copy_context().run(...),
    which isolates plain ContextVar.set() calls from the caller -- this test
    reproduces that exact boundary (not just a plain function call) to catch
    a real regression that was found and fixed during development: an
    earlier int-based implementation passed every other test here but still
    silently reset to [1] on each "tool call" once routed through this
    boundary, because .set() inside a copied context never leaks back out.
    The passage -> number dict must cross it too.
    """
    reset_citation_counter()

    first = contextvars.copy_context().run(_numbers, ["a", "b", "c", "d", "e"])
    second = contextvars.copy_context().run(_numbers, ["f", "a"])

    assert first == [1, 2, 3, 4, 5]
    assert second == [6, 1]


def _citation(marker: int) -> dict:
    return {"marker": marker, "source": "catalog", "pages": [marker]}


def test_cited_markers_reads_single_and_grouped_brackets():
    answer = "Needs ACC 2301 [3]. GPA rules apply [2, 4] and [ 7 ] is not a marker."
    assert cited_markers(answer) == {2, 3, 4}


def test_keep_cited_drops_uncited_and_duplicates_and_sorts():
    citations = [_citation(1), _citation(2), _citation(3), _citation(4), _citation(2)]
    kept = keep_cited(citations, "First [4], then [2], and again [4].")
    assert [c["marker"] for c in kept] == [2, 4]


def test_answer_without_citations_lists_no_sources():
    # e.g. an "I don't know" answer: it used none of the passages it was given.
    assert keep_cited([_citation(1), _citation(2)], "I don't know based on the documents.") == []


def test_marker_with_no_matching_citation_is_ignored():
    # The model invented [9]; there's no source to show for it.
    assert keep_cited([_citation(1)], "Fact [1], other fact [9].") == [_citation(1)]
