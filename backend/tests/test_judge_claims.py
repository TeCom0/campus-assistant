"""Tests for the faithfulness judge's deterministic parts
(app.evaluation.judge_claims): prompt building, the quote check, and merging
the judge's verdicts into per-claim results. No LLM calls.
"""

from app.evaluation.judge_claims import (
    AnswerVerdict,
    ClaimVerdict,
    build_prompt,
    merge_verdicts,
    quote_found,
)

PASSAGE_TEXT = (
    "Instructors should be informed before the absence to agree with the student on a suitable "
    "time\nand manner for makeup, should it be necessary. A maximum of three of these absences "
    "per\nsemester may be authorized."
)
PASSAGES = [
    {"marker": 1, "source": "catalog", "pages": [101], "texts": [PASSAGE_TEXT]},
    {"marker": 2, "source": "catalog", "pages": [120], "texts": ["Repeated courses count once."]},
]


def _claim(n: int, markers: list[int], kind: str = "own", auto_label=None) -> dict:
    return {
        "claim_id": f"q#{n}",
        "text": f"claim {n}",
        "kind": kind,
        "markers": markers,
        "auto_label": auto_label,
    }


def _verdict(n: int, label: str, quote: str = "") -> ClaimVerdict:
    return ClaimVerdict(claim_id=f"q#{n}", label=label, evidence_quote=quote, reason="r")


def test_prompt_lists_each_claims_scope_and_every_text_of_a_repeated_marker():
    passages = [{"marker": 1, "source": "catalog", "pages": [222], "texts": ["entry", "entry+"]}]
    prompt = build_prompt("Q?", "A [1].", passages, [_claim(1, [1]), _claim(2, [], "uncited")])
    assert "- id: q#1 | check against: [1] | claim: claim 1" in prompt
    assert "- id: q#2 | check against: all passages | claim: claim 2" in prompt
    assert "entry\n--- (same marker, returned again with more text) ---\nentry+" in prompt


def test_quote_found_ignores_line_breaks_case_and_typographic_quotes():
    texts = [PASSAGE_TEXT]
    assert quote_found("a maximum of three of these absences per semester", texts)
    assert quote_found("A maximum of three ... may be authorized.", texts)
    assert quote_found(
        "Instructors should be informed before the absence",
        ["Instructors should be informed before the absence"],
    )
    assert quote_found("the student’s record", ["the student's record"])


def test_quote_found_rejects_invented_or_out_of_order_text():
    texts = [PASSAGE_TEXT]
    assert not quote_found("A maximum of five of these absences", texts)
    assert not quote_found("may be authorized ... Instructors should", texts)
    assert not quote_found("", texts)


def test_supported_with_a_verifiable_quote_stays_supported():
    claims = [_claim(1, [1])]
    verdict = AnswerVerdict(
        abstains=False, verdicts=[_verdict(1, "supported", "A maximum of three of these absences")]
    )
    assert merge_verdicts(claims, PASSAGES, verdict)[0]["label"] == "supported"


def test_quote_from_a_passage_the_claim_did_not_cite_makes_it_unsupported():
    # Cites [2], but the judge's evidence is in [1].
    claims = [_claim(1, [2])]
    verdict = AnswerVerdict(
        abstains=False, verdicts=[_verdict(1, "supported", "A maximum of three of these absences")]
    )
    result = merge_verdicts(claims, PASSAGES, verdict)[0]
    assert (result["judge_label"], result["label"], result["flag"]) == (
        "supported",
        "unsupported",
        "quote_not_found",
    )


def test_uncited_claims_are_checked_against_all_passages():
    claims = [_claim(1, [], "uncited")]
    verdict = AnswerVerdict(abstains=False, verdicts=[_verdict(1, "supported", "count once")])
    assert merge_verdicts(claims, PASSAGES, verdict)[0]["label"] == "supported"


def test_auto_labelled_missing_and_duplicate_verdicts():
    claims = [_claim(1, [9], auto_label="unsupported"), _claim(2, [1]), _claim(3, [1])]
    verdict = AnswerVerdict(
        abstains=False,
        verdicts=[_verdict(2, "no_claim"), _verdict(2, "supported", "x"), _verdict(7, "no_claim")],
    )
    results = merge_verdicts(claims, PASSAGES, verdict)
    assert [(r["label"], r["flag"]) for r in results] == [
        ("unsupported", "invalid_citation"),
        ("no_claim", None),  # the first verdict for q#2 counts
        (None, "no_verdict"),  # the judge skipped q#3 (and q#7 isn't a claim)
    ]
