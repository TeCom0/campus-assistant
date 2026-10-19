"""Split cleaned document text (data/processed/*.txt) into overlapping chunks.

Chunks are the unit we'll embed and store in Phase 1's later steps. Each chunk
keeps track of which source file and page(s) it came from, so answers can cite
their source later, and of where it sits in the document: its LEVEL (general,
undergraduate or graduate) and its SECTION (the nearest heading above it).
A fixed-size window can cut a rule from its heading (the undergraduate repeat
rules are a table away from "Repeat Policy"), and parallel undergraduate and
graduate policies differ (repeat: C- or lower vs. B- or lower); without these,
a chunk doesn't say what it is about or whom it applies to.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.embeddings import count_tokens, get_model

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

MAX_CHUNK_CHARS = 1000
OVERLAP_CHARS = 150

PAGE_MARKER_RE = re.compile(r"--- page (\d+) ---\n")

# The catalog's part headings, as body lines on their own (the table of
# contents lists them too, followed by a page number, so an exact line match
# skips those). Everything before the undergraduate part (admissions,
# financial aid, add/drop, plagiarism, grading) is university-wide.
LEVEL_HEADINGS = {
    "AL AKHAWAYN UNDERGRADUATE STUDIES": "undergraduate",
    "AL AKHAWAYN GRADUATE STUDIES": "graduate",
    "ACADEMIC CENTERS AND INSTITUTES": "general",  # Language Center, faculty list
}
# How a level is written in a chunk's "Section:" line: the catalog's own part
# names. No words for "general": the part before the undergraduate studies
# mixes university-wide policies with financial aid for both levels, so a
# label like "All students" would sometimes be false.
LEVEL_LABELS = {"undergraduate": "Undergraduate Studies", "graduate": "Graduate Studies"}
# Sources with one level throughout (web pages have no part headings).
SOURCE_LEVELS = {"graduate_scholarships": "graduate"}
DEFAULT_LEVEL = "general"

# Repeated at the top of every catalog page; never a heading.
PAGE_HEADER_LINES = {"Al Akhawayn University", "www.aui.ma", "2024-", "2025"}
# Words a title-case heading leaves in lower case.
SMALL_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "per",
    "the", "to", "with",
}  # fmt: skip


@dataclass
class Chunk:
    source: str
    chunk_index: int
    text: str
    pages: list[int] = field(default_factory=list)  # empty for non-paginated (HTML) sources
    language: str = "en"  # TODO: derive per-source once non-English sources are added
    level: str = DEFAULT_LEVEL  # "general", "undergraduate" or "graduate"
    section: str | None = None  # nearest heading above the chunk's first line


def _split_into_pages(text: str) -> list[tuple[int | None, str]]:
    """Split processed text into (page_number, page_text) pairs.

    Files with '--- page N ---' markers (from PDF extraction) are split
    accordingly; files without markers (HTML sources) are returned as a
    single page with page_number=None.
    """
    matches = list(PAGE_MARKER_RE.finditer(text))
    if not matches:
        return [(None, text)]

    pages = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        pages.append((int(match.group(1)), text[start:end]))
    return pages


def _split_into_lines(text: str) -> list[str]:
    # Neither pypdf's nor BeautifulSoup's text extraction reliably produces
    # blank-line-separated paragraphs (both emit a single "\n" between lines),
    # so single lines -- not blank-line paragraphs -- are our smallest atomic
    # unit for packing into chunks.
    lines = [line.strip() for line in text.split("\n")]
    return [line for line in lines if line]


def looks_like_heading(line: str) -> bool:
    """A heading's shape: 1-8 words, title or upper case, no digits or punctuation.

    PDF extraction loses fonts, so shape and context (is_heading) are all there
    is. Excludes the page header, table header rows ("Course Code Course Name")
    and the abbreviation table ("Finance FIN"); names ("Hazzaz, Safia") and
    titles ("Mr. ...") are excluded by the punctuation rule.
    """
    words = line.split()
    if not 1 <= len(words) <= 8 or line in PAGE_HEADER_LINES:
        return False
    if re.search(r"[\d.,;:!?]", line) or not line[0].isupper() or "Course Code" in line:
        return False
    if not line.isupper() and re.search(r"\s[A-Z]{2,5}$", line):
        return False
    return all(w[0].isupper() or w.lower() in SMALL_WORDS or not w[0].isalpha() for w in words)


def _ends_sentence(line: str) -> bool:
    # Not ")": the probation table's "(may appeal)" cell precedes its "Not
    # Allowed" cell, which would then pass as the heading of the undergraduate
    # repeat rules printed after the table.
    return line[-1] in ".:;!?" or line in PAGE_HEADER_LINES or line.isdigit()


def _starts_text(line: str) -> bool:
    return len(line.split()) >= 6 or line.startswith("•")


def is_heading(previous: str, line: str, following: str) -> bool:
    """A heading-shaped line between the end of a sentence (or another heading)
    and the start of real text.

    The context keeps table cells ("Spring" between "Fall" and "Summer") and
    staff titles (after a name line) out. Measured on the catalog: 535
    headings, about 1 in 20 wrong in samples (mostly table header rows).
    """
    return (
        looks_like_heading(line)
        and (_ends_sentence(previous) or looks_like_heading(previous))
        and _starts_text(following)
    )


def assign_sections(source: str, lines: list[str]) -> list[tuple[str, str | None]]:
    """(level, section) in effect at each line of one document."""
    level = SOURCE_LEVELS.get(source, DEFAULT_LEVEL)
    section = None
    sections = []
    for i, line in enumerate(lines):
        if line in LEVEL_HEADINGS:
            level, section = LEVEL_HEADINGS[line], None
        elif 0 < i < len(lines) - 1 and is_heading(lines[i - 1], line, lines[i + 1]):
            section = line
        sections.append((level, section))
    return sections


def section_line(level: str, section: str | None, first_line: str) -> str | None:
    """The "Section: ..." line a chunk's text starts with, or None if it adds nothing.

    In the text, not only in metadata: the embedding, the keyword index
    (generated from `text`) and the model all read the text. The heading is
    left out when the chunk already starts with it.
    """
    parts = [LEVEL_LABELS[level]] if level in LEVEL_LABELS else []
    if section and section != first_line:
        parts.append(section)
    return "Section: " + " > ".join(parts) if parts else None


def chunk_text(source: str, text: str) -> list[Chunk]:
    """Chunk one document's text into overlapping, line-aligned windows."""
    lines: list[tuple[int | None, str]] = []
    for page_number, page_text in _split_into_pages(text):
        for line in _split_into_lines(page_text):
            lines.append((page_number, line))
    # Over the whole document, not per page: a heading's next line can be on
    # the next page.
    sections = assign_sections(source, [line for _, line in lines])

    chunks: list[Chunk] = []
    current: list[tuple[int, int | None, str]] = []  # (line number, page, line) in progress
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return

        chunk_str = "\n".join(line for _, _, line in current)
        pages = sorted({pg for _, pg, _ in current if pg is not None})
        # The section in effect at the chunk's first line; a heading further
        # down is already in the chunk's own text.
        level, section = sections[current[0][0]]
        prefix = section_line(level, section, current[0][2])
        if prefix:
            chunk_str = prefix + "\n" + chunk_str
        chunks.append(
            Chunk(
                source=source,
                chunk_index=len(chunks),
                text=chunk_str,
                pages=pages,
                level=level,
                section=section,
            )
        )

        # Carry the tail lines of this chunk into the next one (up to
        # OVERLAP_CHARS) so boundary-crossing context isn't lost.
        overlap: list[tuple[int, int | None, str]] = []
        overlap_len = 0
        for n, pg, line in reversed(current):
            if overlap_len + len(line) > OVERLAP_CHARS and overlap:
                break
            overlap.insert(0, (n, pg, line))
            overlap_len += len(line)
        current = overlap
        current_len = overlap_len

    for n, (page_number, line) in enumerate(lines):
        if current_len + len(line) > MAX_CHUNK_CHARS and current:
            flush()
        current.append((n, page_number, line))
        current_len += len(line)

    flush()
    return chunks


def chunk_all() -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for processed_file in sorted(PROCESSED_DIR.glob("*.txt")):
        text = processed_file.read_text(encoding="utf-8")
        source = processed_file.stem
        chunks = chunk_text(source, text)
        all_chunks.extend(chunks)
        print(f"chunked: {processed_file.name} -> {len(chunks)} chunks")
    return all_chunks


def save_chunks(chunks: list[Chunk]) -> None:
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in chunks)


def report_token_lengths(chunks: list[Chunk]) -> None:
    """Report how chunk sizes compare to the embedding model's token limit.

    Read dynamically from the model (not hardcoded) so this check can't
    silently go stale if the embedding model is ever changed again -- that's
    exactly how the previous model's 128-token limit went unnoticed against
    ~1000-char chunks.
    """
    limit = get_model().max_seq_length
    counts = count_tokens([c.text for c in chunks])
    over_limit = sum(1 for t in counts if t > limit)
    print(
        f"\ntoken length check ({get_model().tokenizer.name_or_path}, limit={limit}):\n"
        f"  min={min(counts)} max={max(counts)} mean={sum(counts) / len(counts):.1f}\n"
        f"  over limit: {over_limit}/{len(counts)} ({100 * over_limit / len(counts):.1f}%)"
    )


if __name__ == "__main__":
    all_chunks = chunk_all()
    save_chunks(all_chunks)
    print(f"\ntotal chunks: {len(all_chunks)} -> saved to {CHUNKS_PATH}")
    report_token_lengths(all_chunks)
