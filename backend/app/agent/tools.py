"""Tools available to the LangGraph agent.

Both tools use response_format="content_and_artifact": `content` is the
string the LLM reads, `artifact` is structured citation data attached to
the resulting ToolMessage that the LLM never sees but the API layer (app/
main.py) reads directly to build the /chat endpoint's `citations` SSE
event -- avoids re-parsing the LLM-facing text to recover source/page
metadata. Citation numbers come from app.agent.citations, which hands out
a continuously increasing sequence across ALL tool calls within one agent
run (so a second tool call picks up where the first left off, never
restarting at [1]).
"""

from langchain_core.tools import tool

from app.agent.citations import next_citation_numbers
from app.db.connection import get_connection
from app.retrieval.hybrid_search import search_hybrid

CATALOG_SOURCE = "academic_catalog_2024_2025"


@tool(response_format="content_and_artifact")
def search_documents(query: str) -> tuple[str, list[dict]]:
    """Search Al Akhawayn University's academic catalog and scholarship pages.

    Use this for any question about academic policies, course requirements,
    grading, registration, admissions, or scholarships/fellowships that might
    be described in official university documents. Returns relevant passages
    with numbered citations like [1], [2].
    """
    results = search_hybrid(query, top_k=5)
    if not results:
        return "No relevant passages found in the university documents.", []

    numbers = next_citation_numbers(len(results))
    parts = [
        f"[{n}] (source: {r.source}, pages: {r.pages})\n{r.text}"
        for n, r in zip(numbers, results, strict=True)
    ]
    artifact = [
        {"marker": n, "source": r.source, "pages": r.pages}
        for n, r in zip(numbers, results, strict=True)
    ]
    return "\n\n".join(parts), artifact


@tool(response_format="content_and_artifact")
def query_courses(code: str, follow_prerequisites: bool = False) -> tuple[str, list[dict]]:
    """Look up a specific AUI course by its code (e.g. "ACC 2302") in the structured
    course catalog. Returns its title, credits, and prerequisites/corequisites exactly
    as stated in the catalog.

    Set follow_prerequisites=True to also return the FULL prerequisite chain --
    every course transitively required before this one, not just the immediate
    prerequisite -- for questions like "what do I need before taking X?".

    Use this tool, not search_documents, whenever the question names or implies a
    specific course code or asks about prerequisite chains.
    """
    conn = get_connection()
    code = code.strip().upper()
    row = conn.execute(
        """
        SELECT code, department, title, credits, prerequisites_text, corequisites_text, page
        FROM courses WHERE code = %s
        """,
        (code,),
    ).fetchone()

    if not row:
        conn.close()
        return f"No course found with code '{code}' in AUI's course catalog.", []

    code_, dept, title, credits, prereq_text, coreq_text, page = row
    (marker,) = next_citation_numbers(1)
    source_note = f"page {page}" if page is not None else "no page recorded"
    lines = [
        (
            f"[{marker}] {code_}: {title} ({credits} SCH), department {dept} "
            f"(source: {CATALOG_SOURCE}, {source_note})"
        ),
        f"Prerequisites (as stated in catalog): {prereq_text or 'None'}",
    ]
    if coreq_text:
        lines.append(f"Corequisites: {coreq_text}")

    if follow_prerequisites:
        chain = conn.execute(
            """
            WITH RECURSIVE chain AS (
                SELECT prerequisite_code, 1 AS depth
                FROM course_prerequisites
                WHERE course_code = %s
                UNION ALL
                SELECT cp.prerequisite_code, chain.depth + 1
                FROM course_prerequisites cp
                JOIN chain ON cp.course_code = chain.prerequisite_code
                WHERE chain.depth < 10
            )
            SELECT DISTINCT prerequisite_code, depth FROM chain ORDER BY depth, prerequisite_code
            """,
            (code,),
        ).fetchall()
        if chain:
            lines.append(
                f"Full prerequisite chain for [{marker}] (all courses referenced, directly or "
                "indirectly). CAUTION: this flat list does NOT capture AND/OR logic between "
                "alternatives -- e.g. a course listing 'X, or Y, or Z' as its prerequisite will "
                "show X, Y, and Z all here, even though only ONE of them is actually required. "
                "For the exact logic, always check each course's own 'Prerequisites (as stated "
                "in catalog)' text (query this tool again for that course's code if needed) "
                "before telling the student something is mandatory."
            )
            lines.extend(f"  - {prereq_code} (step {depth})" for prereq_code, depth in chain)
        else:
            lines.append(
                "No further prerequisite chain found in the structured data (either this "
                "course has no prerequisites, or its prerequisites aren't other AUI courses)."
            )

    conn.close()
    artifact = [
        {
            "marker": marker,
            "source": CATALOG_SOURCE,
            "pages": [page] if page is not None else None,
        }
    ]
    return "\n".join(lines), artifact
