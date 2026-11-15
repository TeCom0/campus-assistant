"""replace_course_rows: one edition's courses and edges, replaced in one transaction (A2.3).

Needs the Postgres container; skipped when it isn't reachable. Everything runs as the owner in
a transaction that is always rolled back, with fake editions, so the real courses are never
touched.
"""

import psycopg
import pytest
from edition_rows import add_edition

from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.ingestion.courses import replace_course_rows

pytestmark = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")


def _course(code: str, source: str, prerequisites: str | None = None) -> dict:
    return {"code": code, "department": "ZZZ", "title": f"Course {code}", "credits": 3,
            "prerequisites_text": prerequisites, "corequisites_text": None, "page": 1,
            "source": source}  # fmt: skip


def _courses(*courses: dict) -> dict[str, dict]:
    return {c["code"]: c for c in courses}


@pytest.fixture
def conn():
    connection = get_owner_connection()
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        add_edition(connection, "test_a", document_id="test_catalog", status="active")
        add_edition(connection, "test_b", document_id="test_catalog", status="superseded")
        for edition in ("test_a", "test_b"):
            replace_course_rows(
                connection,
                edition,
                _courses(_course("ZZZ 1001", edition, "ZZZ 1002"), _course("ZZZ 1002", edition)),
                [("ZZZ 1001", "ZZZ 1002")],
            )
        yield connection
    connection.close()


def _rows(conn, edition: str) -> tuple[list[str], list[tuple[str, str]]]:
    courses = conn.execute(
        "SELECT code FROM courses WHERE source = %s ORDER BY code", (edition,)
    ).fetchall()
    edges = conn.execute(
        "SELECT course_code, prerequisite_code FROM course_prerequisites WHERE source = %s "
        "ORDER BY 1, 2",
        (edition,),
    ).fetchall()
    return [c for (c,) in courses], edges


def test_a_course_the_new_extraction_lost_is_removed(conn):
    deleted = replace_course_rows(conn, "test_a", _courses(_course("ZZZ 1001", "test_a")), [])

    assert deleted == (2, 1)
    assert _rows(conn, "test_a") == (["ZZZ 1001"], [])


def test_another_edition_is_left_alone(conn):
    replace_course_rows(conn, "test_a", _courses(_course("ZZZ 1001", "test_a")), [])

    assert _rows(conn, "test_b") == (["ZZZ 1001", "ZZZ 1002"], [("ZZZ 1001", "ZZZ 1002")])


def test_a_failing_insert_leaves_the_edition_as_it_was(conn):
    # An edge whose course isn't in the edition: its foreign key fails after the deletes ran.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        replace_course_rows(
            conn, "test_a", _courses(_course("ZZZ 1001", "test_a")), [("ZZZ 9999", "ZZZ 1001")]
        )

    assert _rows(conn, "test_a") == (["ZZZ 1001", "ZZZ 1002"], [("ZZZ 1001", "ZZZ 1002")])


def test_no_courses_is_refused(conn):
    with pytest.raises(ValueError, match="no courses"):
        replace_course_rows(conn, "test_a", {}, [])
    assert _rows(conn, "test_a")[0] == ["ZZZ 1001", "ZZZ 1002"]


def test_courses_labelled_with_another_edition_are_refused(conn):
    with pytest.raises(ValueError, match="passed as 'test_a'"):
        replace_course_rows(conn, "test_a", _courses(_course("ZZZ 1001", "test_b")), [])
