"""Sanitising: remove what a reader of the document can't see (A2.4 step 3).

Text a human reviewer doesn't see, but a model reads, is how an instruction gets planted
in a document (docs/architecture.md, 4.4; threat IN-1). Sanitising removes two kinds, and
counts them, so the dry run (step 5) can report what it took out:

- invisible characters: zero-width characters, bidi controls (which can reorder what a
  reader sees) and the byte-order mark. Nothing else is touched: no Unicode
  normalisation, which would change the catalog's bytes.
- hidden HTML elements: the `hidden` attribute, `aria-hidden="true"`, or an inline style
  with display:none, visibility:hidden or font-size:0. CSS classes that hide text (from a
  stylesheet) aren't detected; PDF text hidden by a tiny or background-coloured font is
  B1's.

The method was fixed in CLAUDE.md ("A2.4 rule") before this code. Today's three files
hold none of either, so sanitising them changes nothing.
"""

import re

from bs4 import BeautifulSoup, Tag

# Written as numbers, so this file holds no invisible character itself.
INVISIBLE_CODE_POINTS = (
    0x200B, 0x200C, 0x200D, 0x2060,  # zero-width space, non-joiner, joiner, word joiner
    0xFEFF,  # byte-order mark (zero-width no-break space)
    0x200E, 0x200F, 0x061C,  # left-to-right, right-to-left and Arabic letter marks
    *range(0x202A, 0x202F),  # bidi embeddings and overrides, U+202A to U+202E
    *range(0x2066, 0x206A),  # bidi isolates, U+2066 to U+2069
)  # fmt: skip
INVISIBLE_CHARACTERS_RE = re.compile("[" + "".join(map(chr, INVISIBLE_CODE_POINTS)) + "]")

# font-size: a zero (0, 0px, 0.0em, .0rem), never 0.5em or 10px.
HIDING_STYLE_RE = re.compile(
    r"display\s*:\s*none"
    r"|visibility\s*:\s*hidden"
    r"|font-size\s*:\s*(0+(\.0*)?|\.0+)(px|pt|em|rem|%)?\s*(;|!|$)",
    re.IGNORECASE,
)


def strip_invisible(text: str) -> tuple[str, int]:
    """The text without invisible characters, and how many were removed."""
    cleaned, removed = INVISIBLE_CHARACTERS_RE.subn("", text)
    return cleaned, removed


def is_hidden(element: Tag) -> bool:
    """Is this element hidden from a reader by its own attributes?"""
    if element.has_attr("hidden"):
        return True
    if str(element.get("aria-hidden", "")).strip().lower() == "true":
        return True
    return bool(HIDING_STYLE_RE.search(str(element.get("style", ""))))


def remove_hidden_elements(soup: BeautifulSoup) -> int:
    """Remove every hidden element, with what is inside it; return how many.

    One at a time, in document order: an element inside a hidden one goes with it and
    isn't counted again.
    """
    removed = 0
    while (element := soup.find(is_hidden)) is not None:
        element.decompose()
        removed += 1
    return removed
