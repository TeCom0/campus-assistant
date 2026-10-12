"""Tests for the faithfulness baseline report (app.evaluation.report)."""

from app.evaluation.report import final_labels, group_stats, summarize_answer

QUESTION = {"language": "en", "set": "main", "expected_behavior": "answer"}


def _claim(n: int, kind: str, auto_label: str | None = None) -> dict:
    return {"claim_id": f"q#{n}", "id": "q", "kind": kind, "auto_label": auto_label}


def _summary(error: bool = False, cited: int = 1, unsupported_cited: int = 0, **extra) -> dict:
    base = {
        "error": error,
        "abstains": False,
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
