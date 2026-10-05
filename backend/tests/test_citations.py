"""Tests for request-scoped citation numbering (app.agent.citations).

Simulates what happens when the agent makes multiple tool calls within one
answer: each call reserves the next block of numbers, continuing the
sequence rather than restarting at [1] -- the exact behavior the /chat
streaming design depends on for globally unique citation markers.
"""

import contextvars

from app.agent.citations import next_citation_numbers, reset_citation_counter


def test_single_call_starts_at_one():
    reset_citation_counter()
    assert next_citation_numbers(3) == [1, 2, 3]


def test_second_call_continues_the_sequence():
    reset_citation_counter()
    first = next_citation_numbers(3)
    second = next_citation_numbers(2)

    assert first == [1, 2, 3]
    assert second == [4, 5]


def test_three_tool_calls_stay_globally_unique_and_contiguous():
    reset_citation_counter()
    # Simulates: search_documents (5 results), query_courses (1 fact),
    # search_documents again (2 results) -- the kind of sequence a real
    # multi-tool agent turn could produce.
    search_1 = next_citation_numbers(5)
    course = next_citation_numbers(1)
    search_2 = next_citation_numbers(2)

    all_numbers = search_1 + course + search_2
    assert all_numbers == [1, 2, 3, 4, 5, 6, 7, 8]
    assert len(set(all_numbers)) == len(all_numbers)  # no duplicates


def test_reset_isolates_requests_from_each_other():
    reset_citation_counter()
    next_citation_numbers(4)

    # A new request must not see the previous request's numbers.
    reset_citation_counter()
    assert next_citation_numbers(1) == [1]


def test_zero_count_returns_empty_without_advancing_counter():
    reset_citation_counter()
    assert next_citation_numbers(0) == []
    assert next_citation_numbers(1) == [1]


def test_survives_copy_context_boundary_like_langchain_tool_execution():
    """LangChain runs each tool call via contextvars.copy_context().run(...),
    which isolates plain ContextVar.set() calls from the caller -- this test
    reproduces that exact boundary (not just a plain function call) to catch
    a real regression that was found and fixed during development: an
    earlier int-based implementation passed every other test here but still
    silently reset to [1] on each "tool call" once routed through this
    boundary, because .set() inside a copied context never leaks back out.
    """
    reset_citation_counter()

    def call_one():
        return next_citation_numbers(5)

    def call_two():
        return next_citation_numbers(2)

    first = contextvars.copy_context().run(call_one)
    second = contextvars.copy_context().run(call_two)

    assert first == [1, 2, 3, 4, 5]
    assert second == [6, 7]
