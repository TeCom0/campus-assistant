"""Tests for where chunks end (app.ingestion.chunk.chunk_text): after a sentence
end where possible, with the unfinished sentence moved whole to the next chunk
and an overlap of whole sentences; by lines, as before, when there is no
sentence end to cut at (tables, lists).

Synthetic lines are 110 characters long, so a 1000-character chunk holds 9 of
them and the 10th triggers the cut. The last tests run on the real catalog.
"""

from app.ingestion.chunk import (
    MAX_CHUNK_CHARS,
    PROCESSED_DIR,
    _split_into_lines,
    _split_into_pages,
    chunk_text,
)

SOURCE = "prestigious_scholarships"  # general level: no "Section:" line on synthetic text
CATALOG = "academic_catalog_2024_2025"


def _line(n: int, end: str = "") -> str:
    """A 110-character lower-case line (never a heading), ending with `end`."""
    text = f"line {n} "
    return (text + "x" * (110 - len(text) - len(end))) + end


def _lines_of(chunk) -> list[str]:
    return chunk.text.split("\n")


def test_a_full_chunk_ends_at_its_last_sentence_end_and_the_unfinished_sentence_moves_on():
    lines = [_line(i, ".") for i in range(6)] + [_line(6), _line(7), _line(8), _line(9, ".")]
    first, second = chunk_text(SOURCE, "\n".join(lines))

    assert _lines_of(first) == lines[:6]  # ends at line 5's period, not mid-sentence
    # Overlap: line 5, the whole last sentence (110 <= 150 chars); then the
    # unfinished sentence (lines 6-9) whole.
    assert _lines_of(second) == lines[5:]


def test_a_sentence_end_in_the_first_half_is_not_used_as_the_cut():
    lines = [_line(0, ".")] + [_line(i) for i in range(1, 10)]
    first = chunk_text(SOURCE, "\n".join(lines))[0]
    assert _lines_of(first) == lines[:9]  # cut by size, as before


def test_without_sentence_ends_the_overlap_is_the_last_line_as_before():
    lines = [_line(i) for i in range(10)]  # a table: no punctuation
    first, second = chunk_text(SOURCE, "\n".join(lines))

    assert _lines_of(first) == lines[:9]
    assert _lines_of(second) == lines[8:]  # one line of overlap (110 <= 150 < 220)


def test_no_overlap_needed_when_the_cut_falls_on_a_sentence_end_with_long_sentences():
    # Every sentence spans two lines (220 chars > the 150-char overlap window).
    lines = [_line(i, "." if i % 2 else "") for i in range(12)]
    chunks = chunk_text(SOURCE, "\n".join(lines))

    assert _lines_of(chunks[0])[-1].endswith(".")
    assert _lines_of(chunks[1])[0] == lines[len(_lines_of(chunks[0]))]  # starts a sentence


def _catalog_chunks_and_lines():
    text = (PROCESSED_DIR / f"{CATALOG}.txt").read_text(encoding="utf-8")
    lines = [line for _, page in _split_into_pages(text) for line in _split_into_lines(page)]
    return chunk_text(CATALOG, text), lines


def _body(chunk) -> list[str]:
    lines = _lines_of(chunk)
    return lines[1:] if lines[0].startswith("Section: ") else lines


def test_the_nine_semesters_sentence_is_no_longer_cut_in_the_real_catalog():
    chunks, _ = _catalog_chunks_and_lines()
    assert not any(_body(c)[0].startswith("semesters for undergraduates and 4") for c in chunks)
    assert any("committed for the 9\nsemesters for undergraduates" in c.text for c in chunks)


def test_every_catalog_line_is_in_a_chunk_and_no_chunk_is_over_budget():
    chunks, lines = _catalog_chunks_and_lines()
    covered, position = set(), 0
    for c in chunks:
        body = _body(c)
        while lines[position : position + len(body)] != body:
            position += 1
        covered.update(range(position, position + len(body)))
        assert sum(len(line) for line in body) <= MAX_CHUNK_CHARS
    assert covered == set(range(len(lines)))
