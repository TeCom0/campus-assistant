"""The generated scope text: right for today's registry, and refuses what it can't describe."""

import json
from dataclasses import replace

import pytest

from app import scope as scope_module
from app.registry import Registry, load_registry
from app.scope import (
    BACKEND_SCOPE_PATH,
    FRONTEND_SCOPE_PATH,
    ScopeError,
    load_scope,
    render_scope,
)


def _without(registry: Registry, document_id: str) -> Registry:
    return Registry(tuple(d for d in registry.documents if d.id != document_id))


def _with_domain(registry: Registry, document_id: str, domain: str) -> Registry:
    return Registry(
        tuple(replace(d, domain=domain) if d.id == document_id else d for d in registry.documents)
    )


@pytest.mark.parametrize("path", [BACKEND_SCOPE_PATH, FRONTEND_SCOPE_PATH])
def test_the_committed_files_match_the_registry(path):
    # Parsed, not bytes: a Windows checkout can give the file CRLF line endings.
    assert json.loads(path.read_text(encoding="utf-8")) == render_scope(load_registry())


def test_the_page_description_matches_the_generated_text():
    # index.html is read before any JavaScript runs, so it can't import the JSON. If this
    # fails after a registry change, copy meta_description from scope.json into index.html.
    html = (FRONTEND_SCOPE_PATH.parents[1] / "index.html").read_text(encoding="utf-8")
    description = render_scope(load_registry())["meta_description"]
    assert f'content="{description}"' in html


def test_todays_registry_gives_todays_text():
    scope = render_scope(load_registry())
    assert scope["prompt_documents"] == (
        "academic policies, course catalog descriptions, scholarship information"
    )
    assert scope["tool_documents"] == "academic catalog and scholarship pages"
    assert scope["tool_topics"] == (
        "academic policies, course requirements, grading, registration, admissions, "
        "or scholarships/fellowships"
    )
    assert scope["covers_en"] == "Al Akhawayn University's academic catalog and scholarship pages"
    assert scope["covers_fr"] == (
        "le catalogue académique et les pages de bourses de l'université Al Akhawayn"
    )
    assert scope["catalog_label"] == "2024–2025"
    assert scope["catalog_card_title"] == "Academic Catalog 2024–2025"
    assert scope["first_screen_documents"] == (
        "public 2024–2025 Academic Catalog and AUI's scholarship pages"
    )
    assert scope["about_documents"] == "2024–2025 Academic Catalog and scholarship pages"
    assert scope["meta_description"] == (
        "An unofficial student project: answers about Al Akhawayn University's public "
        "academic catalog and scholarship pages, in English or French, with their sources."
    )
    assert scope["ingestion_documents"] == "catalog PDF + 2 scholarship pages"


def test_one_page_left_reads_in_the_singular():
    # What A2.5 will do: the prestigious scholarships page goes.
    scope = render_scope(_without(load_registry(), "prestigious_scholarships"))
    assert scope["tool_documents"] == "academic catalog and scholarship page"
    assert scope["first_screen_documents"] == (
        "public 2024–2025 Academic Catalog and AUI's scholarship page"
    )
    assert scope["ingestion_documents"] == "catalog PDF + 1 scholarship page"
    assert scope["covers_fr"] == (
        "le catalogue académique et la page des bourses de l'université Al Akhawayn"
    )


def test_the_catalog_alone_needs_no_and():
    registry = _without(
        _without(load_registry(), "prestigious_scholarships"), "graduate_scholarships"
    )
    scope = render_scope(registry)
    assert scope["prompt_documents"] == "academic policies, course catalog descriptions"
    assert scope["tool_documents"] == "academic catalog"
    assert scope["about_documents"] == "2024–2025 Academic Catalog"
    assert scope["ingestion_documents"] == "catalog PDF"
    assert scope["tool_topics"].endswith("registration, or admissions")


def test_a_domain_with_no_wording_is_refused():
    registry = _with_domain(load_registry(), "graduate_scholarships", "dining")
    with pytest.raises(ScopeError, match="dining"):
        render_scope(registry)


def test_a_second_academic_document_is_refused():
    # The catalog's domain has no page wording, so it can't be guessed.
    registry = _with_domain(load_registry(), "graduate_scholarships", "academic")
    with pytest.raises(ScopeError, match="graduate_scholarships"):
        render_scope(registry)


def test_a_document_not_in_english_is_refused():
    # The search tool tells the model the documents are in English.
    registry = load_registry()
    page = registry.documents[1]
    french = replace(page, editions=(replace(page.editions[0], language="fr"),))
    documents = tuple(french if d.id == page.id else d for d in registry.documents)
    with pytest.raises(ScopeError, match="in English"):
        render_scope(Registry(documents))


def test_the_api_reads_the_json_and_never_the_registry_file(monkeypatch):
    # The API's image doesn't hold data/registry.toml.
    def no_registry():
        raise AssertionError("load_scope read the registry file")

    monkeypatch.setattr(scope_module, "load_registry", no_registry)
    assert load_scope()["tool_documents"] == "academic catalog and scholarship pages"


def test_a_document_with_two_editions_is_refused():
    # Which one is in force is the database's status (A2.3), not this file's to guess.
    registry = load_registry()
    catalog = registry.documents[0]
    second = replace(catalog.editions[0], id="academic_catalog_2025_2026", course_tables=False)
    two = replace(catalog, editions=(*catalog.editions, second))
    with pytest.raises(ScopeError, match="2 editions"):
        render_scope(Registry((two, *registry.documents[1:])))
