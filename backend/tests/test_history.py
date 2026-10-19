"""Tests for building the agent's input messages from optional chat history."""

from app.agent import graph
from app.agent.history import build_input_messages, strip_citation_markers
from app.config import MAX_HISTORY_MESSAGES


def test_no_history_gives_just_the_question():
    assert build_input_messages("What is the credit limit?", None) == [
        {"role": "user", "content": "What is the credit limit?"}
    ]


def test_history_comes_before_the_current_question():
    history = [
        {"role": "user", "content": "How many credits transfer?"},
        {"role": "assistant", "content": "68 for undergraduates."},
    ]
    messages = build_input_messages("And for graduates?", history)

    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "And for graduates?"


def test_citation_markers_are_stripped_from_prior_assistant_turns_only():
    history = [
        {"role": "user", "content": "How many credits [1] transfer?"},
        {"role": "assistant", "content": "68 credits [2].\n\n- Graduates: 12 [3]"},
    ]
    messages = build_input_messages("Next?", history)

    assert messages[0]["content"] == "How many credits [1] transfer?"
    assert messages[1]["content"] == "68 credits.\n\n- Graduates: 12"


def test_grouped_citation_markers_are_stripped_too():
    # The answer can cite "[2, 4]"; keep_cited reads that form, so it must be
    # stripped as well or its old numbers reach the next request.
    history = [{"role": "assistant", "content": "68 credits [2, 4] and 12 [1,3]."}]
    messages = build_input_messages("Next?", history)

    assert messages[0]["content"] == "68 credits and 12."


def test_history_is_capped_to_the_most_recent_turns():
    history = [{"role": "user", "content": f"turn {i}"} for i in range(50)]
    messages = build_input_messages("latest", history)

    assert len(messages) == 11  # MAX_HISTORY_MESSAGES (10) + the current question
    assert messages[-1]["content"] == "latest"
    assert messages[0]["content"] == "turn 40"


def test_strip_keeps_text_without_markers_unchanged():
    assert strip_citation_markers("No citations here.") == "No citations here."


def test_fallback_answers_are_left_out_but_the_question_stays():
    fallback = graph.FALLBACK_WITH_SOURCES["en"] + " [1] [2] [3]"
    history = [
        {"role": "user", "content": "How many courses can I take?"},
        {"role": "assistant", "content": fallback},
        {"role": "user", "content": "Quelle est la limite ?"},
        {"role": "assistant", "content": graph.FALLBACK_NO_SOURCES["fr"]},
    ]
    messages = build_input_messages("Try again please", history)

    assert messages == [
        {"role": "user", "content": "How many courses can I take?"},
        {"role": "user", "content": "Quelle est la limite ?"},
        {"role": "user", "content": "Try again please"},
    ]


def test_a_real_answer_that_mentions_not_finishing_is_kept():
    answer = "The catalog says you can't finish a degree in under 7 semesters [2]."
    messages = build_input_messages("Next?", [{"role": "assistant", "content": answer}])
    assert (
        messages[0]["content"] == "The catalog says you can't finish a degree in under 7 semesters."
    )


def test_the_cap_counts_only_turns_that_are_kept():
    fallback = {"role": "assistant", "content": graph.FALLBACK_NO_SOURCES["en"]}
    real = [{"role": "user", "content": f"q{i}"} for i in range(MAX_HISTORY_MESSAGES)]
    messages = build_input_messages("Next?", [*real[:5], fallback, *real[5:]])

    assert [m["content"] for m in messages[:-1]] == [m["content"] for m in real]
