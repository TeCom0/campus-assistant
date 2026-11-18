"""Loaders: turn one downloaded file into a list of Blocks (docs/architecture.md, 4.1).

A Block is the smallest unit a loader produces: a piece of text, and where it came from
in the file (a page, for a PDF). Every format has its own loader, and every loader has
the same shape, so the rest of ingestion doesn't care whether a document was a PDF or a
web page:

    blocks = loader_for("pdf", path).load(path)
    text = to_chunker_text(blocks)      # what chunk.py and courses.py read

Only PDF and HTML exist. Any other format raises UnsupportedFormat, naming the file and
what is supported: Word, Excel and PowerPoint wait for a real document to design against.

A2.4 step 1 moves today's extraction here unchanged: to_chunker_text rebuilds, byte for
byte, the text clean.py wrote before (tests/test_loaders.py checks it on the real files).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from bs4 import BeautifulSoup
from pypdf import PdfReader

# Elements whose text a reader of the page doesn't see as content.
HTML_NOISE_TAGS = ["script", "style", "nav", "header", "footer", "noscript"]


@dataclass(frozen=True)
class Block:
    """One piece of a document's text, and where it is in the file."""

    kind: Literal["text", "heading", "table"]
    text: str
    page: int | None = None  # 1-based PDF page; None for a web page


@runtime_checkable
class Loader(Protocol):
    """What every loader looks like. A Protocol is structural: any class with these
    two members is a Loader, with no inheritance needed."""

    formats: tuple[str, ...]

    def load(self, path: Path) -> list[Block]: ...


class UnsupportedFormat(Exception):
    pass


class PdfLoader:
    formats = ("pdf",)

    def load(self, path: Path) -> list[Block]:
        """One block per page, empty pages included: a page number must stay a page number."""
        reader = PdfReader(path)
        return [
            Block("text", page.extract_text() or "", page=number)
            for number, page in enumerate(reader.pages, start=1)
        ]


class WebLoader:
    formats = ("html",)

    def load(self, path: Path) -> list[Block]:
        """The visible text, one line per string in the page, without the noise tags."""
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for tag in soup(HTML_NOISE_TAGS):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return [Block("text", text)] if text else []


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
    splitting a page into more blocks later doesn't change its text.
    """
    paged = {block.page is not None for block in blocks}
    if len(paged) > 1:
        raise ValueError("a document's blocks are either all paged or none")
    if paged == {True}:
        return "\n\n".join(f"--- page {block.page} ---\n{block.text}" for block in blocks)
    return "\n".join(block.text for block in blocks)


def load_text(path: Path, format: str) -> str:
    """Load a file with its format's loader and return the chunker's text."""
    return to_chunker_text(loader_for(format, path).load(path))
