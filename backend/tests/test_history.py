"""Tests for building the agent's input messages from optional chat history."""

from app.agent.history import build_input_messages, strip_citation_markers


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
