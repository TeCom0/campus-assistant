"""Tests for the retrieval eval's text anchors (app.evaluation.run_retrieval_eval):
a result is a hit if it comes from the expected source and contains the anchor,
whatever its chunk number. No database needed.
"""

from dataclasses import dataclass

from app.evaluation.run_retrieval_eval import (
    anchor_locations,
    contains_anchor,
    load_eval_set,
    rank_of_first_match,
)

EXPECTED = {"source": "catalog", "anchor": "a maximum of 68 semester credits are transferable"}


@dataclass
class _Result:
    source: str
    chunk_index: int
    text: str


def test_anchor_matches_across_line_breaks_case_and_curly_quotes():
    text = (
        "For undergraduate programs, A MAXIMUM of 68\nsemester credits   are transferable to AUI."
    )
    assert contains_anchor("catalog", text, EXPECTED)
    quote = {"source": "catalog", "anchor": "another person's words"}
    assert contains_anchor("catalog", "present another person’s words", quote)


def test_anchor_must_come_from_the_expected_source():
    text = "a maximum of 68 semester credits are transferable"
    assert not contains_anchor("graduate_scholarships", text, EXPECTED)


def test_a_partial_anchor_is_not_a_hit():
    # What a chunk boundary cutting the sentence would leave.
    assert not contains_anchor("catalog", "a maximum of 68 semester", EXPECTED)


def test_rank_is_the_first_result_holding_the_anchor_whatever_its_chunk_number():
    results = [
        _Result("catalog", 7, "unrelated"),
        _Result("catalog", 999, "... a maximum of 68 semester credits are transferable ..."),
        _Result("catalog", 51, "a maximum of 68 semester credits are transferable"),
    ]
    assert rank_of_first_match(results, [EXPECTED]) == 2
    assert rank_of_first_match(results[:1], [EXPECTED]) is None


def test_any_of_several_anchors_counts():
    other = {"source": "catalog", "anchor": "unrelated"}
    assert rank_of_first_match([_Result("catalog", 7, "unrelated")], [EXPECTED, other]) == 1


def test_anchor_locations_list_every_chunk_holding_it_and_none_when_lost():
    question = {"id": "q", "expected": [EXPECTED]}
    chunks = [
        ("catalog", 50, "... a maximum of 68 semester credits are transferable"),  # overlap
        ("catalog", 51, "a maximum of 68 semester credits are transferable to AUI"),
        ("catalog", 52, "nothing"),
    ]
    assert anchor_locations([question], chunks)[0]["chunks"] == [50, 51]
    assert anchor_locations([question], chunks[2:])[0]["chunks"] == []


def test_every_eval_question_has_an_anchor_and_no_chunk_number():
    for q in load_eval_set():
        assert q["expected"], q["id"]
        for e in q["expected"]:
            assert set(e) == {"source", "anchor"}, q["id"]
            assert len(e["anchor"].split()) >= 6, q["id"]  # long enough to be distinctive
