"""Tests for the blind hand-labelling helpers (app.evaluation.hand_labels):
what goes on the labelling page and when a labels file counts as complete
(which is what unlocks the judge on a hand-labelled run).
"""

from app.evaluation.hand_labels import labelling_items, missing_labels


def _answer(answer_id: str) -> dict:
    return {
        "id": answer_id,
        "language": "en",
        "question": "Q?",
        "answer": "A.",
        "passages": [],
        "error": None,
    }


def _claim(answer_id: str, n: int, auto_label=None) -> dict:
    return {
        "claim_id": f"{answer_id}#{n}",
        "id": answer_id,
        "set": "regression",
        "text": "t",
        "kind": "own",
        "markers": [1],
        "block_type": "paragraph",
        "auto_label": auto_label,
    }


def test_page_leaves_out_auto_labelled_claims_empty_answers_and_the_set():
    answers = [_answer("a"), _answer("crashed"), _answer("all_auto")]
    claims = [_claim("a", 1), _claim("a", 2, "unsupported"), _claim("all_auto", 1, "unsupported")]
    items = labelling_items(answers, claims)
    assert [i["id"] for i in items] == ["a"]
    assert [c["claim_id"] for c in items[0]["claims"]] == ["a#1"]
    assert "set" not in items[0]["claims"][0]  # knowing it's a regression question could bias


def test_missing_labels_lists_unlabelled_claims_and_abstains():
    items = labelling_items([_answer("a")], [_claim("a", 1), _claim("a", 2)])
    labels = {"claims": {"a#1": {"label": "supported"}, "a#2": {"label": "maybe"}}, "answers": {}}
    assert missing_labels(labels, items) == ["a (abstains)", "a#2"]


def test_complete_labels_have_nothing_missing():
    items = labelling_items([_answer("a")], [_claim("a", 1)])
    labels = {
        "claims": {"a#1": {"label": "no_claim", "note": ""}},
        "answers": {"a": {"abstains": False}},
    }
    assert missing_labels(labels, items) == []
