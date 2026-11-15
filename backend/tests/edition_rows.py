"""A test document and edition, for DB tests that insert their own chunks or courses.

Since A2.3 every content row's `source` must be an edition the registry tables hold
(schema.sql's foreign keys), so a test that inserts fake rows registers a fake edition
first, inside the same rolled-back transaction.
"""

import psycopg
from psycopg.types.json import Jsonb


def add_edition(
    conn: psycopg.Connection,
    edition_id: str,
    *,
    document_id: str | None = None,
    status: str = "active",
    visibility: str = "public",
    course_tables: bool = False,
) -> None:
    document_id = document_id or f"{edition_id}_document"
    conn.execute(
        "INSERT INTO documents (id, domain, audience, visibility, time_sensitive, title) "
        "VALUES (%s, 'academic', 'all', %s, false, %s) ON CONFLICT (id) DO NOTHING",
        (document_id, visibility, Jsonb({"en": "Test document", "fr": "Document de test"})),
    )
    conn.execute(
        "INSERT INTO document_editions (id, document_id, label, card_title, retrieved_at, "
        "language, format, source_url, course_tables, status, sha256, parser_version, "
        "quality_report) VALUES (%s, %s, 'test', 'Test edition', '2026-11-15', 'en', 'pdf', "
        "'https://example.invalid/test.pdf', %s, %s, 'test', 'unversioned', '{}')",
        (edition_id, document_id, course_tables, status),
    )


class Lent:
    """A test's connection, lent to code that opens and closes its own (searches, lookups):
    rows the test inserted stay visible to it, inside the transaction that is rolled back."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def close(self) -> None:
        pass  # the test's transaction stays open, to be rolled back
