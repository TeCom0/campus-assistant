"""Tests for the judge-vs-human agreement statistics (app.evaluation.agreement)."""

import pytest

from app.evaluation.agreement import cohens_kappa, compare, unjudged, wilson_interval


def test_kappa_is_one_for_perfect_agreement_and_zero_at_chance():
    assert cohens_kappa([("supported", "supported"), ("unsupported", "unsupported")]) == 1.0
    # Each labeller says "supported" half the time, independently: chance level.
    pairs = [("supported", "supported"), ("supported", "unsupported"),
             ("unsupported", "supported"), ("unsupported", "unsupported")]  # fmt: skip
    assert cohens_kappa(pairs) == pytest.approx(0.0)


def test_kappa_discounts_agreement_that_comes_from_one_common_label():
    # 9/10 agree, but almost everything is "supported" for both: kappa is far lower.
    pairs = [("supported", "supported")] * 8 + [
        ("unsupported", "unsupported"),
        ("unsupported", "supported"),
    ]
    assert cohens_kappa(pairs) == pytest.approx(0.6154, abs=1e-3)


def test_wilson_interval_is_wide_for_small_samples():
    low, high = wilson_interval(36, 40)  # 90%
    assert 0.76 < low < 0.78 and 0.95 < high < 0.97
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_compare_separates_lenient_and_strict_errors():
    human = {"a": "unsupported", "b": "supported", "c": "no_claim", "d": "supported"}
    judge = {"a": "supported", "b": "unsupported", "c": "no_claim", "d": "supported", "x": "?"}
    result = compare(human, judge)
    assert (result["n"], result["agree"]) == (4, 2)
    assert result["lenient"] == ["a"]
    assert result["strict"] == ["b"]
    assert result["disagreements"] == ["a", "b"]


def test_unjudged_lists_reference_claims_the_judge_has_not_labelled():
    human = {"a#1": "supported", "a#2": "unsupported", "b#1": "no_claim"}
    assert unjudged(human, {"a#1": "supported"}) == ["a#2", "b#1"]
    # Extra judge labels (claims outside the sample) don't matter.
    assert unjudged(human, {**human, "c#1": "supported"}) == []
