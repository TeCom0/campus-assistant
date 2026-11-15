"""Which editions the request path may read: the active edition of each public document.

docs/architecture.md section 5.2: superseded and withdrawn editions are never searched, and
a non-public document never reaches a student. Every search and course lookup puts
SOURCE_IN_FORCE in its WHERE clause, so the rule is one piece of SQL in one place, not a
condition each query has to remember. A2.3's tests load a superseded edition and a
non-public one next to an active one and check neither can surface.

A subquery, not a list of ids fetched first: Postgres reads the registry in the same
statement, so a rollback (`activate`, sub-step 4) takes effect on the very next search,
with no cache to go stale and no extra round trip. The registry tables hold a handful of
rows, so it costs nothing measurable.

`source` is the edition id in document_chunks, courses and course_prerequisites (schema.sql).
"""

IN_FORCE_EDITIONS_SQL = """
    SELECT e.id
    FROM document_editions e
    JOIN documents d ON d.id = e.document_id
    WHERE e.status = 'active' AND d.visibility = 'public'
"""

SOURCE_IN_FORCE = f"source IN ({IN_FORCE_EDITIONS_SQL})"


# What GET /editions serves: the editions in force, by the same rule as the searches, so
# the interface can't name an edition the searches don't read. `label` as the registry
# writes it ("2024-2025"); the interface shows it with an en dash, like the generated text.
EDITIONS_IN_FORCE_SQL = f"""
    SELECT e.id, e.document_id, e.label, e.card_title, e.course_tables
    FROM document_editions e
    WHERE e.id IN ({IN_FORCE_EDITIONS_SQL})
    ORDER BY e.document_id
"""


def read_editions_in_force(conn) -> list[dict]:
    """Every edition in force, as GET /editions serves it."""
    names = ("id", "document_id", "label", "card_title", "course_tables")
    return [dict(zip(names, row, strict=True)) for row in conn.execute(EDITIONS_IN_FORCE_SQL)]
