"""The A2.6b step 2 harness's schedule: no model call, no database."""

from collections import Counter

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent import graph
from app.evaluation.run_retry_note_check import (
    NOTES,
    PREVIOUS_CITATION_RETRY_NOTE,
    diagnosis_runs,
    retry_input_previous,
    schedule,
)


def test_the_previous_input_is_what_the_retry_sent_before_step_1():
    # Before step 1 the graph sent: system prompt, budget note and citation note in one system
    # message, then the conversation without tool calls, and nothing after it.
    messages = [
        HumanMessage("q"),
        AIMessage("", tool_calls=[{"id": "c1", "name": "search_documents", "args": {}}]),
        ToolMessage("[1] a passage", tool_call_id="c1", artifact=[{"marker": 1}]),
    ]
    system, *conversation = retry_input_previous(messages, "en")
    assert system["content"] == "\n\n".join(
        [
            graph._build_system_prompt("en"),
            graph.BUDGET_EXHAUSTED_NOTE,
            PREVIOUS_CITATION_RETRY_NOTE,
        ]
    )
    assert conversation == graph._without_tool_calls(messages)
    # Nothing but the note differs from the new input.
    new_system, *new_conversation, _note = graph._retry_input(messages, "en")
    assert new_conversation == conversation
    assert system["content"] == new_system["content"] + "\n\n" + PREVIOUS_CITATION_RETRY_NOTE


def test_each_note_gets_ten_calls_on_the_same_search_sets():
    calls = schedule()
    assert Counter(note for _, _, note in calls) == {"current": 10, "new": 10}
    for note in NOTES:
        sets = Counter(s for _, s, n in calls if n == note)
        assert sets == {0: 4, 1: 3, 2: 3}  # round-robin over the 3 diagnosis runs


def test_both_notes_of_a_pair_use_the_same_set_and_the_lead_alternates():
    calls = schedule()
    pairs = [calls[i : i + 2] for i in range(0, len(calls), 2)]
    for (pair_a, set_a, _), (pair_b, set_b, _) in pairs:
        assert pair_a == pair_b and set_a == set_b
    assert [p[0][2] for p in pairs] == ["current", "new"] * 5


def test_the_diagnosis_has_the_three_runs_the_rule_names():
    runs = diagnosis_runs()
    assert len(runs) == 3
    assert all(r["queries"] for r in runs)
