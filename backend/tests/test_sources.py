"""Tests for source display info and source links (app.sources, GET /sources/...).

The reachability check is replaced, so these make no network requests.
"""

import httpx
from fastapi.testclient import TestClient

from app import main, sources
from app.sources import SOURCES, link_target, url_answers, with_display_info

CATALOG = "academic_catalog_2024_2025"


def test_the_catalog_link_opens_the_pdf_at_the_cited_page(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    assert link_target(CATALOG, 120) == SOURCES[CATALOG].url + "#page=120"
    assert link_target(CATALOG, None) == SOURCES[CATALOG].url


def test_if_the_pdf_does_not_answer_the_link_goes_to_the_catalog_landing_page(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: False)
    assert link_target(CATALOG, 120) == "https://aui.ma/academic-catalogs"


def test_web_pages_open_at_their_url_and_unknown_sources_have_none(monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    assert link_target("graduate_scholarships", None) == SOURCES["graduate_scholarships"].url
    assert link_target("not_a_source", 3) is None


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
        ]
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
    client = TestClient(main.app)

    response = client.get(f"/sources/{CATALOG}?page=67", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("#page=67")
    assert client.get("/sources/nope", follow_redirects=False).status_code == 404
