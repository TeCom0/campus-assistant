"""What the UI shows for each source document, and where its link goes.

Source cards name a document the way a person would and open it at the cited
page. Links go through the API (GET /sources/{source}?page=N) rather than
straight to aui.ma, so that if the catalog PDF moves or fails, the link falls
back to the catalog's landing page instead of a dead page.

URLs are the ones in data/sources.md; the landing page lists every catalog
edition (checked 2026-10-19: all return HTTP 200).
"""

import time
from dataclasses import dataclass

import httpx

from app.ingestion.chunk import LEVEL_LABELS


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    # Where the link goes if `url` doesn't answer (None: no fallback, use url).
    fallback_url: str | None = None
    # A PDF opened at the cited page with #page=N.
    paged: bool = False


SOURCES = {
    "academic_catalog_2024_2025": Source(
        title="Academic Catalog 2024–2025",
        url="https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en",
        fallback_url="https://aui.ma/academic-catalogs",
        paged=True,
    ),
    "graduate_scholarships": Source(
        title="Graduate Scholarships (AUI website)",
        url="https://aui.ma/admission-aid/graduates/scholarships",
    ),
    "prestigious_scholarships": Source(
        title="Prestigious Scholarships (AUI website)",
        url="https://aui.ma/prestigious-scholarship",
    ),
}

# Remember whether a URL answered, so a page of source cards doesn't send one
# request to aui.ma per click.
CHECK_TTL_SECONDS = 3600
CHECK_TIMEOUT_SECONDS = 5
_checked: dict[str, tuple[float, bool]] = {}


def url_answers(url: str, now: float | None = None) -> bool:
    """Does `url` return a 2xx (after redirects)? Cached for CHECK_TTL_SECONDS."""
    now = time.monotonic() if now is None else now
    cached = _checked.get(url)
    if cached and now - cached[0] < CHECK_TTL_SECONDS:
        return cached[1]
    try:
        response = httpx.head(url, follow_redirects=True, timeout=CHECK_TIMEOUT_SECONDS)
        ok = response.is_success
    except httpx.HTTPError:
        ok = False
    _checked[url] = (now, ok)
    return ok


def link_target(source_id: str, page: int | None) -> str | None:
    """Where a source card's link should go; None for an unknown source."""
    source = SOURCES.get(source_id)
    if source is None:
        return None
    if source.fallback_url and not url_answers(source.url):
        return source.fallback_url
    if source.paged and page is not None:
        return f"{source.url}#page={page}"
    return source.url


def with_display_info(citations: list[dict]) -> list[dict]:
    """Citations as the UI shows them: plus the document's title and a link path.

    The link is relative to the API (GET /sources/...), so it follows the
    fallback above. A citation's first page is the one opened.
    """
    shown = []
    for c in citations:
        source = SOURCES.get(c["source"])
        pages = c.get("pages") or []
        link = f"/sources/{c['source']}" + (f"?page={pages[0]}" if pages else "")
        shown.append(
            {
                **c,
                "title": source.title if source else c["source"],
                "section": section_path(c.get("level"), c.get("section")),
                "link": link if source else None,
            }
        )
    return shown


def section_path(level: str | None, section: str | None) -> str | None:
    """ "Undergraduate Studies › Repeat Policy", as on the chunk's Section line."""
    parts = [LEVEL_LABELS[level]] if level in LEVEL_LABELS else []
    if section:
        parts.append(section)
    return " › ".join(parts) or None
