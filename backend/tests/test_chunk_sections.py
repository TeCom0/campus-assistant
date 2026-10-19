"""Tests for the level and section each chunk gets (app.ingestion.chunk).

Heading cases are real lines of the processed catalog, positive and
negative, with their real neighbours. The last tests run on the whole
catalog file (tracked in git), pinning the two repeat policies that motivated
this: the undergraduate rules (C- or lower) sit a table away from their
heading, and the graduate rule (B- or lower) was given as the general one.
"""

import pytest

from app.ingestion.chunk import (
    PROCESSED_DIR,
    _split_into_lines,
    _split_into_pages,
    assign_sections,
    chunk_text,
    is_heading,
    looks_like_heading,
    section_line,
)
from app.ingestion.store import chunk_row

CATALOG = "academic_catalog_2024_2025"
SENTENCE = "Every student is responsible for knowing these regulations."
TEXT = "All courses taken at AUI, whether passed or failed, remain a permanent part of the record."


@pytest.mark.parametrize(
    "line",
    [
        "Repeat Policy",
        "Transfer Credit Maximums",
        "Minimum Grades for Transferable Courses",
        "Adding/Dropping Courses",
        "PROBATION REGULATIONS AND PROCEDURES",
        "Philosophy (PHI)",
    ],
)
def test_real_headings_have_a_headings_shape(line):
    assert looks_like_heading(line)


@pytest.mark.parametrize(
    "line",
    [
        "Hazzaz, Safia",  # staff list: comma
        "Mr. Mohammed FIKRAT",  # board list: period
        "Finance FIN",  # abbreviation table
        "Course Code Course Name",  # table header row
        "Al Akhawayn University",  # page header
        "2025",  # page header
        "SGPA < 2.0 Warning Allowed",  # table row: digits
        "requirements pertaining to their academic programs.",  # sentence
        "AL AKHAWAYN UNDERGRADUATE STUDIES 115",  # table of contents entry
    ],
)
def test_other_lines_do_not(line):
    assert not looks_like_heading(line)


def test_a_heading_sits_between_a_sentence_end_and_real_text():
    assert is_heading(SENTENCE, "Repeat Policy", TEXT)
    assert is_heading("Undergraduate Academic Regulations", "Student Classifications", TEXT)


@pytest.mark.parametrize(
    ("previous", "line", "following"),
    [
        ("(may appeal)", "Not Allowed", "SGPA ≥ 2.9 Under Watch Allowed Allowed Allowed"),
        ("Fall", "Spring", "Summer"),  # table cells
        ("Boukhare, Imane", "Counselor", "Guennoun, Adnane"),  # staff title under a name
        (SENTENCE, "Repeat Policy", "Semester of Unsatisfactory"),  # followed by a table
    ],
)
def test_heading_shaped_lines_out_of_context_are_not_headings(previous, line, following):
    assert not is_heading(previous, line, following)


def test_part_headings_set_the_level_and_reset_the_section():
    lines = [
        "AL AKHAWAYN UNDERGRADUATE STUDIES 115",  # table of contents: no switch
        SENTENCE,
        "Grading Policy",
        TEXT,
        "AL AKHAWAYN UNDERGRADUATE STUDIES",
        TEXT,
        SENTENCE,
        "Repeat Policy",
        TEXT,
        "AL AKHAWAYN GRADUATE STUDIES",
        TEXT,
        "ACADEMIC CENTERS AND INSTITUTES",
        TEXT,
    ]
    assert assign_sections(CATALOG, lines) == [
        ("general", None),
        ("general", None),
        ("general", "Grading Policy"),
        ("general", "Grading Policy"),
        ("undergraduate", None),
        ("undergraduate", None),
        ("undergraduate", None),
        ("undergraduate", "Repeat Policy"),
        ("undergraduate", "Repeat Policy"),
        ("graduate", None),
        ("graduate", None),
        ("general", None),
        ("general", None),
    ]


def test_web_pages_get_their_sources_level():
    assert assign_sections("graduate_scholarships", ["a", "b"])[0][0] == "graduate"
    assert assign_sections("prestigious_scholarships", ["a", "b"])[0][0] == "general"


def test_a_chunk_takes_the_section_of_its_first_line():
    body = "\n".join([SENTENCE, "Repeat Policy", *[TEXT] * 12, "Academic Probation", *[TEXT] * 12])
    chunks = chunk_text(CATALOG, body)

    assert len(chunks) > 2
    assert chunks[0].section is None  # starts before the first heading
    assert chunks[1].section == "Repeat Policy"
    assert chunks[-1].section == "Academic Probation"


def _catalog_lines() -> list[str]:
    text = (PROCESSED_DIR / f"{CATALOG}.txt").read_text(encoding="utf-8")
    return [line for _, page in _split_into_pages(text) for line in _split_into_lines(page)]


def test_both_repeat_policies_get_their_level_and_heading_in_the_real_catalog():
    lines = _catalog_lines()
    sections = assign_sections(CATALOG, lines)

    def section_of(fragment: str) -> tuple[str, str | None]:
        return next(sections[i] for i, line in enumerate(lines) if fragment in line)

    assert section_of("A student may repeat any course in which a C- or lower") == (
        "undergraduate",
        "Repeat Policy",
    )
    assert section_of("repeat any course in which a B- or lower") == ("graduate", "Repeat Policy")
    assert section_of("a maximum of 68 semester credits are transferable") == (
        "general",
        "Transfer Credit Maximums",
    )


def test_the_undergraduate_repeat_rules_chunk_is_tagged_although_its_heading_is_elsewhere():
    text = (PROCESSED_DIR / f"{CATALOG}.txt").read_text(encoding="utf-8")
    chunk = next(c for c in chunk_text(CATALOG, text) if "a C- or lower has been earned" in c.text)

    first_line, body = chunk.text.split("\n", 1)
    assert "Repeat Policy" not in body  # the heading is in the previous chunk
    assert (chunk.level, chunk.section) == ("undergraduate", "Repeat Policy")
    assert first_line == "Section: Undergraduate Studies > Repeat Policy"  # so the text says it


@pytest.mark.parametrize(
    ("level", "section", "first_line", "expected"),
    [
        ("undergraduate", "Repeat Policy", "SGPA ≥ 2.0", "Section: Undergraduate Studies > Repeat Policy"),
        ("graduate", None, "text", "Section: Graduate Studies"),
        ("general", "Transfer Credit Maximums", "text", "Section: Transfer Credit Maximums"),
        ("general", None, "text", None),  # nothing to add
        # The chunk starts with its own heading: not repeated.
        ("general", "Plagiarism", "Plagiarism", None),
        ("graduate", "Repeat Policy", "Repeat Policy", "Section: Graduate Studies"),
    ],
)  # fmt: skip
def test_section_line(level, section, first_line, expected):
    assert section_line(level, section, first_line) == expected


def test_chunk_text_starts_with_the_section_line_and_keeps_the_body():
    body = [SENTENCE, "Repeat Policy", TEXT]
    chunk = chunk_text(CATALOG, "\n".join(["AL AKHAWAYN GRADUATE STUDIES", *body]))[0]
    assert chunk.text == "Section: Graduate Studies\nAL AKHAWAYN GRADUATE STUDIES\n" + "\n".join(
        body
    )
    # General level, no heading yet: no prefix, the text is unchanged.
    assert chunk_text(CATALOG, "\n".join(body))[0].text == "\n".join(body)


def test_store_row_carries_level_and_section_and_rejects_old_chunks():
    chunk = {"source": CATALOG, "chunk_index": 3, "text": "t", "pages": [1], "language": "en",
             "level": "graduate", "section": "Repeat Policy"}  # fmt: skip
    row = chunk_row(chunk, [0.0] * 384)
    assert row[5:7] == ("graduate", "Repeat Policy")
    old = {k: v for k, v in chunk.items() if k not in ("level", "section")}
    with pytest.raises(KeyError):
        chunk_row(old, [0.0] * 384)
