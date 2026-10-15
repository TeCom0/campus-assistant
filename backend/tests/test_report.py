"""Tests for the faithfulness baseline report (app.evaluation.report)."""

from app.evaluation.report import final_labels, group_stats, summarize_answer

QUESTION = {"language": "en", "set": "main", "expected_behavior": "answer"}


def _claim(n: int, kind: str, auto_label: str | None = None, exclude: str | None = None) -> dict:
    return {
        "claim_id": f"q#{n}",
        "id": "q",
        "kind": kind,
        "auto_label": auto_label,
        "exclude": exclude,
    }


def _summary(error: bool = False, cited: int = 1, unsupported_cited: int = 0, **extra) -> dict:
    base = {
        "id": "q",
        "error": error,
        "abstains": False,
        "expected_behavior": "answer",
        "false_refusal": False,
        "missed_refusal": False,
        "excluded_claims": 0,
        "cited_claims": cited,
        "unsupported_cited": unsupported_cited,
        "unsupported_own": 0,
        "unsupported_uncited": 0,
    }
    return {**base, **extra}


def test_final_labels_prefer_the_auto_label_and_leave_unjudged_claims_none():
    claims = [_claim(1, "own"), _claim(2, "own", auto_label="unsupported"), _claim(3, "own")]
    judgements = [{"claims": [{"claim_id": "q#1", "label": "supported"}]}]
    assert final_labels(claims, judgements) == {
        "q#1": "supported",
        "q#2": "unsupported",  # never sent to the judge
        "q#3": None,  # not judged yet: the report refuses to run
    }


def test_summarize_counts_unsupported_claims_by_kind():
    claims = [
        _claim(1, "own"),
        _claim(2, "block"),
        _claim(3, "source_line"),
        _claim(4, "uncited"),
    ]
    labels = {"q#1": "supported", "q#2": "unsupported", "q#3": "no_claim", "q#4": "unsupported"}
    answer = {"id": "q", "run": 1, "error": None}
    s = summarize_answer(answer, QUESTION, claims, labels, abstains=False)
    assert (s["cited_claims"], s["unsupported_cited"], s["unsupported_own"]) == (3, 1, 0)
    assert (s["uncited_claims"], s["unsupported_uncited"]) == (1, 1)


def test_group_stats_keep_crashes_out_of_the_headline_but_count_them():
    answers = [
        _summary(unsupported_cited=1),
        _summary(),
        _summary(error=True, cited=0),
        _summary(cited=0),  # cites nothing: can't be "unfaithful", so it's counted apart
    ]
    s = group_stats(answers)
    assert (s["answers"], s["errors"], s["answered"]) == (4, 1, 3)
    assert (s["unfaithful"], s["unfaithful_pct"]) == (1, 33.3)
    assert s["citing_nothing"] == 1


def test_own_only_counts_answers_whose_unsupported_claim_has_its_own_marker():
    answers = [
        _summary(unsupported_cited=1, unsupported_own=1),
        _summary(unsupported_cited=2, unsupported_own=0),  # only scope-rule claims
    ]
    s = group_stats(answers)
    assert (s["unfaithful"], s["unfaithful_own_only"]) == (2, 1)


def test_excluded_claims_are_neither_labelled_nor_counted():
    claims = [_claim(1, "uncited", exclude="refusal"), _claim(2, "own")]
    labels = final_labels(claims, [{"claims": [{"claim_id": "q#2", "label": "supported"}]}])
    assert labels == {"q#2": "supported"}  # the refusal needs no judge, so no refusal to run
    answer = {"id": "q", "run": 1, "error": None}
    s = summarize_answer(answer, QUESTION, claims, labels, abstains=True)
    assert (s["cited_claims"], s["uncited_claims"], s["excluded_claims"]) == (1, 0, 1)


def test_declines_are_checked_against_the_expected_behavior():
    answer = {"id": "q", "run": 1, "error": None}
    unanswerable = {**QUESTION, "expected_behavior": "abstain"}
    declined_answerable = summarize_answer(answer, QUESTION, [], {}, abstains=True)
    answered_unanswerable = summarize_answer(answer, unanswerable, [], {}, abstains=False)
    declined_unanswerable = summarize_answer(answer, unanswerable, [], {}, abstains=True)
    assert declined_answerable["false_refusal"] and not declined_answerable["missed_refusal"]
    assert answered_unanswerable["missed_refusal"] and not answered_unanswerable["false_refusal"]
    assert (
        not declined_unanswerable["false_refusal"] and not declined_unanswerable["missed_refusal"]
    )
    crashed = summarize_answer({**answer, "error": "400"}, QUESTION, [], {}, abstains=None)
    assert not crashed["false_refusal"]  # a crash is reported as an error, not a refusal


def test_group_stats_list_false_and_missed_refusals_and_missing_verdicts():
    answers = [
        _summary(id="a", abstains=True, false_refusal=True),
        _summary(id="b", expected_behavior="abstain", missed_refusal=True),
        _summary(id="c", expected_behavior="abstain", abstains=True),
        _summary(id="d", abstains=None),
        _summary(id="e", error=True, abstains=None),  # crashed: in neither check
    ]
    s = group_stats(answers)
    assert (s["false_refusals"], s["should_answer"]) == (["a"], 2)
    assert (s["missed_refusals"], s["should_abstain"]) == (["b"], 2)
    assert s["no_decline_verdict"] == ["d"]
