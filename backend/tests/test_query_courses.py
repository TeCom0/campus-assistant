"""Tests for query_courses' prerequisite chain, against the real courses data.

Needs the Postgres container (seeded with app.ingestion.courses); skipped
when it isn't reachable, so the rest of the suite still runs without it.
"""

import psycopg
import pytest

from app.agent.citations import reset_citation_counter
from app.agent.tools import _prerequisite_chain, query_courses
from app.db.connection import get_connection


def _db_available() -> bool:
    try:
        get_connection().close()
        return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Postgres not reachable")


def _chain_text(code: str) -> str:
    reset_citation_counter()
    text, _ = query_courses.func(code, follow_prerequisites=True)
    return text


def test_chain_shows_each_courses_own_catalog_wording():
    # The original bug: ACC 2301's "or" wasn't shown, so all three MTH
    # alternatives were presented as required.
    text = _chain_text("ACC 2302")
    assert (
        "ACC 2301: Accounting Principles I (step 1) -- requires: MTH 1305, or MTH 1303, or MTH 1304"
    ) in text


def test_each_course_is_listed_once():
    # SCM 5305 has the deepest chain in the catalog, with courses reachable
    # at more than one depth.
    chain_lines = [line for line in _chain_text("SCM 5305").splitlines() if line.startswith("  - ")]
    codes = [line.split()[1] + " " + line.split()[2].rstrip(":") for line in chain_lines]
    assert len(codes) == len(set(codes))


def test_cycle_in_the_data_does_not_loop():
    conn = get_connection()
    # force_rollback: the fake courses and the cycle never reach the real data.
    with conn.transaction(force_rollback=True):
        for code in ("ZZZ 1001", "ZZZ 1002", "ZZZ 1003"):
            conn.execute(
                "INSERT INTO courses (code, department, title, credits, source) "
                "VALUES (%s, 'ZZZ', 'Test course', 3, 'test')",
                (code,),
            )
        # 1001 -> 1002 -> 1003, and 1003 points back to both 1001 and 1002.
        for course, prereq in [
            ("ZZZ 1001", "ZZZ 1002"),
            ("ZZZ 1002", "ZZZ 1003"),
            ("ZZZ 1003", "ZZZ 1001"),
            ("ZZZ 1003", "ZZZ 1002"),
        ]:
            conn.execute(
                "INSERT INTO course_prerequisites (course_code, prerequisite_code) VALUES (%s, %s)",
                (course, prereq),
            )

        chain = _prerequisite_chain(conn, "ZZZ 1001")
    conn.close()

    assert [(code, depth) for code, depth, _, _ in chain] == [("ZZZ 1002", 1), ("ZZZ 1003", 2)]
