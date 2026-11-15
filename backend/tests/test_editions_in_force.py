"""Only the editions in force reach a student (A2.3, app/editions.py, docs/architecture.md 5.2).

Next to an active edition, a superseded one and an active edition of a non-public document
each hold a chunk that matches the query exactly and their own courses. Searches and course
lookups must return the active public one only. Flipping the statuses inside the same
transaction then shows the filter reads the registry on every request, which is what makes a
rollback take effect on the next question.

Needs the Postgres container; skipped when it isn't reachable. Everything runs as the owner
in a transaction that is always rolled back. The search functions open their own connections,
so each test lends them this one instead: rows inserted here are invisible to any other
connection until a commit that never comes. The query embedding is fixed, so no model loads.
"""

import pytest
from edition_rows import Lent, add_edition

from app.agent import tools
from app.agent.citations import reset_citation_counter
from app.config import EMBEDDING_DIM
from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.retrieval import keyword_search, vector_search

pytestmark = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")

WORD = "zyxquorbal"  # in no real chunk, so only the test chunks match the keyword search
VECTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)  # every test chunk, and the query: distance 0
TEST_EDITIONS = {"test_old", "test_new", "test_private"}


def _chunk(conn, source: str) -> None:
    conn.execute(
        "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, embedding) "
        "VALUES (%s, 0, %s, 'en', 'test-model', %s::vector)",
        (source, f"Section: test\n{WORD} rules of {source}", str(VECTOR)),
    )


def _course(conn, code: str, title: str, source: str, prerequisites: str | None = None) -> None:
    conn.execute(
        "INSERT INTO courses (code, department, title, credits, prerequisites_text, source) "
        "VALUES (%s, 'ZZZ', %s, 3, %s, %s)",
        (code, title, prerequisites, source),
    )


def _edge(conn, course: str, prerequisite: str, source: str) -> None:
    conn.execute(
        "INSERT INTO course_prerequisites (course_code, prerequisite_code, source) "
        "VALUES (%s, %s, %s)",
        (course, prerequisite, source),
    )


@pytest.fixture
def conn(monkeypatch):
    connection = get_owner_connection(register_vector_type=True)
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        add_edition(connection, "test_old", document_id="test_catalog", status="superseded")
        add_edition(connection, "test_new", document_id="test_catalog", status="active")
        add_edition(
            connection, "test_private", document_id="test_internal", visibility="non_public"
        )
        for source in sorted(TEST_EDITIONS):
            _chunk(connection, source)
        # ZZZ 1001 is in both catalog editions, with a different chain in each; ZZZ 1002 was
        # removed in the new one (TL-4); ZZZ 1003 exists only in the non-public document.
        # The old edition also has its own ZZZ 1004, requiring ZZZ 1005: a walk from the new
        # ZZZ 1001 that left its edition would add ZZZ 1005, and a title join that did would
        # list ZZZ 1004 twice.
        _course(connection, "ZZZ 1001", "Old title", "test_old", "ZZZ 1002")
        _course(connection, "ZZZ 1002", "Removed course", "test_old")
        _edge(connection, "ZZZ 1001", "ZZZ 1002", "test_old")
        _course(connection, "ZZZ 1004", "Old prerequisite", "test_old", "ZZZ 1005")
        _edge(connection, "ZZZ 1004", "ZZZ 1005", "test_old")
        _course(connection, "ZZZ 1001", "New title", "test_new", "ZZZ 1004")
        _course(connection, "ZZZ 1004", "New prerequisite", "test_new")
        _edge(connection, "ZZZ 1001", "ZZZ 1004", "test_new")
        _course(connection, "ZZZ 1003", "Internal course", "test_private")

        lent = Lent(connection)
        for module in (vector_search, keyword_search, tools):
            monkeypatch.setattr(module, "get_connection", lambda **_: lent)
        monkeypatch.setattr(vector_search, "embed_query", lambda _query: VECTOR)
        yield connection
    connection.close()


def _test_sources(results) -> list[str]:
    return [r.source for r in results if r.source in TEST_EDITIONS]


def _lookup(code: str, follow: bool = True) -> tuple[str, list[dict], dict]:
    reset_citation_counter()
    return tools._look_up_course(code, follow)


def _supersede_new_and_reactivate_old(conn) -> None:
    # Two statements, in this order: the one-active-edition index is checked row by row.
    conn.execute("UPDATE document_editions SET status = 'superseded' WHERE id = 'test_new'")
    conn.execute("UPDATE document_editions SET status = 'active' WHERE id = 'test_old'")


def test_vector_search_returns_only_the_active_public_edition(conn):
    assert _test_sources(vector_search.search_vector("anything", top_k=10)) == ["test_new"]


def test_keyword_search_returns_only_the_active_public_edition(conn):
    assert _test_sources(keyword_search.search_keyword(WORD, top_k=10)) == ["test_new"]


def test_a_course_is_looked_up_in_the_active_edition(conn):
    text, citations, lookup = _lookup("ZZZ 1001")
    assert "New title" in text and "Old title" not in text
    assert citations[0]["source"] == "test_new"
    assert lookup["found"] == "course"


def test_the_prerequisite_chain_stays_inside_that_edition(conn):
    text, _, lookup = _lookup("ZZZ 1001")
    chain = text.split("Full prerequisite chain")[1]
    assert "ZZZ 1004: New prerequisite (step 1)" in chain
    assert "Old prerequisite" not in chain  # the title join stayed in the edition
    assert "ZZZ 1005" not in chain  # the walk didn't follow the old edition's edge
    assert "ZZZ 1002" not in chain
    assert lookup["chain_length"] == 1


def test_a_course_the_new_edition_removed_is_not_found(conn):
    # Not "no_description" either: no edge in force references it.
    _, citations, lookup = _lookup("ZZZ 1002")
    assert (citations, lookup["found"]) == ([], "not_found")


def test_a_course_of_a_non_public_document_is_not_found(conn):
    _, citations, lookup = _lookup("ZZZ 1003")
    assert (citations, lookup["found"]) == ([], "not_found")


def test_a_status_change_applies_to_the_next_search_and_lookup(conn):
    _supersede_new_and_reactivate_old(conn)

    assert _test_sources(vector_search.search_vector("anything", top_k=10)) == ["test_old"]
    assert _test_sources(keyword_search.search_keyword(WORD, top_k=10)) == ["test_old"]
    text, _, _ = _lookup("ZZZ 1001")
    assert "Old title" in text
    assert "ZZZ 1002: Removed course (step 1)" in text
    assert _lookup("ZZZ 1002")[2]["found"] == "course"


def test_a_withdrawn_edition_is_not_searched_either(conn):
    conn.execute("UPDATE document_editions SET status = 'withdrawn' WHERE id = 'test_new'")
    assert _test_sources(vector_search.search_vector("anything", top_k=10)) == []
    assert _lookup("ZZZ 1001")[2]["found"] == "not_found"
