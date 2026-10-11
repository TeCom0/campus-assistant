"""Tests for the blind hand-labelling helpers (app.evaluation.hand_labels):
what goes on the labelling page and when a labels file counts as complete
(which is what unlocks the judge on a hand-labelled run).
"""

from collections import Counter

from app.evaluation.hand_labels import (
    MAX_SAMPLED_PER_ANSWER,
    labelling_items,
    missing_labels,
    stratified_sample,
)


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


# --- the 40-claim sample that replaced run 1's too-quick full pass ----------


def _pool() -> list[dict]:
    """60 claims over 12 answers: 30 uncited/fr, 20 own/en, 10 block/en."""
    claims = []
    for n in range(60):
        kind, language = (
            ("uncited", "fr") if n < 30 else ("own", "en") if n < 50 else ("block", "en")
        )
        claims.append({"claim_id": f"c{n}", "id": f"a{n % 12}", "kind": kind, "language": language})
    return claims


def test_sample_is_reproducible_and_proportional():
    pool = _pool()
    sample = stratified_sample(pool, 12, seed=1)
    assert sample == stratified_sample(pool, 12, seed=1)
    assert len(sample) == len(set(sample)) == 12
    kinds = Counter(next(c["kind"] for c in pool if c["claim_id"] == i) for i in sample)
    assert kinds == {"uncited": 6, "own": 4, "block": 2}  # 30/60, 20/60, 10/60 of 12


def test_sample_takes_at_most_three_claims_per_answer():
    pool = [{"claim_id": f"c{n}", "id": "a0" if n < 10 else f"a{n}", "kind": "own",
             "language": "en"} for n in range(20)]  # fmt: skip
    sample = stratified_sample(pool, 10, seed=3)
    assert sum(1 for i in sample if int(i[1:]) < 10) <= MAX_SAMPLED_PER_ANSWER


def test_sample_page_shows_only_the_sampled_claims():
    items = labelling_items(
        [_answer("a"), _answer("b")], [_claim("a", 1), _claim("a", 2), _claim("b", 1)], {"a#2"}
    )
    assert [(i["id"], [c["claim_id"] for c in i["claims"]]) for i in items] == [("a", ["a#2"])]
