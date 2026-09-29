"""Split cleaned document text (data/processed/*.txt) into overlapping chunks.

Chunks are the unit we'll embed and store in Phase 1's later steps. Each chunk
keeps track of which source file and page(s) it came from, so answers can cite
their source later.
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


@dataclass
class Chunk:
    source: str
    chunk_index: int
    text: str
    pages: list[int] = field(default_factory=list)  # empty for non-paginated (HTML) sources
    language: str = "en"  # TODO: derive per-source once non-English sources are added


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


def chunk_text(source: str, text: str) -> list[Chunk]:
    """Chunk one document's text into overlapping, line-aligned windows."""
    lines: list[tuple[int | None, str]] = []
    for page_number, page_text in _split_into_pages(text):
        for line in _split_into_lines(page_text):
            lines.append((page_number, line))

    chunks: list[Chunk] = []
    current: list[tuple[int | None, str]] = []  # (page, line) pairs in progress
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return

        chunk_str = "\n".join(line for _, line in current)
        pages = sorted({pg for pg, _ in current if pg is not None})
        chunks.append(Chunk(source=source, chunk_index=len(chunks), text=chunk_str, pages=pages))

        # Carry the tail lines of this chunk into the next one (up to
        # OVERLAP_CHARS) so boundary-crossing context isn't lost.
        overlap: list[tuple[int | None, str]] = []
        overlap_len = 0
        for pg, line in reversed(current):
            if overlap_len + len(line) > OVERLAP_CHARS and overlap:
                break
            overlap.insert(0, (pg, line))
            overlap_len += len(line)
        current = overlap
        current_len = overlap_len

    for page_number, line in lines:
        if current_len + len(line) > MAX_CHUNK_CHARS and current:
            flush()
        current.append((page_number, line))
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
