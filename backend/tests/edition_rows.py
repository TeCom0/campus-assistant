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
        "'https://example.invalid/test.pdf', false, %s, 'test', 'unversioned', '{}')",
        (edition_id, document_id, status),
    )
