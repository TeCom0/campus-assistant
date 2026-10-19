"""Tests for saving example answers (app.generate_examples): nothing reaches the
app's folder unless approved, and the review shows each cited passage's text.
No LLM calls."""

import json

import pytest

from app import generate_examples


def _write(folder, example_id: str) -> None:
    (folder / f"{example_id}.json").write_text(json.dumps({"id": example_id}), encoding="utf-8")


def test_approve_copies_only_the_approved_examples(tmp_path, monkeypatch):
    review, saved = tmp_path / "review", tmp_path / "saved"
    review.mkdir()
    _write(review, "a")
    _write(review, "b")
    monkeypatch.setattr(generate_examples, "SAVED_DIR", saved)

    generate_examples.approve(["a"], review)
    assert sorted(p.name for p in saved.iterdir()) == ["a.json"]


def test_approve_refuses_an_example_that_was_never_generated(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_examples, "SAVED_DIR", tmp_path / "saved")
    with pytest.raises(SystemExit):
        generate_examples.approve(["missing"], tmp_path)


def test_review_puts_each_cited_passage_next_to_the_answer():
    saved = {
        "id": "x",
        "question": "Q?",
        "tool_calls": [{"tool": "search_documents", "label": 'Searching documents for "q"'}],
        "answer": "Yes [1].",
        "citations": [
            {"marker": 1, "title": "Academic Catalog 2024–2025", "section": "Repeat Policy"}
        ],
    }
    cited = [
        {"marker": 1, "source": "academic_catalog_2024_2025", "pages": [120], "text": "PASSAGE"}
    ]
    review = generate_examples.review_section(saved, cited)

    assert "Yes [1]." in review
    assert "[1] Academic Catalog 2024–2025, p. 120 -- Repeat Policy" in review
    assert "PASSAGE" in review
