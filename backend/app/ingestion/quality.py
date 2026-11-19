"""The measured checks of the dry run (A2.4 step 5; CLAUDE.md, "A2.4 rule", check methods).

Each function measures one thing on an edition's text and decides nothing; ingest.py
compares the numbers with the limits below and gives the verdict. The methods were
written in the rule before any of them was computed. The values that come from today's
files were measured once, on 2026-11-19, from the 2024-2025 catalog:

- near-empty pages: 9 of 435 (pages 1, 10, 26, 41, 80, 84, 91, 96, 100: cover and
  divider pages, under 4 characters each once the page header is removed);
- table-like pages: 11 of 435 (22-24, 133, 139, 154, 220, 221, 354, 371, 372);
- U+FFFD and mojibake: 0 in all three files;
- headings: 533 in the catalog, 4 and 7 in the two web pages (no previous edition, so
  report only);
- the longest chunk: 396 tokens, under the model's 512.
"""

from collections import Counter

from app.ingestion.chunk import (
    PAGE_MARKER_RE,
    ChunkSettings,
    _split_into_lines,
    _split_into_pages,
    is_heading,
    join_tables,
)
from app.ingestion.courses import COURSE_CODE_RE

# Scanned or image-only: a page with fewer non-whitespace characters than this, once its
# page-header lines are removed, is near-empty. The edition is refused when the share of
# such pages is above the larger of 5% and twice the catalog's.
NEAR_EMPTY_CHARS = 50
CATALOG_NEAR_EMPTY_SHARE = 9 / 435
NEAR_EMPTY_LIMIT = max(0.05, 2 * CATALOG_NEAR_EMPTY_SHARE)

# Table-like PDF pages (D6): at least 10 non-empty lines of 3 words or fewer, making up at
# least 60% of the page's non-empty lines. Refused above 1.25 times the catalog's share,
# until B1 brings a table-aware PDF extractor.
TABLE_LIKE_SHORT_WORDS = 3
TABLE_LIKE_MIN_SHORT_LINES = 10
TABLE_LIKE_MIN_SHARE = 0.6
CATALOG_TABLE_LIKE_SHARE = 11 / 435
TABLE_LIKE_LIMIT = 1.25 * CATALOG_TABLE_LIKE_SHARE

# Encoding: U+FFFD plus mojibake (UTF-8 read as Latin-1/Windows-1252), per 10,000
# characters.
ENCODING_LIMIT_PER_10K = 1.0
MOJIBAKE = ("Ã", "â€")

# Headings: refused below this share of the previous edition's count.
HEADINGS_FLOOR = 0.8


def pages_of(text: str) -> list[tuple[int, list[str]]]:
    """A paged text's pages, each as its non-empty lines, stripped. A web page has no
    pages: []."""
    if not PAGE_MARKER_RE.search(text):
        return []
    return [(number, _split_into_lines(page)) for number, page in _split_into_pages(text)]


def header_lines(pages: list[tuple[int, list[str]]], declared: frozenset[str]) -> frozenset[str]:
    """The page-header lines to ignore when measuring a page: the layout's own when it
    declares them (the catalog's), otherwise every line found on more than half the pages.

    With fewer than 2 pages nothing can be called repeated: on one page every line would
    be "on more than half the pages", and the whole page would count as header.
    """
    if declared:
        return declared
    if len(pages) < 2:
        return frozenset()
    seen = Counter(line for _, lines in pages for line in set(lines))
    return frozenset(line for line, count in seen.items() if count > len(pages) / 2)


def near_empty_pages(pages: list[tuple[int, list[str]]], headers: frozenset[str]) -> list[int]:
    """Pages with fewer than NEAR_EMPTY_CHARS non-whitespace characters outside the page
    header: what a scanned page, with no text layer, looks like."""
    return [
        number
        for number, lines in pages
        if sum(len("".join(line.split())) for line in lines if line not in headers)
        < NEAR_EMPTY_CHARS
    ]


def table_like_pages(pages: list[tuple[int, list[str]]]) -> list[int]:
    """Pages that look like a table flattened into one cell per line, which pypdf can't
    rebuild (D6)."""
    found = []
    for number, lines in pages:
        short = sum(1 for line in lines if len(line.split()) <= TABLE_LIKE_SHORT_WORDS)
        if short >= TABLE_LIKE_MIN_SHORT_LINES and short >= TABLE_LIKE_MIN_SHARE * len(lines):
            found.append(number)
    return found


def encoding_errors(text: str) -> int:
    """Replacement characters plus mojibake sequences."""
    return text.count("�") + sum(text.count(sequence) for sequence in MOJIBAKE)


def count_headings(text: str, settings: ChunkSettings) -> int:
    """How many lines the chunker takes as a section heading (part headings excluded),
    found on the same units chunk_text reads: pages split into lines, tables joined."""
    units = [
        line
        for _, line in join_tables(
            [
                (number, line)
                for number, page in _split_into_pages(text)
                for line in _split_into_lines(page)
            ]
        )
    ]
    rules = settings.rules
    return sum(
        1
        for i in range(1, len(units) - 1)
        if units[i] not in rules.level_headings
        and is_heading(units[i - 1], units[i], units[i + 1], rules)
    )


def codes_in_text(text: str) -> set[str]:
    """Every course code written anywhere in a text, as "ABC 1234"."""
    return {f"{m.group(1)} {m.group(2)}" for m in COURSE_CODE_RE.finditer(text)}
