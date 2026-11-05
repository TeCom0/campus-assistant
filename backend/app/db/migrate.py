"""One-shot: bring a database to the current schema and roles. Run by the owner.

    python -m app.db.migrate

Idempotent, so it can run on every deploy and on a volume that already exists.
Only exception types are printed: psycopg's messages can quote the statement.
"""

import sys
from pathlib import Path

import psycopg
from psycopg import sql

from app.config import CAMPUS_API_PASSWORD, CAMPUS_API_USER
from app.db.connection import get_connection, init_schema

ROLES_PATH = Path(__file__).resolve().parent / "roles.sql"


def set_api_password(conn: psycopg.Connection, password: str) -> None:
    # libpq turns the password into a SCRAM verifier here on the client, so the
    # server never sees it: a statement that failed and reached Postgres's log
    # would hold only the verifier.
    verifier = conn.pgconn.encrypt_password(
        password.encode(), CAMPUS_API_USER.encode(), b"scram-sha-256"
    ).decode()
    conn.execute(
        sql.SQL("ALTER ROLE {} PASSWORD {}").format(
            sql.Identifier(CAMPUS_API_USER), sql.Literal(verifier)
        )
    )


def migrate(conn: psycopg.Connection, api_password: str) -> None:
    init_schema(conn)  # first: roles.sql grants on these tables
    conn.execute(ROLES_PATH.read_text(encoding="utf-8"))
    set_api_password(conn, api_password)


def main() -> int:
    if not CAMPUS_API_PASSWORD:
        print("[migrate] CAMPUS_API_PASSWORD is not set")
        return 1
    try:
        conn = get_connection(register_vector_type=False)
        try:
            migrate(conn, CAMPUS_API_PASSWORD)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 -- only its type goes to the log, see the docstring
        print(f"[migrate] failed: {type(e).__name__}")
        return 1
    print("[migrate] schema and roles are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
