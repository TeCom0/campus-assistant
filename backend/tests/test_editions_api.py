"""GET /editions: the editions in force, for the interface's edition names (A2.3 sub-step 5).

With the real data it serves what the generated text says today, so the interface reads the
same either way. With two editions of a document, `activate` and its rollback change what it
serves on the next request. A database failure gets a fixed 503 that leaks nothing, and the
endpoint isn't counted against the demo limits.

The database tests need the Postgres container, seeded; skipped when it isn't reachable.
"""

import json

import psycopg
import pytest
from edition_rows import Lent, add_edition
from fastapi.testclient import TestClient

from app import main
from app.config import EMBEDDING_DIM
from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.registry import activate
from app.scope import BACKEND_SCOPE_PATH

needs_db = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")
client = TestClient(main.app)


def _served() -> dict:
    response = client.get("/editions")
    assert response.status_code == 200
    return {e["id"]: e for e in response.json()["editions"]}


@needs_db
def test_it_serves_what_the_generated_text_says_today():
    scope = json.loads(BACKEND_SCOPE_PATH.read_text(encoding="utf-8"))
    served = _served()
    catalogs = [e for e in served.values() if e["course_tables"]]
    assert len(catalogs) == 1
    catalog = catalogs[0]
    assert catalog["card_title"] == scope["catalog_card_title"]
    # The interface shows the registry's "2024-2025" with an en dash, as app/scope.py does.
    assert catalog["label"].replace("-", "–") == scope["catalog_label"]


@needs_db
def test_it_is_not_counted_against_the_demo_limits():
    conn = get_owner_connection()
    try:
        before = conn.execute("SELECT count(*) FROM question_log").fetchone()
        _served()
        after = conn.execute("SELECT count(*) FROM question_log").fetchone()
    finally:
        conn.close()
    assert before == after


@pytest.fixture
def two_editions(monkeypatch):
    connection = get_owner_connection(register_vector_type=True)
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        add_edition(connection, "test_old", document_id="test_catalog", status="active")
        add_edition(connection, "test_new", document_id="test_catalog", status="draft")
        add_edition(connection, "test_private", document_id="test_internal",
                    visibility="non_public")  # fmt: skip
        # A chunk each: activate refuses an edition with none, the rollback target included.
        for source in ("test_old", "test_new"):
            connection.execute(
                "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, "
                "embedding) VALUES (%s, 0, 'x', 'en', 'test-model', "
                "array_fill(0::real, ARRAY[%s])::vector)",
                (source, EMBEDDING_DIM),
            )
        lent = Lent(connection)
        monkeypatch.setattr(main, "get_connection", lambda **_: lent)
        yield connection
    connection.close()


def _test_ids() -> set[str]:
    return {i for i in _served() if i.startswith("test_")}


@needs_db
def test_it_serves_active_public_editions_only(two_editions):
    assert _test_ids() == {"test_old"}


@needs_db
def test_activation_and_rollback_change_what_it_serves(two_editions):
    activate(two_editions, "test_new", activated_by="test-maintainer")
    assert _test_ids() == {"test_new"}

    activate(two_editions, "test_old", activated_by="test-rollback")
    assert _test_ids() == {"test_old"}


def test_a_database_failure_gets_a_fixed_503_and_logs_nothing(monkeypatch, capsys, caplog):
    secret = "SECRETMARKER-in-a-database-message"

    def unreachable(**_):
        raise psycopg.OperationalError(secret)

    monkeypatch.setattr(main, "get_connection", unreachable)
    response = client.get("/editions")

    assert response.status_code == 503
    assert response.json() == {"message": "Editions unavailable."}
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err + caplog.text
