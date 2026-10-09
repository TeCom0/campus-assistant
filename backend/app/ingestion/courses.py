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

from app.db.connection import get_connection, init_schema

CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "academic_catalog_2024_2025.txt"
)
SOURCE_NAME = "academic_catalog_2024_2025"

PAGE_MARKER_RE = re.compile(r"--- page (\d+) ---")
HEADER_RE = re.compile(r"^([A-Z]{3}) (\d{4}) (.+?)\s*\((\d+)\s*SCH\)\s*$")
PREREQ_LABEL_RE = re.compile(r"^(Pre-?requisites?|Co-?requisites?):\s*(.*)", re.IGNORECASE)
# The space is optional: a few prerequisite lines write codes without one
# (e.g. "CSC3326, CSC3351 or MIS 3301"). Deliberately uppercase-only and no
# hyphen: neither variant occurs in the catalog's prerequisite text, and a
# case-insensitive pattern would match phrases like "and 2024" as a course.
COURSE_CODE_RE = re.compile(r"\b([A-Z]{3}) ?(\d{4})\b")


def extract_courses() -> dict[str, dict]:
    lines = CATALOG_PATH.read_text(encoding="utf-8").split("\n")

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
            "source": SOURCE_NAME,
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


COURSE_UPSERT_SQL = """
    INSERT INTO courses
        (code, department, title, credits, prerequisites_text, corequisites_text, page, source)
    VALUES
        (%(code)s, %(department)s, %(title)s, %(credits)s, %(prerequisites_text)s,
         %(corequisites_text)s, %(page)s, %(source)s)
    ON CONFLICT (code) DO UPDATE SET
        department = EXCLUDED.department,
        title = EXCLUDED.title,
        credits = EXCLUDED.credits,
        prerequisites_text = EXCLUDED.prerequisites_text,
        corequisites_text = EXCLUDED.corequisites_text,
        page = EXCLUDED.page,
        source = EXCLUDED.source
"""

PREREQ_EDGE_INSERT_SQL = """
    INSERT INTO course_prerequisites (course_code, prerequisite_code)
    VALUES (%s, %s)
"""


def seed_courses() -> None:
    courses = extract_courses()
    edges = extract_prerequisite_edges(courses)

    conn = get_connection(register_vector_type=False)
    init_schema(conn)
    with conn.cursor() as cur:
        cur.executemany(COURSE_UPSERT_SQL, list(courses.values()))
        # Re-derive edges fresh each run rather than upserting, so a changed
        # extraction never leaves stale edges behind.
        cur.execute("DELETE FROM course_prerequisites")
        if edges:
            cur.executemany(PREREQ_EDGE_INSERT_SQL, edges)
    conn.close()
    print(f"seeded {len(courses)} courses, {len(edges)} prerequisite edges")


if __name__ == "__main__":
    seed_courses()
