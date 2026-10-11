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


def test_chain_course_without_description_is_not_called_missing_from_the_catalog():
    # MTH 1305 is in the catalog (Gen Ed lists) but has no course-description
    # entry, so it has no title in our data. The old line said "not found in
    # the structured catalog data", which the model passed on as "not in the
    # catalog".
    text = _chain_text("ACC 2302")
    assert "  - MTH 1305 (step 2) -- referenced in the catalog but has no course description" in (
        text
    )
    assert "not found" not in text


def test_direct_lookup_of_referenced_course_without_description():
    reset_citation_counter()
    text, artifact = query_courses.func("MTH 1305")
    assert text.startswith("MTH 1305 is referenced in the catalog but has no course description")
    assert artifact == []


def test_repeated_lookup_returns_its_citation_with_the_new_text():
    # The second lookup adds the chain; a claim citing the marker may rest on
    # either text, so the evaluation needs both, under the same marker.
    reset_citation_counter()
    first_text, first = query_courses.func("ACC 2302")
    second_text, second = query_courses.func("ACC 2302", follow_prerequisites=True)
    assert first[0]["marker"] == second[0]["marker"] == 1
    assert first[0]["text"] == first_text
    assert second[0]["text"] == second_text
    assert "Full prerequisite chain" in second_text


def test_direct_lookup_of_unknown_code_still_says_not_found():
    reset_citation_counter()
    text, _ = query_courses.func("ZZZ 9999")
    assert text == "No course found with code 'ZZZ 9999' in AUI's course catalog."


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
