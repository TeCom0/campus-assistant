"""Tests for the adjudication files (app.evaluation.adjudication): only the
disagreements, the right passages, and decisions that are never overwritten."""

from app.evaluation import adjudication
from app.evaluation.adjudication import (
    blind_items,
    build_items,
    check_decisions,
    checked_against,
    decisions_template,
    render_blind_markdown,
    render_markdown,
)

PASSAGES = [
    {"marker": 1, "source": "catalog", "pages": [101], "texts": ["Three absences per semester."]},
    {"marker": 2, "source": "catalog", "pages": [120], "texts": ["Short.", "Longer, with more."]},
]
ANSWERS = {"q": {"question": "Q?", "answer": "A [1].", "passages": PASSAGES}}
CLAIMS = {
    "q#1": {"id": "q", "text": "claim one", "kind": "own", "markers": [1]},
    "q#2": {"id": "q", "text": "claim two", "kind": "uncited", "markers": []},
    "q#3": {"id": "q", "text": "claim three", "kind": "own", "markers": [2]},
}
REFERENCE = {
    "claims": {
        "q#1": {"label": "supported"},
        "q#2": {"label": "no_claim", "note": "a refusal"},
        "q#3": {"label": "supported"},
    }
}


def _result(label, judge_label=None, flag=None, quote=""):
    return {"label": label, "judge_label": judge_label or label, "flag": flag,
            "evidence_quote": quote, "reason": "r"}  # fmt: skip


JUDGE = {
    "q#1": _result("supported", quote="Three absences"),  # agrees: not an item
    "q#2": _result("unsupported", "supported", "quote_not_found", "invented"),
    "q#3": _result("unsupported"),
}


def test_only_disagreements_become_items_with_both_labels():
    items = build_items(REFERENCE, JUDGE, CLAIMS, ANSWERS)
    assert [i["claim_id"] for i in items] == ["q#2", "q#3"]
    first = items[0]
    assert (first["human_label"], first["human_note"]) == ("no_claim", "a refusal")
    assert (first["judge_label"], first["judge_final"], first["flag"]) == (
        "supported", "unsupported", "quote_not_found",
    )  # fmt: skip


def test_claims_are_shown_with_their_own_passages_or_all_when_uncited():
    assert checked_against(CLAIMS["q#3"], PASSAGES) == [PASSAGES[1]]
    assert checked_against(CLAIMS["q#2"], PASSAGES) == PASSAGES


def test_markdown_has_every_text_of_the_claims_passages_and_the_quote_check():
    items = build_items(REFERENCE, JUDGE, CLAIMS, ANSWERS)
    md = render_markdown(1, "judge-model", items)
    assert "Short." in md and "Longer, with more." in md  # both texts of marker 2
    assert "FAILED -- quote not found" in md
    assert "'invented'" in md


def test_template_has_no_decisions_and_check_reports_them():
    items = build_items(REFERENCE, JUDGE, CLAIMS, ANSWERS)
    decisions = decisions_template(1, "judge-model", items)
    assert decisions["claims"]["q#2"] == {
        "original": "no_claim", "judge_raw": "supported", "judge": "unsupported",
        "decision": None, "note": "",
    }  # fmt: skip
    assert len(check_decisions(decisions)) == 2
    decisions["claims"]["q#2"]["decision"] = "no_claim"
    decisions["claims"]["q#3"]["decision"] = "mostly supported"  # not a label
    assert [p.split(":")[0] for p in check_decisions(decisions)] == ["q#3"]


def test_existing_decisions_are_never_overwritten(tmp_path, monkeypatch):
    out = tmp_path / "adjudications_run1.json"
    out.write_text('{"claims": {"q#2": {"decision": "no_claim"}}}', encoding="utf-8")
    monkeypatch.setattr(adjudication, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(adjudication, "reference_labels_path", lambda run: tmp_path / "ref.json")
    (tmp_path / "ref.json").write_text('{"claims": {}}', encoding="utf-8")
    for name in ("judgements_run1.jsonl", "claims_run1.jsonl", "answers_run1.jsonl"):
        (tmp_path / name).write_text("", encoding="utf-8")
    adjudication.write_files(1)
    assert out.read_text(encoding="utf-8") == '{"claims": {"q#2": {"decision": "no_claim"}}}'


def test_blind_items_cover_only_new_disagreements_with_a_correct_key():
    current = {"q#1": "supported", "q#2": "no_claim", "q#3": "supported", "q#4": "unsupported"}
    judge = {
        "q#1": _result("supported"),  # agrees
        "q#2": _result("unsupported"),  # disagrees, but already adjudicated
        "q#3": _result("unsupported"),  # new disagreement
        "q#4": _result("supported"),  # new disagreement
    }
    items, key = blind_items(current, judge, already={"q#2"})
    assert [i["claim_id"] for i in items] == ["q#3", "q#4"]
    for item in items:
        labels = {key[item["claim_id"]][side]: item[side] for side in ("A", "B")}
        assert labels == {"reference": current[item["claim_id"]],
                          "judge": judge[item["claim_id"]]["label"]}  # fmt: skip


def test_blind_order_is_random_but_reproducible():
    current = {f"q#{n}": "supported" for n in range(20)}
    judge = {cid: _result("unsupported") for cid in current}
    _, key = blind_items(current, judge, already=set(), seed=1)
    assert {k["A"] for k in key.values()} == {"reference", "judge"}  # both orders occur
    assert blind_items(current, judge, already=set(), seed=1)[1] == key


def test_blind_page_shows_neither_the_judges_quote_nor_its_reason():
    claims = {"q#3": {"id": "q", "text": "claim three", "kind": "own", "markers": [2]}}
    items = [{"claim_id": "q#3", "A": "unsupported", "B": "supported"}]
    md = render_blind_markdown(1, items, claims, ANSWERS)
    assert "**Label A:** unsupported | **Label B:** supported" in md
    assert "Longer, with more." in md  # the passage is there
    assert "quote" not in md.lower() and "reason" not in md.lower()
