"""Postgres connection helper, shared by ingestion (writes) and retrieval (reads)."""

from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from app.config import DATABASE_URL, EMBEDDING_DIM

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Without a timeout, psycopg on Windows waits forever when nothing listens on
# the port (measured 2026-10-21: a raw socket is refused in ~2 s, psycopg was
# still waiting after 60 s), and a server that accepts but never answers
# blocks it on any OS. libpq applies the timeout to each address it tries:
# "localhost" is ::1 then 127.0.0.1, so the worst case is twice this.
CONNECT_TIMEOUT_SECONDS = 10


def get_connection(
    *, register_vector_type: bool = True, connect_timeout: int = CONNECT_TIMEOUT_SECONDS
) -> psycopg.Connection:
    # register_vector fails if the vector extension doesn't exist yet, as on a
    # fresh database (e.g. in CI). Setup scripts pass False, then init_schema
    # creates the extension and registers the type.
    conn = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=connect_timeout)
    if register_vector_type:
        register_vector(conn)
    return conn


def database_reachable(conninfo: str = DATABASE_URL, timeout_seconds: int = 2) -> bool:
    """True if Postgres accepts a connection within the timeout (per address).

    For the DB tests' skip check, which runs at collection time: without a
    short timeout an unreachable database stalled the whole pytest run.
    """
    try:
        psycopg.connect(conninfo, connect_timeout=timeout_seconds).close()
        return True
    except psycopg.OperationalError:
        return False


def init_schema(conn: psycopg.Connection) -> None:
    # A plain replace, not str.format(): schema.sql's own syntax (Postgres's
    # '{}' empty-array literal) uses curly braces too, which .format() would
    # misinterpret as a positional placeholder.
    sql = SCHEMA_PATH.read_text(encoding="utf-8").replace("{embedding_dim}", str(EMBEDDING_DIM))
    conn.execute(sql)
    register_vector(conn)
