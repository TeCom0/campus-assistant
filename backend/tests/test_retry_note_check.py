"""The A2.6b step 2 harness's schedule: no model call, no database."""

from collections import Counter

from app.evaluation.run_retry_note_check import NOTES, diagnosis_runs, schedule


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
