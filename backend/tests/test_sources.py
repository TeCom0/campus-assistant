"""Tests for source display info and source links (app.sources, GET /sources/...).

No database: the code takes the registry's rows as an argument, so these give it rows
in memory. The reachability check is replaced, so they make no network requests.
tests/test_sources_api.py proves the API really reads the synced tables.
"""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main, sources
from app.registry import RegistryError, SourceRow, load_registry
from app.sources import (
    link_target,
    load_sources,
    section_path,
    sources_from_rows,
    url_answers,
    with_display_info,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "examples"

CATALOG = "academic_catalog_2024_2025"
CATALOG_URL = "https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en"
GRADUATE = "graduate_scholarships"
GRADUATE_URL = "https://aui.ma/admission-aid/graduates/scholarships"


def _row(status: str = "active", edition_id: str = CATALOG) -> SourceRow:
    return SourceRow(
        edition_id=edition_id,
        card_title="Academic Catalog 2024–2025",
        source_url=CATALOG_URL,
        fallback_url="https://aui.ma/academic-catalogs",
        format="pdf",
        status=status,
    )


ROWS = [
    _row(),
    SourceRow(
        edition_id=GRADUATE,
        card_title="Graduate Scholarships (AUI website)",
        source_url=GRADUATE_URL,
        fallback_url=None,
        format="html",
        status="active",
    ),
]
SOURCES = sources_from_rows(ROWS)


def _rows_from_the_real_file() -> list[SourceRow]:
    return [
        SourceRow(
            edition_id=edition.id,
            card_title=edition.card_title,
            source_url=edition.source_url,
            fallback_url=edition.fallback_url,
            format=edition.format,
            status="active",
        )
        for edition in load_registry().editions
    ]


def test_the_catalog_link_opens_the_pdf_at_the_cited_page(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    assert link_target(CATALOG, 120, SOURCES) == CATALOG_URL + "#page=120"
    assert link_target(CATALOG, None, SOURCES) == CATALOG_URL


def test_if_the_pdf_does_not_answer_the_link_goes_to_the_catalog_landing_page(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: False)
    assert link_target(CATALOG, 120, SOURCES) == "https://aui.ma/academic-catalogs"


def test_web_pages_open_at_their_url_and_unknown_sources_have_none(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    assert link_target(GRADUATE, None, SOURCES) == GRADUATE_URL
    assert link_target("not_a_source", 3, SOURCES) is None


def test_only_a_pdf_opens_at_a_page(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    assert link_target(GRADUATE, 5, SOURCES) == GRADUATE_URL


@pytest.mark.parametrize(
    ("status", "expected"),
    [("active", 302), ("superseded", 302), ("draft", 404), ("withdrawn", 404)],
)
def test_the_endpoint_for_each_edition_status(monkeypatch, status, expected):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    monkeypatch.setattr(main, "load_sources", lambda: sources_from_rows([_row(status)]))
    response = TestClient(main.app).get(f"/sources/{CATALOG}?page=3", follow_redirects=False)
    assert response.status_code == expected
    if expected == 302:
        assert response.headers["location"] == CATALOG_URL + "#page=3"


@pytest.mark.parametrize(
    ("status", "linked"),
    [("active", True), ("superseded", True), ("draft", False), ("withdrawn", False)],
)
def test_a_card_for_each_edition_status(status, linked):
    known = sources_from_rows([_row(status)])
    card = with_display_info([{"marker": 1, "source": CATALOG, "pages": [3]}], known)[0]
    if linked:
        assert card["title"] == "Academic Catalog 2024–2025"
        assert card["link"] == f"/sources/{CATALOG}?page=3"
    else:
        assert card["title"] == CATALOG
        assert card["link"] is None


def test_empty_registry_tables_are_an_error_not_a_page_of_bare_ids(monkeypatch):
    class _Connection:
        def close(self):
            pass

    monkeypatch.setattr(sources, "get_connection", lambda **kwargs: _Connection())
    monkeypatch.setattr(sources, "read_source_rows", lambda conn: [])
    with pytest.raises(RegistryError, match="empty"):
        load_sources()


def test_load_sources_uses_the_rows_it_read(monkeypatch):
    closed = []

    class _Connection:
        def close(self):
            closed.append(True)

    monkeypatch.setattr(sources, "get_connection", lambda **kwargs: _Connection())
    monkeypatch.setattr(sources, "read_source_rows", lambda conn: ROWS)
    assert load_sources() == SOURCES
    assert closed == [True]


@pytest.mark.parametrize("path", sorted(EXAMPLES_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_saved_examples_keep_the_title_and_link_they_were_saved_with(path):
    # They replay in the UI with no API call, and their links hit /sources/{id}. Any
    # title or link that changed here would be a visible change on the first screen.
    known = sources_from_rows(_rows_from_the_real_file())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["citations"], "the example must cite something for this to prove anything"
    for citation in saved["citations"]:
        card = with_display_info(
            [{"marker": 1, "source": citation["source"], "pages": citation["pages"]}], known
        )[0]
        assert card["title"] == citation["title"]
        assert card["link"] == citation["link"]


def test_the_real_file_gives_every_edition_todays_card_and_link(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    known = sources_from_rows(_rows_from_the_real_file())
    cards = {
        edition: with_display_info([{"marker": 1, "source": edition, "pages": pages}], known)[0]
        for edition, pages in (
            (CATALOG, [120]),
            (GRADUATE, []),
            ("prestigious_scholarships", []),
        )
    }
    assert cards[CATALOG]["title"] == "Academic Catalog 2024–2025"
    assert cards[CATALOG]["link"] == f"/sources/{CATALOG}?page=120"
    assert cards[GRADUATE]["title"] == "Graduate Scholarships (AUI website)"
    assert cards[GRADUATE]["link"] == f"/sources/{GRADUATE}"
    assert cards["prestigious_scholarships"]["title"] == "Prestigious Scholarships (AUI website)"
    assert link_target(CATALOG, 120, known) == CATALOG_URL + "#page=120"
    assert link_target(GRADUATE, None, known) == GRADUATE_URL
    assert (
        link_target("prestigious_scholarships", None, known)
        == "https://aui.ma/prestigious-scholarship"
    )


def test_reachability_is_checked_once_per_hour(monkeypatch):
    calls = []

    def head(url, **kwargs):
        calls.append(url)
        return httpx.Response(404, request=httpx.Request("HEAD", url))

    monkeypatch.setattr(sources.httpx, "head", head)
    monkeypatch.setattr(sources, "_checked", {})
    assert url_answers("https://x.test/a.pdf", now=0) is False
    assert url_answers("https://x.test/a.pdf", now=1800) is False
    assert len(calls) == 1  # cached
    url_answers("https://x.test/a.pdf", now=3601)
    assert len(calls) == 2  # expired


def test_a_network_error_counts_as_not_answering(monkeypatch):
    def head(url, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(sources.httpx, "head", head)
    monkeypatch.setattr(sources, "_checked", {})
    assert url_answers("https://x.test/b.pdf", now=0) is False


def test_citations_get_a_title_and_a_link_to_their_first_page():
    shown = with_display_info(
        [
            {
                "marker": 1,
                "source": CATALOG,
                "pages": [120, 121],
                "section": "Repeat Policy",
                "level": "undergraduate",
            },
            {"marker": 2, "source": "graduate_scholarships", "pages": []},
            {"marker": 3, "source": "mystery", "pages": None},
        ],
        SOURCES,
    )
    assert shown[0]["title"] == "Academic Catalog 2024–2025"
    assert shown[0]["link"] == f"/sources/{CATALOG}?page=120"
    assert shown[0]["section"] == "Undergraduate Studies › Repeat Policy"
    assert shown[1]["link"] == "/sources/graduate_scholarships"
    assert shown[1]["section"] is None
    assert (shown[2]["title"], shown[2]["link"]) == ("mystery", None)


def test_the_endpoint_redirects_and_is_not_a_question(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)

    def no_limits(request):
        raise AssertionError("a source link must not count against the limits")

    monkeypatch.setattr(main, "admit_question", no_limits)
    monkeypatch.setattr(main, "load_sources", lambda: SOURCES)
    client = TestClient(main.app)

    response = client.get(f"/sources/{CATALOG}?page=67", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("#page=67")
    assert client.get("/sources/nope", follow_redirects=False).status_code == 404


def test_the_card_path_shows_every_spanned_heading_up_to_three():
    assert section_path(
        "undergraduate", "Repeat Policy", ["Repeat Policy", "Academic Probation"]
    ) == ("Undergraduate Studies › Repeat Policy → Academic Probation")
    assert section_path("general", "Plagiarism", []) == "Plagiarism"  # older rows: section alone
    assert section_path("general", None, ["A", "B", "C", "D", "E"]) == "A → B → C → …"
    assert section_path("general", None, None) is None
