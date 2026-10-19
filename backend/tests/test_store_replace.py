"""Tests for store.replace_rows: the full replace used after re-chunking.

Needs the Postgres container; skipped when it isn't reachable. Everything runs
inside a transaction that is always rolled back (force_rollback), with fake
model names, so the real chunks are never touched. init_schema runs inside it
too, so the level/section columns exist even on a database loaded before them.
"""

import psycopg
import pytest

from app.config import EMBEDDING_DIM
from app.db.connection import get_connection, init_schema
from app.ingestion.store import UPSERT_SQL, chunk_row, replace_rows, update_sections

MODEL = "test-replace-model"
OTHER_MODEL = "test-other-model"


def _db_available() -> bool:
    try:
        get_connection().close()
        return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Postgres not reachable")


def _chunk(index: int, text: str, level: str = "general") -> dict:
    return {"source": "test_source", "chunk_index": index, "text": text, "pages": [],
            "language": "en", "level": level, "section": None, "sections": []}  # fmt: skip


def _row(index: int, text: str, model: str, level: str = "general") -> tuple:
    return chunk_row(_chunk(index, text, level), [0.0] * EMBEDDING_DIM, model)


def _texts(conn, model: str) -> list[str]:
    rows = conn.execute(
        "SELECT text FROM document_chunks WHERE model_name = %s ORDER BY chunk_index", (model,)
    ).fetchall()
    return [r[0] for r in rows]


@pytest.fixture
def conn():
    connection = get_connection()
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        with connection.cursor() as cur:
            cur.executemany(
                UPSERT_SQL,
                [_row(0, "old 0", MODEL), _row(1, "old 1", MODEL), _row(0, "keep", OTHER_MODEL)],
            )
        yield connection
    connection.close()


def test_replace_removes_rows_the_new_chunking_no_longer_has(conn):
    deleted = replace_rows(conn, [_row(0, "new 0", MODEL)], MODEL)

    assert deleted == 2
    assert _texts(conn, MODEL) == ["new 0"]  # the old chunk 1 is gone, not left stale
    assert _texts(conn, OTHER_MODEL) == ["keep"]  # other models are untouched


def test_a_failing_insert_leaves_the_table_as_it_was(conn):
    bad = _row(0, "new 0", MODEL, level="postgraduate")  # violates the level CHECK
    with pytest.raises(psycopg.errors.CheckViolation):
        replace_rows(conn, [_row(5, "new 5", MODEL), bad], MODEL)

    assert _texts(conn, MODEL) == ["old 0", "old 1"]  # the delete was undone too


def test_update_sections_changes_only_the_metadata(conn):
    # The fixture's other model is left alone; this one is updated in place.
    loaded = [
        {**_chunk(0, "old 0"), "sections": ["A", "B"]},
        {**_chunk(1, "old 1"), "sections": ["C"]},
    ]
    assert update_sections(conn, loaded, MODEL) == 2
    rows = conn.execute(
        "SELECT text, sections FROM document_chunks WHERE model_name = %s ORDER BY chunk_index",
        (MODEL,),
    ).fetchall()
    assert rows == [("old 0", ["A", "B"]), ("old 1", ["C"])]


def test_update_sections_refuses_when_a_chunk_text_differs(conn):
    changed = [{**_chunk(0, "NEW TEXT"), "sections": ["A"]}, {**_chunk(1, "old 1"), "sections": []}]
    with pytest.raises(SystemExit, match="use --replace"):
        update_sections(conn, changed, MODEL)
    sections = conn.execute(
        "SELECT sections FROM document_chunks WHERE model_name = %s", (MODEL,)
    ).fetchall()
    assert all(s == [] for (s,) in sections)  # nothing written
