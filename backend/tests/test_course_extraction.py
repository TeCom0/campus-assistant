"""Tests for prerequisite-edge extraction from catalog prerequisite text."""

from app.ingestion.courses import extract_prerequisite_edges


def _edges_for(prereq_text: str) -> list[tuple[str, str]]:
    return extract_prerequisite_edges({"CSC 4307": {"prerequisites_text": prereq_text}})


def test_codes_written_without_a_space_are_found():
    # Real catalog wording for CSC 4307.
    edges = _edges_for("CSC3326, CSC3351 or MIS 3301, and Junior classification")
    assert edges == [
        ("CSC 4307", "CSC 3326"),
        ("CSC 4307", "CSC 3351"),
        ("CSC 4307", "MIS 3301"),
    ]


def test_ordinary_words_followed_by_a_number_are_not_codes():
    assert _edges_for("Junior classification and 2024 catalog rules") == []
