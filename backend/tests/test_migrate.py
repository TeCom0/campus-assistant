"""The migrate command: it can run again and again on an existing database, the
role gets exactly the rights the code uses, and the password never leaves the
client in clear or reaches the output.

Everything runs in a rolled-back transaction as the owner, because roles and
grants are transactional too, so the database's own role keeps its password.
"""

import pytest
from psycopg.abc import Query

from app.config import CAMPUS_API_PASSWORD
from app.db import migrate as migrate_module
from app.db.connection import database_reachable, get_connection
from app.db.migrate import main, migrate, set_api_password

MARKER_PASSWORD = "SECRETMARKER-not-a-real-password"
EXPECTED_GRANTS = {
    ("course_prerequisites", "SELECT"),
    ("courses", "SELECT"),
    ("document_chunks", "SELECT"),
    ("question_log", "DELETE"),
    ("question_log", "INSERT"),
    ("question_log", "SELECT"),
}

needs_db = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")


@pytest.fixture
def conn():
    connection = get_connection(register_vector_type=False)
    with connection.transaction(force_rollback=True):
        yield connection
    connection.close()


def _grants(conn) -> set[tuple[str, str]]:
    rows = conn.execute(
        "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = 'campus_api'"
    ).fetchall()
    return set(rows)


@needs_db
def test_running_it_twice_leaves_the_same_exact_rights(conn):
    migrate(conn, MARKER_PASSWORD)
    first = _grants(conn)
    migrate(conn, MARKER_PASSWORD)
    assert first == _grants(conn) == EXPECTED_GRANTS


@needs_db
def test_the_role_is_not_privileged(conn):
    migrate(conn, MARKER_PASSWORD)
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
        "FROM pg_roles WHERE rolname = 'campus_api'"
    ).fetchone()
    assert row == (True, False, False, False, False, False)


@needs_db
def test_it_restores_the_attributes_of_a_role_someone_changed(conn):
    migrate(conn, MARKER_PASSWORD)
    conn.execute("ALTER ROLE campus_api CREATEDB")
    migrate(conn, MARKER_PASSWORD)
    created = conn.execute(
        "SELECT rolcreatedb FROM pg_roles WHERE rolname = 'campus_api'"
    ).fetchone()
    assert created == (False,)


@needs_db
def test_the_server_receives_only_a_verifier(conn, monkeypatch):
    migrate(conn, "first")
    sent = []
    real_execute = conn.execute

    def recording(query: Query, *args, **kwargs):
        sent.append(query.as_string(conn) if hasattr(query, "as_string") else str(query))
        return real_execute(query, *args, **kwargs)

    monkeypatch.setattr(conn, "execute", recording)
    set_api_password(conn, MARKER_PASSWORD)

    assert sent, "the statement really went through the recorder"
    assert MARKER_PASSWORD not in "".join(sent)
    stored = real_execute(
        "SELECT rolpassword FROM pg_authid WHERE rolname = 'campus_api'"
    ).fetchone()[0]
    assert stored.startswith("SCRAM-SHA-256$")
    assert MARKER_PASSWORD not in stored


def test_a_failure_prints_only_the_exception_type(monkeypatch, capfd):
    def failing(*args, **kwargs):
        raise ValueError(f"something quoting {MARKER_PASSWORD}")

    monkeypatch.setattr(migrate_module, "CAMPUS_API_PASSWORD", MARKER_PASSWORD)
    monkeypatch.setattr(migrate_module, "get_connection", failing)

    assert main() == 1
    out, err = capfd.readouterr()
    assert "ValueError" in out
    assert MARKER_PASSWORD not in out + err


def test_a_missing_password_stops_it(monkeypatch, capfd):
    called = []
    monkeypatch.setattr(migrate_module, "CAMPUS_API_PASSWORD", "")
    monkeypatch.setattr(migrate_module, "get_connection", lambda **kwargs: called.append(1))

    assert main() == 1
    assert not called
    assert "CAMPUS_API_PASSWORD" in capfd.readouterr().out


@needs_db
def test_success_prints_no_password(monkeypatch, capfd):
    # main() opens its own connection and commits, so it uses the real password.
    if not CAMPUS_API_PASSWORD:
        pytest.skip("CAMPUS_API_PASSWORD is not set")
    assert main() == 0
    out, err = capfd.readouterr()
    assert "up to date" in out
    assert CAMPUS_API_PASSWORD not in out + err
