"""Loaders (A2.4 step 1): one interface for every format, and today's text unchanged.

The last two tests are the step's proof on the real files: the loaders rebuild every
registered edition's processed text, and from it every chunk in chunks.jsonl, byte for
byte. They need data/raw, which is gitignored, so they skip where it isn't (CI).
"""

import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from app.ingestion.chunk import chunk_text
from app.ingestion.loaders import (
    Block,
    Loader,
    PdfLoader,
    UnsupportedFormat,
    WebLoader,
    load_text,
    loader_for,
    to_chunker_text,
)
from app.registry import load_registry

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"
DATA = Path(__file__).resolve().parents[2] / "data"


def test_both_loaders_have_the_loader_shape():
    assert isinstance(PdfLoader(), Loader)
    assert isinstance(WebLoader(), Loader)


def test_loader_for_picks_by_format():
    assert isinstance(loader_for("pdf", Path("a.pdf")), PdfLoader)
    assert isinstance(loader_for("html", Path("a.html")), WebLoader)


@pytest.mark.parametrize("format", ["docx", "xlsx", "txt", "", "PDF"])
def test_unknown_format_is_refused_naming_the_file(format):
    with pytest.raises(UnsupportedFormat) as refused:
        loader_for(format, Path("budget.docx"))
    assert "budget.docx" in str(refused.value)
    assert "supported: html, pdf" in str(refused.value)


def test_pdf_gives_one_block_per_page_with_its_number():
    blocks = PdfLoader().load(FIXTURES / "fixture_finance_fees.pdf")
    assert [(b.kind, b.page) for b in blocks] == [("text", 1), ("text", 2)]
    assert blocks[0].text.startswith("Student Fees and Payments\n")
    assert blocks[1].text.startswith("Refunds\n")


def test_an_empty_pdf_page_keeps_its_block_and_number(tmp_path):
    # The real files have no page without text, so build one: dropping it would shift
    # every later page number in the citations.
    spec = importlib.util.spec_from_file_location("make_pdf", FIXTURES / "make_fixture_pdf.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    path = tmp_path / "gap.pdf"
    path.write_bytes(generator.build_pdf([["first page"], [], ["third page"]]))

    blocks = PdfLoader().load(path)
    assert [(b.page, b.text) for b in blocks] == [(1, "first page"), (2, ""), (3, "third page")]
    assert to_chunker_text(blocks) == (
        "--- page 1 ---\nfirst page\n\n--- page 2 ---\n\n\n--- page 3 ---\nthird page"
    )


def test_web_page_drops_the_noise_tags():
    [block] = WebLoader().load(FIXTURES / "fixture_dining_guide.html")
    assert block.page is None
    assert "Campus Dining Guide" in block.text
    for noise in ("should be stripped", "font-weight", "Site header", "Home", "Footer"):
        assert noise not in block.text


def test_paged_text_has_a_marker_per_page():
    blocks = [
        Block("text", "one", page=1),
        Block("text", "", page=2),
        Block("text", "three", page=3),
    ]
    assert to_chunker_text(blocks) == (
        "--- page 1 ---\none\n\n--- page 2 ---\n\n\n--- page 3 ---\nthree"
    )


def test_web_text_joins_blocks_by_newline():
    assert to_chunker_text([Block("text", "a\nb"), Block("text", "c")]) == "a\nb\nc"
    assert to_chunker_text([]) == ""


def test_mixed_paged_and_unpaged_blocks_are_refused():
    with pytest.raises(ValueError):
        to_chunker_text([Block("text", "a", page=1), Block("text", "b")])


# --- On the real files ------------------------------------------------------------


def _registered_files():
    editions = load_registry().editions
    return [(e, DATA / "raw" / e.filename) for e in editions]


needs_raw = pytest.mark.skipif(
    not all(path.exists() for _, path in _registered_files()), reason="data/raw not present"
)


@pytest.fixture(scope="module")
def loaded_texts() -> dict[str, str]:
    return {e.id: load_text(path, e.format) for e, path in _registered_files()}


@needs_raw
def test_loaders_rebuild_the_processed_text_byte_for_byte(loaded_texts):
    for edition_id, text in loaded_texts.items():
        saved = (DATA / "processed" / f"{edition_id}.txt").read_text(encoding="utf-8")
        assert text == saved, edition_id


@needs_raw
def test_loaded_text_chunks_to_chunks_jsonl_exactly(loaded_texts):
    lines = (DATA / "processed" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    saved = [json.loads(line) for line in lines]
    rebuilt = [
        asdict(chunk)
        for edition_id in sorted(loaded_texts)
        for chunk in chunk_text(edition_id, loaded_texts[edition_id])
    ]
    assert len(rebuilt) == 1161
    assert rebuilt == saved
