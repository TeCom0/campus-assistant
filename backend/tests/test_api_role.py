"""What the API's database role can and can't do, proven on a real connection.

Uses the same check as the deploy's gate (app/db/verify_role.py). The owner control
runs that same check as the owner and expects it to report problems: without it,
"everything was denied" could just mean the probes are broken.

In CI these must run: a missing role fails instead of skipping.
"""

import os
from pathlib import Path

import psycopg
import pytest
import yaml

from app.config import CAMPUS_API_USER
from app.db import verify_role
from app.db.connection import database_reachable, get_connection, get_owner_connection
from app.db.verify_role import (
    COPY_TO_PROGRAM,
    MUST_BE_DENIED,
    MUST_WORK,
    Probe,
    _denied_problem,
    _in_savepoint,
    _statement,
    check,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def api_conn():
    if not database_reachable():
        if os.environ.get("CI"):
            pytest.fail("the API's role must connect in CI: the rights must not go unproven")
        pytest.skip("can't connect as the API's role: is Postgres up, and migrate run?")
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture
def owner_conn(api_conn):
    connection = get_owner_connection()
    yield connection
    connection.close()


def test_the_api_connects_as_its_own_role(api_conn):
    assert api_conn.execute("SELECT current_user").fetchone() == (CAMPUS_API_USER,)


def test_the_role_is_exactly_as_it_should_be(api_conn):
    assert check(api_conn) == []


@pytest.mark.parametrize(
    ("probes", "name"),
    [
        (MUST_WORK, "select document_chunks, vector operator"),
        (MUST_WORK, "select courses"),
        (MUST_WORK, "question_log writes, through check_and_record"),
        (MUST_BE_DENIED, "insert into document_chunks"),
        (MUST_BE_DENIED, "create table"),
        (MUST_BE_DENIED, "drop table"),
        (MUST_BE_DENIED, "copy to a program"),
    ],
)
def test_the_required_probes_stay_in_the_check(probes, name):
    assert name in {probe.name for probe in probes}


def test_the_check_commits_nothing(api_conn, owner_conn):
    def counts():
        return owner_conn.execute(
            "SELECT (SELECT count(*) FROM question_log), "
            "(SELECT count(*) FROM question_log WHERE ip_hash = 'verify-role-probe'), "
            "(SELECT count(*) FROM document_chunks)"
        ).fetchone()

    before = counts()
    assert check(api_conn) == []
    assert counts() == before
    assert before[1] == 0


def test_check_and_record_really_wrote_inside_the_transaction(api_conn):
    # So "nothing was committed" above isn't just "nothing was ever written".
    with api_conn.transaction(force_rollback=True):
        probe = next(p for p in MUST_WORK if "check_and_record" in p.name)
        assert _in_savepoint(api_conn, probe) is None


def test_a_savepoint_undoes_a_probe_that_worked(api_conn):
    with api_conn.transaction(force_rollback=True):
        api_conn.execute("INSERT INTO question_log (ip_hash) VALUES ('kept')")
        inserted = _statement("insert", "INSERT INTO question_log (ip_hash) VALUES ('rolled-back')")
        assert _in_savepoint(api_conn, inserted) is None
        rows = api_conn.execute(
            "SELECT ip_hash FROM question_log WHERE ip_hash IN ('kept', 'rolled-back')"
        ).fetchall()
    assert rows == [("kept",)]


def test_a_failed_probe_leaves_the_transaction_usable(api_conn):
    with api_conn.transaction(force_rollback=True):
        error = _in_savepoint(api_conn, _statement("denied", "DROP TABLE document_chunks"))
        assert error.sqlstate == "42501"
        assert api_conn.execute("SELECT 1").fetchone() == (1,)


# --- The check itself: only 42501 counts as denied ---


@pytest.mark.parametrize(
    ("statement", "sqlstate"),
    [
        ("SELEC 1", "42601"),  # a syntax error
        ("DROP TABLE no_such_table_here", "42P01"),  # a missing table
    ],
)
def test_a_denied_probe_failing_for_another_reason_is_a_problem(api_conn, statement, sqlstate):
    probe = _statement("probe", statement)
    with api_conn.transaction(force_rollback=True):
        error = _in_savepoint(api_conn, probe)
    assert error.sqlstate == sqlstate
    assert _denied_problem(probe, error) == f"failed with {sqlstate}, not 42501: probe"


def test_a_denied_probe_that_worked_is_a_problem():
    assert _denied_problem(Probe("probe", print), None) == "should be denied but worked: probe"


def test_a_denied_probe_failing_with_42501_is_fine(api_conn):
    probe = _statement("probe", "CREATE TABLE verify_role_probe (id int)")
    with api_conn.transaction(force_rollback=True):
        error = _in_savepoint(api_conn, probe)
    assert _denied_problem(probe, error) is None


# --- The owner control, with the same harness ---


def test_the_same_check_reports_the_owner(owner_conn):
    problems = check(owner_conn, skip_copy_to_program=True)

    for probe in MUST_BE_DENIED:
        if probe is not COPY_TO_PROGRAM:
            assert f"should be denied but worked: {probe.name}" in problems
    assert "role attributes aren't login-only" in problems
    # Everything the API needs also works as the owner: only the denials differ.
    assert not [p for p in problems if p.startswith("should work")]


def test_the_owner_control_changed_nothing(owner_conn):
    def tables():
        return owner_conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchone()

    before = tables(), owner_conn.execute("SELECT count(*) FROM document_chunks").fetchone()
    check(owner_conn, skip_copy_to_program=True)
    after = tables(), owner_conn.execute("SELECT count(*) FROM document_chunks").fetchone()
    assert before == after


# --- The command ---


class _FakeConnection:
    """Stands in for a connection, to pin main()'s behaviour around the check."""

    def __init__(self, user: str, rows: list[int]):
        self.user, self.rows = user, rows

    def execute(self, statement, *args):
        value = (self.user,) if "current_user" in statement else (self.rows.pop(0),)

        class Result:
            def fetchone(self):
                return value

        return Result()

    def close(self):
        pass


def test_the_command_refuses_any_other_role(monkeypatch, capfd):
    monkeypatch.setattr(verify_role, "get_connection", lambda **k: _FakeConnection("owner", []))
    monkeypatch.setattr(
        verify_role, "check", lambda conn: pytest.fail("the probes must not run as another role")
    )
    assert verify_role.main() == 1
    assert "refused" in capfd.readouterr().out


def test_the_command_fails_if_a_row_was_committed(monkeypatch, capfd):
    monkeypatch.setattr(
        verify_role, "get_connection", lambda **k: _FakeConnection(CAMPUS_API_USER, [5, 6])
    )
    monkeypatch.setattr(verify_role, "check", lambda conn: [])
    assert verify_role.main() == 1
    out = capfd.readouterr().out
    assert "before 5, after 6" in out
    assert "row count changed" in out


def test_the_command_prints_only_probe_names(api_conn, capfd):
    assert verify_role.main() == 0
    out = capfd.readouterr().out
    assert "ok:" in out
    assert "SELECT" not in out


def test_a_connection_error_prints_only_its_type(monkeypatch, capfd):
    def failing(**kwargs):
        raise psycopg.OperationalError("password authentication failed SECRETMARKER")

    monkeypatch.setattr(verify_role, "get_connection", failing)
    assert verify_role.main() == 1
    out, err = capfd.readouterr()
    assert "OperationalError" in out
    assert "SECRETMARKER" not in out + err


# --- Where the owner's password can reach ---


def test_compose_keeps_the_owners_credentials_out_of_the_api_container():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    api = compose["services"]["api"]["environment"]
    # env_file passes all of .env in, so these two must be blanked explicitly.
    assert api["POSTGRES_USER"] == ""
    assert api["POSTGRES_PASSWORD"] == ""
    # migrate is the one that needs them, so it must not blank them.
    migrate = compose["services"]["migrate"]["environment"]
    assert "POSTGRES_PASSWORD" not in migrate
