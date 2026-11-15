"""Per-edition content tables (A2.3, schema.sql): what the keys allow and refuse, and the
in-place conversion of a database made before A2.3.

Needs the Postgres container; skipped when it isn't reachable. Everything runs as the owner
inside a transaction that is always rolled back: Postgres's DDL is transactional, so a test
can put the tables back in their pre-A2.3 shape, convert them, and leave the real database
exactly as it was.
"""

import psycopg
import pytest
from edition_rows import add_edition

from app.config import EMBEDDING_DIM
from app.db.connection import database_reachable, get_owner_connection, init_schema

pytestmark = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")

CONTENT_TABLES = ("course_prerequisites", "courses", "document_chunks")

# What a database made before A2.3 has: courses keyed on code alone, edges with no
# source, no foreign key from a content row to its edition. Constraint names are the
# ones Postgres gave the old CREATE TABLEs (read from the local database on 2026-11-15).
BEFORE_A2_3 = """
    ALTER TABLE course_prerequisites DROP CONSTRAINT course_prerequisites_course_fkey;
    ALTER TABLE course_prerequisites DROP CONSTRAINT course_prerequisites_pkey;
    ALTER TABLE course_prerequisites DROP COLUMN source;
    ALTER TABLE courses DROP CONSTRAINT courses_source_fkey;
    ALTER TABLE courses DROP CONSTRAINT courses_pkey;
    ALTER TABLE courses ADD CONSTRAINT courses_pkey PRIMARY KEY (code);
    ALTER TABLE course_prerequisites ADD CONSTRAINT course_prerequisites_pkey
        PRIMARY KEY (course_code, prerequisite_code);
    ALTER TABLE course_prerequisites ADD CONSTRAINT course_prerequisites_course_code_fkey
        FOREIGN KEY (course_code) REFERENCES courses (code);
    ALTER TABLE document_chunks DROP CONSTRAINT document_chunks_source_fkey;
"""

AFTER_A2_3 = {
    ("course_prerequisites", "course_prerequisites_course_fkey",
     "FOREIGN KEY (source, course_code) REFERENCES courses(source, code)"),
    ("course_prerequisites", "course_prerequisites_pkey",
     "PRIMARY KEY (source, course_code, prerequisite_code)"),
    ("courses", "courses_pkey", "PRIMARY KEY (source, code)"),
    ("courses", "courses_source_fkey", "FOREIGN KEY (source) REFERENCES document_editions(id)"),
    ("document_chunks", "document_chunks_pkey", "PRIMARY KEY (id)"),
    ("document_chunks", "document_chunks_source_chunk_index_model_name_key",
     "UNIQUE (source, chunk_index, model_name)"),
    ("document_chunks", "document_chunks_source_fkey",
     "FOREIGN KEY (source) REFERENCES document_editions(id)"),
}  # fmt: skip


@pytest.fixture
def conn():
    connection = get_owner_connection()
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        yield connection
    connection.close()


def _keys(conn) -> set[tuple[str, str, str]]:
    rows = conn.execute(
        "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE contype IN ('p', 'f', 'u') AND conrelid::regclass::text = ANY(%s)",
        (list(CONTENT_TABLES),),
    ).fetchall()
    return set(rows)


def _edges(conn) -> list[tuple[str, str]]:
    return conn.execute(
        "SELECT course_code, prerequisite_code FROM course_prerequisites ORDER BY 1, 2"
    ).fetchall()


def _has_edge_source(conn) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'course_prerequisites' AND column_name = 'source'"
        ).fetchone()
    )


def _add_course(conn, code: str, source: str) -> None:
    conn.execute(
        "INSERT INTO courses (code, department, title, credits, source) "
        "VALUES (%s, 'ZZZ', 'Test course', 3, %s)",
        (code, source),
    )


def test_the_schema_has_the_per_edition_keys(conn):
    assert _keys(conn) == AFTER_A2_3


def test_a_database_made_before_a2_3_is_converted_in_place(conn):
    add_edition(conn, "test_edition")
    _add_course(conn, "ZZZ 1001", "test_edition")
    _add_course(conn, "ZZZ 1002", "test_edition")
    conn.execute(
        "INSERT INTO course_prerequisites (course_code, prerequisite_code, source) "
        "VALUES ('ZZZ 1002', 'ZZZ 1001', 'test_edition')"
    )
    conn.execute(BEFORE_A2_3)
    assert not _has_edge_source(conn)
    edges_before = _edges(conn)
    courses_before = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()

    init_schema(conn)

    assert _keys(conn) == AFTER_A2_3
    assert _edges(conn) == edges_before  # no edge lost or added
    assert conn.execute("SELECT * FROM courses ORDER BY code").fetchall() == courses_before
    # Each edge took its course's edition.
    mismatched = conn.execute(
        "SELECT count(*) FROM course_prerequisites cp JOIN courses c "
        "ON c.code = cp.course_code AND c.source <> cp.source"
    ).fetchone()
    assert mismatched == (0,)
    assert conn.execute(
        "SELECT source FROM course_prerequisites WHERE course_code = 'ZZZ 1002'"
    ).fetchone() == ("test_edition",)


def test_a_conversion_that_fails_changes_nothing(conn):
    conn.execute(BEFORE_A2_3)
    # A chunk from an edition the registry doesn't know: the new foreign key refuses it.
    # Its own zero vector, not one borrowed from a real chunk: CI's database has none.
    conn.execute(
        "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, embedding) "
        "VALUES ('not_in_the_registry', 0, 'x', 'en', 'test-model', "
        "array_fill(0::real, ARRAY[%s])::vector)",
        (EMBEDDING_DIM,),
    )
    # conn.transaction() inside is a savepoint, so the outer transaction survives.
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        init_schema(conn)
    # One batch is one transaction: the course part, which ran first, was undone too.
    assert not _has_edge_source(conn)


def test_running_the_schema_again_changes_nothing(conn):
    before = _keys(conn)
    init_schema(conn)
    assert _keys(conn) == before


def test_two_editions_can_each_hold_the_same_course(conn):
    add_edition(conn, "test_old", document_id="test_catalog", status="superseded")
    add_edition(conn, "test_new", document_id="test_catalog", status="active")
    _add_course(conn, "ZZZ 1001", "test_old")
    _add_course(conn, "ZZZ 1001", "test_new")
    count = conn.execute("SELECT count(*) FROM courses WHERE code = 'ZZZ 1001'").fetchone()
    assert count == (2,)


def test_a_row_from_an_unknown_edition_is_refused(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _add_course(conn, "ZZZ 1001", "not_in_the_registry")


def test_an_edge_cannot_point_from_one_editions_course_into_another(conn):
    add_edition(conn, "test_old", document_id="test_catalog", status="superseded")
    add_edition(conn, "test_new", document_id="test_catalog", status="active")
    _add_course(conn, "ZZZ 1001", "test_old")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO course_prerequisites (course_code, prerequisite_code, source) "
            "VALUES ('ZZZ 1001', 'ZZZ 1000', 'test_new')"
        )


def test_an_edition_that_has_rows_cannot_be_deleted(conn):
    add_edition(conn, "test_edition")
    _add_course(conn, "ZZZ 1001", "test_edition")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("DELETE FROM document_editions WHERE id = 'test_edition'")
