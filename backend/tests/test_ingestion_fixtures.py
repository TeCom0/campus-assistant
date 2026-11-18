"""The A2.4 fixture documents are what fixture_registry.toml says they are, and every
fixture question's anchor is in its document, once (CLAUDE.md, "A2.4 rule").

These run before any search touches the fixtures: they check the inputs of the scratch-
database check (items 6-8), not its results.
"""

import hashlib
import importlib.util
import json
import tomllib
from collections import Counter
from pathlib import Path

import pytest

from app.evaluation.run_retrieval_eval import normalize_text
from app.ingestion.loaders import load_text

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"


def _editions() -> list[dict]:
    with open(FIXTURES / "fixture_registry.toml", "rb") as f:
        registry = tomllib.load(f)
    return [edition for document in registry["document"] for edition in document["edition"]]


def _questions() -> list[dict]:
    return json.loads((FIXTURES / "fixture_questions.json").read_text(encoding="utf-8"))


def _text(edition: dict) -> str:
    return load_text(FIXTURES / f"{edition['id']}.{edition['format']}", edition["format"])


def test_three_fixture_documents_one_per_domain():
    with open(FIXTURES / "fixture_registry.toml", "rb") as f:
        documents = tomllib.load(f)["document"]
    assert sorted(d["domain"] for d in documents) == ["academic", "dining", "finance"]
    assert all(d["visibility"] == "public" for d in documents)
    assert all(e["source_url"].startswith("https://fixtures.invalid/") for e in _editions())


@pytest.mark.parametrize("edition", _editions(), ids=lambda e: e["id"])
def test_fixture_file_matches_its_registry_hash(edition):
    path = FIXTURES / f"{edition['id']}.{edition['format']}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == edition["sha256"]


@pytest.mark.parametrize("edition", _editions(), ids=lambda e: e["id"])
def test_fixture_says_it_is_not_a_university_document(edition):
    assert "TEST FIXTURE: invented text" in _text(edition)


def test_pdf_generator_rebuilds_the_committed_file():
    # Loaded by path: tests/ isn't a package, and CI runs `pytest`, not `python -m pytest`.
    spec = importlib.util.spec_from_file_location(
        "make_fixture_pdf", FIXTURES / "make_fixture_pdf.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    assert generator.build_pdf(generator.PAGES) == generator.OUT.read_bytes()


def test_three_questions_per_fixture_at_least_one_in_french():
    sources = Counter(q["expected"][0]["source"] for q in _questions())
    french = Counter(q["expected"][0]["source"] for q in _questions() if q["language"] == "fr")
    editions = {e["id"] for e in _editions()}
    assert sources == {edition: 3 for edition in editions}
    assert set(french) == editions
    assert all("question_en" in q for q in _questions() if q["language"] == "fr")


@pytest.mark.parametrize("question", _questions(), ids=lambda q: q["id"])
def test_anchor_is_in_its_fixture_exactly_once(question):
    texts = {e["id"]: normalize_text(_text(e)) for e in _editions()}
    [expected] = question["expected"]
    anchor = normalize_text(expected["anchor"])
    assert texts[expected["source"]].count(anchor) == 1
    # And in no other fixture, so a hit can only be the right document.
    assert all(anchor not in text for source, text in texts.items() if source != expected["source"])
