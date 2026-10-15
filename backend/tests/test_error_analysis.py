"""Tests for the error analysis (app.evaluation.error_analysis): which failures
need a cause, and the hand count that sets judge artifacts aside."""

from app.evaluation.error_analysis import collect_failures, count_causes, unconfirmed

QUESTIONS = {
    "m": {"set": "main", "expected_behavior": "answer"},
    "r": {"set": "regression", "expected_behavior": "answer"},
    "u": {"set": "unanswerable", "expected_behavior": "abstain"},
    "c": {"set": "main", "expected_behavior": "answer"},
}


def _claim(answer, n, kind="own", auto_label=None, exclude=None):
    return {"claim_id": f"{answer}#{n}", "id": answer, "kind": kind,
            "auto_label": auto_label, "exclude": exclude}  # fmt: skip


def test_failures_are_unsupported_cited_main_claims_false_refusals_and_crashes():
    answers = [{"id": "m", "error": None}, {"id": "r", "error": None},
               {"id": "u", "error": None}, {"id": "c", "error": "400"}]  # fmt: skip
    claims = [
        _claim("m", 1),  # judged unsupported: a failure
        _claim("m", 2),  # supported
        _claim("m", 3, kind="uncited"),  # unsupported but uncited: not in the headline
        _claim("m", 4, auto_label="unsupported"),  # invalid citation: a failure
        _claim("m", 5, exclude="refusal"),  # excluded: never a failure
        _claim("r", 1),  # unsupported, but not a main answer
    ]
    judgements = [
        {"id": "m", "abstains": False, "claims": [
            {"claim_id": "m#1", "label": "unsupported"}, {"claim_id": "m#2", "label": "supported"},
            {"claim_id": "m#3", "label": "unsupported"}]},
        {"id": "r", "abstains": True, "claims": [{"claim_id": "r#1", "label": "unsupported"}]},
        {"id": "u", "abstains": True, "claims": []},  # declining here is right
    ]  # fmt: skip
    failures = collect_failures(answers, claims, judgements, QUESTIONS)
    assert [(f["id"], f["type"]) for f in failures] == [
        ("m#1", "claim"),
        ("m#4", "claim"),
        ("r", "false_refusal"),  # declined an answerable regression question
        ("c", "crash"),
    ]


def test_hand_count_sets_judge_artifacts_aside():
    failures = [
        {"id": "a#1", "type": "claim", "answer": "a"},
        {"id": "b#1", "type": "claim", "answer": "b"},
        {"id": "b#2", "type": "claim", "answer": "b"},
        {"id": "c", "type": "crash", "answer": "c"},
    ]
    causes = {
        "a#1": {"confirmed": "judge_artifact"},  # a fails only through the judge
        "b#1": {"confirmed": "judge_artifact"},
        "b#2": {"confirmed": "french_retrieval"},  # b has one real failure
        "c": {"confirmed": "crash"},
    }
    counts = count_causes(failures, causes)
    assert counts["by_cause"] == {"crash": 1, "french_retrieval": 1, "judge_artifact": 2}
    assert (counts["failing_answers_judge"], counts["failing_answers_by_hand"]) == (2, 1)
    assert counts["judge_artifact_only"] == ["a"]


def test_unconfirmed_lists_missing_and_unknown_causes():
    failures = [{"id": "a#1"}, {"id": "a#2"}, {"id": "a#3"}]
    causes = {"a#1": {"confirmed": "crash"}, "a#2": {"confirmed": "typo"}}
    assert unconfirmed(failures, causes) == ["a#2", "a#3"]
