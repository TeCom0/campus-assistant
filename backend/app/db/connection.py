"""Postgres connection helper, shared by ingestion (writes) and retrieval (reads)."""

from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from app.config import DATABASE_URL, EMBEDDING_DIM

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(*, register_vector_type: bool = True) -> psycopg.Connection:
    # register_vector fails if the vector extension doesn't exist yet, as on a
    # fresh database (e.g. in CI). Setup scripts pass False, then init_schema
    # creates the extension and registers the type.
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    if register_vector_type:
        register_vector(conn)
    return conn


def init_schema(conn: psycopg.Connection) -> None:
    # A plain replace, not str.format(): schema.sql's own syntax (Postgres's
    # '{}' empty-array literal) uses curly braces too, which .format() would
    # misinterpret as a positional placeholder.
    sql = SCHEMA_PATH.read_text(encoding="utf-8").replace("{embedding_dim}", str(EMBEDDING_DIM))
    conn.execute(sql)
    register_vector(conn)
