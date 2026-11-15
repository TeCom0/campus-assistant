"""`python -m app.registry activate`: which edition is in force, and the rollback (A2.3, rule item 5).

Two editions of one document, each with a chunk that matches the query and its own version of
a course. Activating the new one puts it in force for the very next search and course lookup,
in one transaction, recording who and when; activating the old one again is the rollback. A
failure between the two updates changes nothing, and what would leave students with less than
before (no chunks, no courses, a withdrawn edition) is refused.

Needs the Postgres container; skipped when it isn't reachable. Everything runs as the owner in
a transaction that is always rolled back, lent to the searches as in test_editions_in_force.py.
"""

import psycopg
import pytest
from edition_rows import Lent, add_edition

from app import registry
from app.agent import tools
from app.agent.citations import reset_citation_counter
from app.config import EMBEDDING_DIM
from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.registry import ACTIVATE_SQL, RegistryError, activate, document_statuses
from app.retrieval import keyword_search, vector_search

pytestmark = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")

WORD = "zyxquorbal"
VECTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
TEST_EDITIONS = {"test_old", "test_new"}


def _chunk(conn, source: str) -> None:
    conn.execute(
        "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, embedding) "
        "VALUES (%s, 0, %s, 'en', 'test-model', %s::vector)",
        (source, f"Section: test\n{WORD} rules of {source}", str(VECTOR)),
    )


def _course(conn, title: str, source: str) -> None:
    conn.execute(
        "INSERT INTO courses (code, department, title, credits, source) "
        "VALUES ('ZZZ 1001', 'ZZZ', %s, 3, %s)",
        (title, source),
    )


@pytest.fixture
def conn(monkeypatch):
    connection = get_owner_connection(register_vector_type=True)
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        add_edition(connection, "test_old", document_id="test_catalog", status="active")
        add_edition(connection, "test_new", document_id="test_catalog", status="draft")
        for source, title in (("test_old", "Old title"), ("test_new", "New title")):
            _chunk(connection, source)
            _course(connection, title, source)
        lent = Lent(connection)
        for module in (vector_search, keyword_search, tools):
            monkeypatch.setattr(module, "get_connection", lambda **_: lent)
        monkeypatch.setattr(vector_search, "embed_query", lambda _query: VECTOR)
        yield connection
    connection.close()


def _in_force(conn) -> tuple[list[str], list[str], str]:
    """What a student's next question would get: vector, keyword, and the course title."""
    vector = [r.source for r in vector_search.search_vector("x", 10) if r.source in TEST_EDITIONS]
    keyword = [r.source for r in keyword_search.search_keyword(WORD, 10)
               if r.source in TEST_EDITIONS]  # fmt: skip
    reset_citation_counter()
    _, _, lookup = tools._look_up_course("ZZZ 1001", False)
    return vector, keyword, lookup.get("title")


def _statuses(conn) -> dict[str, str]:
    return {row[0]: row[1] for row in document_statuses(conn, "test_old")}


def test_activating_the_new_edition_puts_it_in_force_for_the_next_question(conn):
    assert _in_force(conn) == (["test_old"], ["test_old"], "Old title")

    result = activate(conn, "test_new", activated_by="test-maintainer")

    assert result.superseded == ("test_old",)
    assert (result.chunks, result.courses) == (1, 1)
    assert _statuses(conn) == {"test_old": "superseded", "test_new": "active"}
    assert _in_force(conn) == (["test_new"], ["test_new"], "New title")


def test_it_records_who_activated_it_and_when(conn):
    activate(conn, "test_new", activated_by="  test-maintainer ")
    by, at = conn.execute(
        "SELECT activated_by, activated_at FROM document_editions WHERE id = 'test_new'"
    ).fetchone()
    assert by == "test-maintainer"
    assert at is not None


def test_rollback_is_the_same_command_the_other_way(conn):
    activate(conn, "test_new", activated_by="test-maintainer")

    result = activate(conn, "test_old", activated_by="test-rollback")

    assert result.superseded == ("test_new",)
    assert _statuses(conn) == {"test_old": "active", "test_new": "superseded"}
    assert _in_force(conn) == (["test_old"], ["test_old"], "Old title")
    # Nothing was deleted on the way: both editions keep their rows.
    counts = conn.execute(
        "SELECT source, count(*) FROM document_chunks WHERE source = ANY(%s) GROUP BY 1",
        (sorted(TEST_EDITIONS),),
    ).fetchall()
    assert dict(counts) == {"test_old": 1, "test_new": 1}


class _FailsOn:
    """The connection, except that one statement raises: a crash between the two updates."""

    def __init__(self, conn, statement: str):
        self._conn = conn
        self._statement = statement

    def transaction(self):
        return self._conn.transaction()

    def execute(self, query, *args, **kwargs):
        if query == self._statement:
            raise RuntimeError("simulated failure")
        return self._conn.execute(query, *args, **kwargs)


def test_a_failure_between_the_two_updates_changes_nothing(conn):
    with pytest.raises(RuntimeError, match="simulated failure"):
        activate(_FailsOn(conn, ACTIVATE_SQL), "test_new", activated_by="test-maintainer")

    # The supersede ran, and was undone with the transaction: the document never went
    # without an edition in force.
    assert _statuses(conn) == {"test_old": "active", "test_new": "draft"}
    assert _in_force(conn) == (["test_old"], ["test_old"], "Old title")


@pytest.mark.parametrize(
    ("edition", "by", "message"),
    [
        ("test_missing", "test-maintainer", "no edition"),
        ("test_old", "test-maintainer", "already active"),
        ("test_new", "   ", "--by is empty"),
    ],
)
def test_it_refuses_and_changes_nothing(conn, edition, by, message):
    with pytest.raises(RegistryError, match=message):
        activate(conn, edition, activated_by=by)
    assert _statuses(conn) == {"test_old": "active", "test_new": "draft"}


def test_a_withdrawn_edition_is_not_brought_back(conn):
    conn.execute("UPDATE document_editions SET status = 'withdrawn' WHERE id = 'test_new'")
    with pytest.raises(RegistryError, match="withdrawn"):
        activate(conn, "test_new", activated_by="test-maintainer")


def test_an_edition_with_no_chunks_is_refused(conn):
    add_edition(conn, "test_empty", document_id="test_catalog", status="draft")
    with pytest.raises(RegistryError, match="no chunks"):
        activate(conn, "test_empty", activated_by="test-maintainer")
    assert _statuses(conn)["test_old"] == "active"


def test_the_course_tables_edition_with_no_courses_is_refused(conn):
    add_edition(conn, "test_no_courses", document_id="test_catalog", status="draft",
                course_tables=True)  # fmt: skip
    _chunk(conn, "test_no_courses")
    with pytest.raises(RegistryError, match="no courses"):
        activate(conn, "test_no_courses", activated_by="test-maintainer")


def test_the_database_itself_refuses_two_active_editions(conn):
    # The command supersedes first; the partial unique index is the backstop for anything
    # that doesn't go through it.
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        conn.execute("UPDATE document_editions SET status = 'active' WHERE id = 'test_new'")


def test_the_cli_refuses_an_unknown_edition_and_says_why(capsys):
    # Against the real database: an unknown edition is refused before anything changes.
    assert registry.main(["activate", "not_an_edition", "--by", "test-maintainer"]) == 1
    assert "refused: no edition 'not_an_edition'" in capsys.readouterr().out
