"""Proves what the connected role can and can't do, without changing anything.

    python -m app.db.verify_role

The same check runs in CI (tests/test_api_role.py) and as the deploy's gate on
production, before the API switches to this role. Everything runs inside one
transaction that is always rolled back, and each probe in its own SAVEPOINT, also
rolled back. check_and_record's own `conn.transaction()` is nested inside that, so
it becomes a savepoint too and commits nothing.

A "denied" probe passes only on SQLSTATE 42501 (insufficient_privilege). Any other
error, a syntax error for one, says nothing about the role's rights, so it counts
as a failure of the check.

Only probe names are printed, never data or error text.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus

from app.config import CAMPUS_API_USER
from app.db.connection import get_connection
from app.limits import check_and_record

INSUFFICIENT_PRIVILEGE = "42501"
PROBE_IP_HASH = "verify-role-probe"

# The role's limits: its connection limit and statement timeout (app/db/roles.sql).
EXPECTED_LIMITS = (50, "5s")

# What the role's grants must be, exactly (app/db/roles.sql).
EXPECTED_GRANTS = {
    ("course_prerequisites", "SELECT"),
    ("courses", "SELECT"),
    ("document_chunks", "SELECT"),
    ("question_log", "DELETE"),
    ("question_log", "INSERT"),
    ("question_log", "SELECT"),
}


@dataclass(frozen=True)
class Probe:
    name: str
    run: Callable[[psycopg.Connection], object]


def _statement(name: str, statement: str) -> Probe:
    return Probe(name, lambda conn: conn.execute(statement))


def _limits_write_path(conn: psycopg.Connection) -> None:
    """The real function the API calls, with limits that can't refuse it."""
    decision = check_and_record(conn, PROBE_IP_HASH, daily_cap=10**9, per_ip_limit=10**9)
    if not decision.allowed:
        raise RuntimeError("check_and_record refused the probe")
    row = conn.execute(
        "SELECT count(*) FROM question_log WHERE ip_hash = %s", (PROBE_IP_HASH,)
    ).fetchone()
    if row[0] != 1:
        raise RuntimeError("check_and_record recorded no row")


def _set_role_to_a_superuser(conn: psycopg.Connection) -> None:
    superuser = conn.execute(
        "SELECT rolname FROM pg_roles WHERE rolsuper ORDER BY rolname LIMIT 1"
    ).fetchone()[0]
    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(superuser)))


MUST_WORK = [
    _statement("select courses", "SELECT 1 FROM courses LIMIT 1"),
    _statement("select course_prerequisites", "SELECT 1 FROM course_prerequisites LIMIT 1"),
    _statement(
        "select document_chunks, vector operator",
        "SELECT embedding <=> embedding FROM document_chunks LIMIT 1",
    ),
    _statement(
        "select document_chunks, full-text",
        "SELECT 1 FROM document_chunks "
        "WHERE text_search @@ plainto_tsquery('english', 'credits') LIMIT 1",
    ),
    _statement("select question_log", "SELECT count(*) FROM question_log"),
    Probe("question_log writes, through check_and_record", _limits_write_path),
    _statement("delete from question_log", "DELETE FROM question_log WHERE false"),
]

COPY_TO_PROGRAM = _statement("copy to a program", "COPY (SELECT 1) TO PROGRAM 'true'")

MUST_BE_DENIED = [
    _statement(
        "insert into document_chunks",
        "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, embedding) "
        "SELECT source, chunk_index, text, language, 'verify-role-probe', embedding "
        "FROM document_chunks LIMIT 1",
    ),
    _statement("update document_chunks", "UPDATE document_chunks SET text = text WHERE false"),
    _statement("delete from document_chunks", "DELETE FROM document_chunks WHERE false"),
    _statement("truncate document_chunks", "TRUNCATE document_chunks"),
    _statement(
        "insert into courses",
        "INSERT INTO courses (code, department, title, credits, source) "
        "VALUES ('ZZZ 0000', 'ZZZ', 'probe', 0, 'probe')",
    ),
    _statement("update question_log", "UPDATE question_log SET ip_hash = ip_hash WHERE false"),
    _statement("truncate question_log", "TRUNCATE question_log"),
    _statement("create table", "CREATE TABLE verify_role_probe (id int)"),
    _statement("create temp table", "CREATE TEMP TABLE verify_role_probe (id int)"),
    _statement("drop table", "DROP TABLE document_chunks"),
    _statement("alter table", "ALTER TABLE question_log ADD COLUMN verify_role_probe int"),
    _statement("create role", "CREATE ROLE verify_role_probe"),
    _statement("create extension", "CREATE EXTENSION pg_trgm"),
    Probe("set role to a superuser", _set_role_to_a_superuser),
    COPY_TO_PROGRAM,
]


def _in_savepoint(conn: psycopg.Connection, probe: Probe) -> psycopg.Error | None:
    """Runs one probe in its own savepoint and always undoes it. Returns its error."""
    conn.execute("SAVEPOINT verify_role_probe")
    error = None
    try:
        probe.run(conn)
    except psycopg.Error as e:
        error = e
    conn.execute("ROLLBACK TO SAVEPOINT verify_role_probe")
    conn.execute("RELEASE SAVEPOINT verify_role_probe")
    return error


def _worked_problem(probe: Probe, error: psycopg.Error | None) -> str | None:
    if error is None:
        return None
    return f"should work but failed ({error.sqlstate}): {probe.name}"


def _denied_problem(probe: Probe, error: psycopg.Error | None) -> str | None:
    if error is None:
        return f"should be denied but worked: {probe.name}"
    if error.sqlstate != INSUFFICIENT_PRIVILEGE:
        return f"failed with {error.sqlstate}, not {INSUFFICIENT_PRIVILEGE}: {probe.name}"
    return None


def _state_problems(conn: psycopg.Connection) -> list[str]:
    problems = []
    attributes = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
        "FROM pg_roles WHERE rolname = current_user"
    ).fetchone()
    if attributes != (True, False, False, False, False, False):
        problems.append("role attributes aren't login-only")

    grants = conn.execute(
        "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = current_user"
    ).fetchall()
    if set(grants) != EXPECTED_GRANTS:
        problems.append("table grants aren't exactly the expected ones")

    rights = conn.execute(
        "SELECT has_schema_privilege(current_user, 'public', 'CREATE'), "
        "has_database_privilege(current_user, current_database(), 'CREATE'), "
        "has_database_privilege(current_user, current_database(), 'TEMP'), "
        "has_sequence_privilege(current_user, 'question_log_id_seq', 'USAGE'), "
        "has_sequence_privilege(current_user, 'document_chunks_id_seq', 'USAGE')"
    ).fetchone()
    if rights != (False, False, False, True, False):
        problems.append("schema, database or sequence rights aren't the expected ones")

    limits = conn.execute(
        "SELECT rolconnlimit, current_setting('statement_timeout') "
        "FROM pg_roles WHERE rolname = current_user"
    ).fetchone()
    if limits != EXPECTED_LIMITS:
        problems.append("connection limit or statement timeout isn't the expected one")
    return problems


def check(conn: psycopg.Connection, *, skip_copy_to_program: bool = False) -> list[str]:
    """Every problem found; empty means the role is exactly as it should be.
    skip_copy_to_program: for the owner control test, where it would really run."""
    problems = []
    denied = [p for p in MUST_BE_DENIED if not (skip_copy_to_program and p is COPY_TO_PROGRAM)]
    with conn.transaction(force_rollback=True):
        # An open transaction is what makes every commit inside a savepoint.
        if conn.info.transaction_status != TransactionStatus.INTRANS:
            raise RuntimeError("the probes must run inside a transaction")
        for probe in MUST_WORK:
            problem = _worked_problem(probe, _in_savepoint(conn, probe))
            if problem:
                problems.append(problem)
        for probe in denied:
            problem = _denied_problem(probe, _in_savepoint(conn, probe))
            if problem:
                problems.append(problem)
        problems.extend(_state_problems(conn))
    return problems


def _question_log_rows(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM question_log").fetchone()[0]


def _run() -> int:
    # On a connection of its own, outside the rolled-back transaction, so it sees
    # only what was really committed.
    observer = get_connection(register_vector_type=False)
    conn = get_connection()
    try:
        user = conn.execute("SELECT current_user").fetchone()[0]
        # The write probes are only safe because they are denied or rolled back.
        if user != CAMPUS_API_USER:
            print("[verify_role] refused: not connected as the API's role")
            return 1
        before = _question_log_rows(observer)
        problems = check(conn)
        after = _question_log_rows(observer)
    finally:
        conn.close()
        observer.close()

    print(f"[verify_role] question_log rows before {before}, after {after}")
    if after != before:
        problems.append("question_log's row count changed")
    for problem in problems:
        print(f"[verify_role] PROBLEM: {problem}")
    if problems:
        return 1
    print(f"[verify_role] ok: {len(MUST_WORK)} allowed, {len(MUST_BE_DENIED)} denied")
    return 0


def main() -> int:
    try:
        return _run()
    except Exception as e:  # noqa: BLE001 -- only its type goes to the log, see the docstring
        print(f"[verify_role] failed: {type(e).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
