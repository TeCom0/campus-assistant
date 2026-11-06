"""What the UI shows for each source document, and where its link goes.

Source cards name a document the way a person would and open it at the cited
page. Links go through the API (GET /sources/{source}?page=N) rather than
straight to aui.ma, so that if the catalog PDF moves or fails, the link falls
back to the catalog's landing page instead of a dead page.

The titles and URLs come from the registry, through its synced tables (the file
isn't in the API's image). The functions below take those rows as an argument, so
they can be tested with rows in memory; only load_sources() touches the database.
"""

import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import httpx

from app.db.connection import get_connection
from app.ingestion.chunk import LEVEL_LABELS
from app.registry import RegistryError, SourceRow, read_source_rows

# Active: live. Superseded: no longer searched, but an answer or saved example already
# citing it keeps a working link. Draft and withdrawn editions act as unknown sources.
LINKABLE_STATUSES = {"active", "superseded"}


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    # Where the link goes if `url` doesn't answer (None: no fallback, use url).
    fallback_url: str | None = None
    # A PDF opened at the cited page with #page=N.
    paged: bool = False


def sources_from_rows(rows: Iterable[SourceRow]) -> dict[str, Source]:
    """The editions a card may link to, by id."""
    return {
        row.edition_id: Source(
            title=row.card_title,
            url=row.source_url,
            fallback_url=row.fallback_url,
            paged=row.format == "pdf",
        )
        for row in rows
        if row.status in LINKABLE_STATUSES
    }


def load_sources() -> dict[str, Source]:
    """The sources in force, read as the API's role. One small query per call.

    Empty tables are an error, not "no sources": every card would silently lose its
    title and link. The deploy script's gate should make this unreachable.
    """
    conn = get_connection(register_vector_type=False)
    try:
        rows = read_source_rows(conn)
    finally:
        conn.close()
    if not rows:
        raise RegistryError("the registry tables are empty")
    return sources_from_rows(rows)


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


def link_target(source_id: str, page: int | None, sources: Mapping[str, Source]) -> str | None:
    """Where a source card's link should go; None for an unknown source."""
    source = sources.get(source_id)
    if source is None:
        return None
    if source.fallback_url and not url_answers(source.url):
        return source.fallback_url
    if source.paged and page is not None:
        return f"{source.url}#page={page}"
    return source.url


def with_display_info(citations: list[dict], sources: Mapping[str, Source]) -> list[dict]:
    """Citations as the UI shows them: plus the document's title and a link path.

    The link is relative to the API (GET /sources/...), so it follows the
    fallback above. A citation's first page is the one opened.
    """
    shown = []
    for c in citations:
        source = sources.get(c["source"])
        pages = c.get("pages") or []
        link = f"/sources/{c['source']}" + (f"?page={pages[0]}" if pages else "")
        shown.append(
            {
                **c,
                "title": source.title if source else c["source"],
                "section": section_path(c.get("level"), c.get("section"), c.get("sections")),
                "link": link if source else None,
            }
        )
    return shown


# A chunk can span many headings (a list of course descriptions); a card shows
# the first few.
MAX_HEADINGS_SHOWN = 3


def section_path(
    level: str | None, section: str | None, sections: list[str] | None = None
) -> str | None:
    """ "Undergraduate Studies › Repeat Policy → Academic Probation": the level,
    then every heading the chunk spans (or its first-line section alone)."""
    headings = list(sections or ([section] if section else []))
    if len(headings) > MAX_HEADINGS_SHOWN:
        headings = headings[:MAX_HEADINGS_SHOWN] + ["…"]
    parts = [LEVEL_LABELS[level]] if level in LEVEL_LABELS else []
    if headings:
        parts.append(" → ".join(headings))
    return " › ".join(parts) or None
