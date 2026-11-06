"""The API really reads the synced tables, as its own role. The one test here that
needs them: everything else about cards and links runs on rows in memory
(tests/test_sources.py). CI syncs before the tests, so there this must not skip.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import main, sources
from app.config import CAMPUS_API_USER
from app.db.connection import database_reachable, get_connection, get_owner_connection
from app.registry import load_registry, read_source_rows
from app.sources import load_sources


@pytest.fixture
def synced_database():
    if not database_reachable():
        if os.environ.get("CI"):
            pytest.fail("the API's reads must not go unproven in CI")
        pytest.skip("Postgres not reachable")
    conn = get_connection(register_vector_type=False)
    try:
        if conn.execute("SELECT count(*) FROM document_editions").fetchone()[0] == 0:
            if os.environ.get("CI"):
                pytest.fail("CI must sync before the tests")
            pytest.skip("run python -m app.registry sync --initial first")
        yield conn
    finally:
        conn.close()


def test_load_sources_reads_the_synced_tables_as_the_apis_role(synced_database):
    user = synced_database.execute("SELECT current_user").fetchone()[0]
    assert user == CAMPUS_API_USER
    loaded = load_sources()
    for edition in load_registry().editions:
        assert loaded[edition.id].title == edition.card_title
        assert loaded[edition.id].url == edition.source_url
        assert loaded[edition.id].fallback_url == edition.fallback_url
        assert loaded[edition.id].paged == (edition.format == "pdf")


def test_the_link_endpoint_redirects_from_the_synced_tables(synced_database, monkeypatch):
    monkeypatch.setattr(sources, "url_answers", lambda url: True)
    edition = load_registry().course_tables_edition()
    client = TestClient(main.app)
    response = client.get(f"/sources/{edition.id}?page=67", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{edition.source_url}#page=67"
    assert client.get("/sources/not_an_edition", follow_redirects=False).status_code == 404


def test_the_read_returns_each_status_and_leaves_out_a_non_public_document(synced_database):
    # On the owner's connection, in a transaction that is rolled back: no other test or
    # request ever sees these statuses.
    owner = get_owner_connection()
    edition = load_registry().course_tables_edition()
    try:
        with owner.transaction(force_rollback=True):
            owner.execute(
                "UPDATE document_editions SET status = 'withdrawn' WHERE id = %s", (edition.id,)
            )
            rows = {row.edition_id: row for row in read_source_rows(owner)}
            assert rows[edition.id].status == "withdrawn"

            owner.execute(
                "UPDATE documents SET visibility = 'non_public' WHERE id = %s",
                (edition.document_id,),
            )
            rows = {row.edition_id: row for row in read_source_rows(owner)}
            assert edition.id not in rows
    finally:
        owner.close()
