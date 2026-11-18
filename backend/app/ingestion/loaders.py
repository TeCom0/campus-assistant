"""Loaders: turn one downloaded file into Blocks (docs/architecture.md, 4.1).

A Block is the smallest unit a loader produces: a piece of text, its kind, and where it
came from in the file (a page, for a PDF). Every format has its own loader, and every
loader has the same shape, so the rest of ingestion doesn't care whether a document was a
PDF or a web page:

    extracted = extract(path, "html")   # load, then sanitise
    extracted.text                      # what chunk.py and courses.py read

Only PDF and HTML exist. Any other format raises UnsupportedFormat, naming the file and
what is supported: Word, Excel and PowerPoint wait for a real document to design against.

A2.4 step 1 moved today's extraction here unchanged. Step 3 adds sanitising (sanitise.py)
and keeps an HTML table whole, as one Markdown block with its header row (4.2). Today's
three files have no table and nothing to sanitise, so their text is still byte for byte
what it was (tests/test_loaders.py checks it on the real files).
"""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from bs4 import BeautifulSoup, NavigableString, Tag
from pypdf import PdfReader

from app.ingestion.sanitise import remove_hidden_elements, strip_invisible

# Elements whose text a reader of the page doesn't see as content.
HTML_NOISE_TAGS = ["script", "style", "nav", "header", "footer", "noscript"]

# Stands in for a table while the rest of the page's text is extracted: a line no real
# page contains (control characters), replaced by the table's block afterwards.
TABLE_PLACEHOLDER = "\x00table {}\x00"


@dataclass(frozen=True)
class Block:
    """One piece of a document's text, and where it is in the file."""

    kind: Literal["text", "heading", "table"]
    text: str  # for a table: Markdown, header row first
    page: int | None = None  # 1-based PDF page; None for a web page


@dataclass(frozen=True)
class Loaded:
    """A loader's result: the blocks, and what the loader removed as hidden."""

    blocks: list[Block]
    hidden_elements: int = 0  # HTML elements removed by sanitise.remove_hidden_elements


@runtime_checkable
class Loader(Protocol):
    """What every loader looks like. A Protocol is structural: any class with these
    two members is a Loader, with no inheritance needed."""

    formats: tuple[str, ...]

    def load(self, path: Path) -> Loaded: ...


class UnsupportedFormat(Exception):
    pass


class PdfLoader:
    formats = ("pdf",)

    def load(self, path: Path) -> Loaded:
        """One block per page, empty pages included: a page number must stay a page number."""
        reader = PdfReader(path)
        return Loaded(
            [
                Block("text", page.extract_text() or "", page=number)
                for number, page in enumerate(reader.pages, start=1)
            ]
        )


def _cell_text(cell: Tag) -> str:
    """A cell's text on one line, with a | that can't end the cell."""
    return " ".join(cell.get_text(" ", strip=True).split()).replace("|", "\\|")


def table_to_markdown(table: Tag) -> str:
    """A table as Markdown: its first row is the header (the <thead> row when there is
    one), then the separator line, then every other row. Short rows are padded, so every
    line has the same number of cells. A caption goes on the line above.

    The header always comes first, so a chunk that holds the table holds its header.
    """
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    header = table.thead.find("tr") if table.thead and table.thead.find("tr") else None
    if header is not None:
        rows.remove(header)
        rows.insert(0, header)
    cells = [[_cell_text(c) for c in row.find_all(["th", "td"], recursive=False)] for row in rows]
    cells = [row for row in cells if row]
    if not cells:
        return ""
    width = max(len(row) for row in cells)
    lines = ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in cells]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    caption = table.caption.get_text(" ", strip=True) if table.caption else ""
    return "\n".join(([caption] if caption else []) + lines)


class WebLoader:
    formats = ("html",)

    def load(self, path: Path) -> Loaded:
        """The visible text, one line per string in the page, without the noise tags or
        hidden elements; each table becomes one Markdown block where it stood."""
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for tag in soup(HTML_NOISE_TAGS):
            tag.decompose()
        hidden = remove_hidden_elements(soup)

        # Outermost tables only: a table inside a table is part of its cell's text.
        tables = [t for t in soup.find_all("table") if t.find_parent("table") is None]
        markdown = []
        for n, table in enumerate(tables):
            markdown.append(table_to_markdown(table))
            table.replace_with(NavigableString(TABLE_PLACEHOLDER.format(n)))

        blocks, text_lines = [], []
        for line in soup.get_text(separator="\n", strip=True).split("\n"):
            placeholder = [n for n in range(len(tables)) if line == TABLE_PLACEHOLDER.format(n)]
            if not placeholder:
                text_lines.append(line)
                continue
            if text_lines:
                blocks.append(Block("text", "\n".join(text_lines)))
                text_lines = []
            if markdown[placeholder[0]]:
                blocks.append(Block("table", markdown[placeholder[0]]))
        if text_lines and any(text_lines):
            blocks.append(Block("text", "\n".join(text_lines)))
        return Loaded(blocks, hidden_elements=hidden)


LOADERS: tuple[Loader, ...] = (PdfLoader(), WebLoader())


def loader_for(format: str, path: Path) -> Loader:
    """The loader for a format, or UnsupportedFormat naming the file."""
    for loader in LOADERS:
        if format in loader.formats:
            return loader
    supported = ", ".join(sorted(f for loader in LOADERS for f in loader.formats))
    raise UnsupportedFormat(
        f"{path.name}: format {format!r} isn't supported (supported: {supported})"
    )


def to_chunker_text(blocks: list[Block]) -> str:
    """The text chunk.py and courses.py read.

    A paged document gets a "--- page N ---" line before each page (chunk.PAGE_MARKER_RE
    and courses.PAGE_MARKER_RE read it back), pages separated by a blank line. A web
    page's blocks are joined by single newlines, as get_text(separator="\\n") does, so
    splitting a page into more blocks doesn't change its text.
    """
    paged = {block.page is not None for block in blocks}
    if len(paged) > 1:
        raise ValueError("a document's blocks are either all paged or none")
    if paged == {True}:
        return "\n\n".join(f"--- page {block.page} ---\n{block.text}" for block in blocks)
    return "\n".join(block.text for block in blocks)


@dataclass(frozen=True)
class Extracted:
    """A file's text, ready to chunk, and what sanitising removed from it."""

    text: str
    invisible_characters: int
    hidden_elements: int


def extract(path: Path, format: str) -> Extracted:
    """Load a file with its format's loader, sanitise it, and return the chunker's text."""
    loaded = loader_for(format, path).load(path)
    blocks, invisible = [], 0
    for block in loaded.blocks:
        text, removed = strip_invisible(block.text)
        blocks.append(replace(block, text=text))
        invisible += removed
    return Extracted(to_chunker_text(blocks), invisible, loaded.hidden_elements)


def load_text(path: Path, format: str) -> str:
    """extract(...).text: the chunker's text, sanitised."""
    return extract(path, format).text
