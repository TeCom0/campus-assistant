"""Extract structured course data (code, title, credits, prerequisites) from
the processed academic catalog text and store it in the courses and
course_prerequisites tables, for the query_courses agent tool.

Deliberately doesn't store full course descriptions -- that text is already
in document_chunks (Phase 1) and searchable via search_documents. This
table is for the structured facts (code/credits/prerequisites) that need
real SQL, especially recursive prerequisite chain-following.

Extraction covers ~666 of the catalog's course entries via a simple header
regex; a small number (~26, roughly 4%) use slightly different formatting
(e.g. an extra qualifier like "(MBA program foundation)" before the credit
count) and aren't captured. Documented here rather than silently accepted:
if those matter later, the regex can be extended, but this covers the very
large majority with a simple, explicit pattern.
"""

import re
from pathlib import Path

from app.db.connection import get_owner_connection, init_schema
from app.registry import load_registry

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"

PAGE_MARKER_RE = re.compile(r"--- page (\d+) ---")
HEADER_RE = re.compile(r"^([A-Z]{3}) (\d{4}) (.+?)\s*\((\d+)\s*SCH\)\s*$")
PREREQ_LABEL_RE = re.compile(r"^(Pre-?requisites?|Co-?requisites?):\s*(.*)", re.IGNORECASE)
# The space is optional: a few prerequisite lines write codes without one
# (e.g. "CSC3326, CSC3351 or MIS 3301"). Deliberately uppercase-only and no
# hyphen: neither variant occurs in the catalog's prerequisite text, and a
# case-insensitive pattern would match phrases like "and 2024" as a course.
COURSE_CODE_RE = re.compile(r"\b([A-Z]{3}) ?(\d{4})\b")


def extract_courses(edition_id: str) -> dict[str, dict]:
    """The courses in an edition's processed text file (data/processed/<id>.txt)."""
    text = (PROCESSED_DIR / f"{edition_id}.txt").read_text(encoding="utf-8")
    return extract_courses_from_text(edition_id, text)


def extract_courses_from_text(edition_id: str, text: str) -> dict[str, dict]:
    """The courses in an edition's text, as the chunker reads it. The dry run calls this
    on text in memory, so nothing is written to data/processed first."""
    lines = text.split("\n")

    page_of_line = []
    current_page = None
    for line in lines:
        m = PAGE_MARKER_RE.match(line)
        if m:
            current_page = int(m.group(1))
        page_of_line.append(current_page)

    courses: dict[str, dict] = {}
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if not m:
            continue
        dept, num, title, credits = m.groups()
        code = f"{dept} {num}"

        prereq_text = None
        coreq_text = None
        for j in range(i + 1, min(i + 4, len(lines))):
            next_line = lines[j].strip()
            pm = PREREQ_LABEL_RE.match(next_line)
            if pm:
                label, value = pm.groups()
                if label.lower().startswith(("pre",)):
                    prereq_text = value
                else:
                    coreq_text = value
                continue
            if HEADER_RE.match(next_line):
                break

        courses[code] = {
            "code": code,
            "department": dept,
            "title": title.strip(),
            "credits": int(credits),
            "prerequisites_text": prereq_text,
            "corequisites_text": coreq_text,
            "page": page_of_line[i],
            "source": edition_id,
        }

    return courses


def extract_prerequisite_edges(courses: dict[str, dict]) -> list[tuple[str, str]]:
    # A set, not a list: the same code can appear twice in one prerequisite_text
    # (e.g. "Prerequisite: HRD 2300 or special permission ... may take HRD 2300
    # as co-requisite"), which would otherwise violate the table's primary key.
    edges: set[tuple[str, str]] = set()
    for code, c in courses.items():
        if not c["prerequisites_text"]:
            continue
        for m in COURSE_CODE_RE.finditer(c["prerequisites_text"]):
            prereq_code = f"{m.group(1)} {m.group(2)}"
            if prereq_code != code:
                edges.add((code, prereq_code))
    return sorted(edges)


COURSE_INSERT_SQL = """
    INSERT INTO courses
        (code, department, title, credits, prerequisites_text, corequisites_text, page, source)
    VALUES
        (%(code)s, %(department)s, %(title)s, %(credits)s, %(prerequisites_text)s,
         %(corequisites_text)s, %(page)s, %(source)s)
"""

PREREQ_EDGE_INSERT_SQL = """
    INSERT INTO course_prerequisites (course_code, prerequisite_code, source)
    VALUES (%s, %s, %s)
"""


def replace_course_rows(
    conn, edition_id: str, courses: dict[str, dict], edges: list[tuple[str, str]]
) -> tuple[int, int]:
    """Replace one edition's courses and prerequisite edges, in one transaction;
    returns how many (courses, edges) were deleted. Other editions are untouched.

    Delete then insert rather than upsert, so a course a new extraction no longer
    finds doesn't stay answerable (TL-4 within one edition). Edges go first, because
    their foreign key points at the edition's courses. One transaction: if an insert
    fails, the deletes are undone and the edition is left as it was.
    """
    if not courses:
        raise ValueError(f"no courses to replace {edition_id!r} with")
    others = {c["source"] for c in courses.values()} - {edition_id}
    if others:
        raise ValueError(f"courses from {sorted(others)} passed as {edition_id!r}")
    with conn.transaction():
        deleted_edges = conn.execute(
            "DELETE FROM course_prerequisites WHERE source = %s", (edition_id,)
        ).rowcount
        deleted_courses = conn.execute(
            "DELETE FROM courses WHERE source = %s", (edition_id,)
        ).rowcount
        with conn.cursor() as cur:
            cur.executemany(COURSE_INSERT_SQL, list(courses.values()))
            # Each edge belongs to its course's edition (schema.sql, A2.3).
            cur.executemany(
                PREREQ_EDGE_INSERT_SQL, [(code, prereq, edition_id) for code, prereq in edges]
            )
    return deleted_courses, deleted_edges


def seed_courses() -> None:
    edition_id = load_registry().course_tables_edition().id
    courses = extract_courses(edition_id)
    edges = extract_prerequisite_edges(courses)

    conn = get_owner_connection()
    init_schema(conn)
    deleted_courses, deleted_edges = replace_course_rows(conn, edition_id, courses, edges)
    print(
        f"{edition_id}: replaced {deleted_courses} courses and {deleted_edges} prerequisite "
        f"edges with {len(courses)} and {len(edges)}"
    )
    # Proof of what's in the tables now, per edition.
    for source, n_courses, n_edges in conn.execute(
        "SELECT c.source, count(*), "
        "(SELECT count(*) FROM course_prerequisites p WHERE p.source = c.source) "
        "FROM courses c GROUP BY c.source ORDER BY c.source"
    ).fetchall():
        print(f"  {source}: {n_courses} courses, {n_edges} prerequisite edges")
    conn.close()


if __name__ == "__main__":
    seed_courses()
