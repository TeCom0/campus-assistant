"""Tools available to the LangGraph agent.

Both tools use response_format="content_and_artifact": `content` is the
string the LLM reads, `artifact` is structured citation data attached to
the resulting ToolMessage that the LLM never sees but the API layer (app/
main.py) reads directly to build the /chat endpoint's `citations` SSE
event -- avoids re-parsing the LLM-facing text to recover source/page
metadata. Each citation also carries the passage `text` the model read, for
the faithfulness evaluation (claims are checked against it); main.py strips
it before sending citations to the browser. Citation numbers come from app.agent.citations, which hands out
a continuously increasing sequence across ALL tool calls within one agent
run (so a second tool call picks up where the first left off, never
restarting at [1]), and gives a passage returned again its earlier number.
"""

import time
from typing import Annotated

from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState

from app.agent.citations import citation_number_for
from app.agent.trace import record_tool_step, snippet
from app.db.connection import get_connection
from app.retrieval.hybrid_search import (
    RRF_K,
    query_key,
    search_hybrid_multi,
    strip_university_name,
    unique_queries,
)

CATALOG_SOURCE = "academic_catalog_2024_2025"

# For a code that other courses list as a prerequisite but that has no
# course-description entry, so no `courses` row (e.g. MTH 1305). It IS in the
# catalog, so "not found" would be false; and with no title given, the model
# has borrowed a neighbouring course's title before.
NO_DESCRIPTION_NOTE = (
    "referenced in the catalog but has no course description there, so its title and "
    "prerequisites aren't available here -- don't state a title for it"
)


def search_queries(query: str, query_en: str, messages) -> list[str]:
    """The phrasings one search_documents call searches and fuses, without repeats.

    - the agent's query, always;
    - its English version (the documents are in English, and a French query
      misses passages an English one finds); if the model left it out or
      empty, the query alone is searched rather than failing;
    - on the first turn only (exactly one student message), the student's
      question word for word: it counters the agent padding its queries
      ("MTH 1305 Al Akhawayn University course description"). A follow-up
      like "And for graduates?" doesn't stand alone, so it isn't searched.

    Also used by the evaluation to record what each search really searched.
    """
    candidates = _candidate_queries(query, query_en, messages)
    return unique_queries([text for _, text in candidates])  # drops blanks and repeats


def _candidate_queries(query: str, query_en: str, messages) -> list[tuple[str, str]]:
    """(origin, text) for each phrasing search_queries starts from, before repeats are dropped."""
    candidates = [("query", query), ("query_en", query_en)]
    questions = [m for m in messages if m.type == "human"]
    if len(questions) == 1:
        candidates.append(("question", str(questions[0].content)))
    return candidates


def search_phrasings(query: str, query_en: str, messages) -> list[dict]:
    """search_queries, with where each phrasing came from, for the trace.

    `origins` lists every candidate a phrasing stands for ("query",
    "query_en", "question"): an English question's query and query_en are
    often the same and searched once. `as_written` is the first of them as
    the agent or student wrote it, before the university's name was stripped.
    """
    candidates = _candidate_queries(query, query_en, messages)
    phrasings = []
    for text in search_queries(query, query_en, messages):
        written = [
            (origin, raw)
            for origin, raw in candidates
            if query_key(strip_university_name(raw)) == query_key(text)
        ]
        phrasings.append(
            {
                "text": text,
                "origins": [origin for origin, _ in written],
                "as_written": written[0][1],
            }
        )
    return phrasings


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


@tool(response_format="content_and_artifact")
def search_documents(
    query: Annotated[str, "What to search for, in the language of the question."],
    # Filled in by LangGraph's ToolNode with the graph state (the conversation);
    # hidden from the model's schema, so the model can't see or set it.
    state: Annotated[dict, InjectedState],
    query_en: Annotated[
        str,
        "The same search in English (the documents are in English). If the query is "
        "already in English, repeat it.",
    ] = "",
    # The model's id for this call, filled in by ToolNode and hidden from the
    # model's schema like `state`. Only the trace uses it: ToolNode runs a
    # round's calls in parallel, and the id puts their steps back in the
    # model's order (trace.in_call_order). None when called directly (tests).
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None,
) -> tuple[str, list[dict]]:
    """Search Al Akhawayn University's academic catalog and scholarship pages.

    Use this for any question about academic policies, course requirements,
    grading, registration, admissions, or scholarships/fellowships that might
    be described in official university documents. Returns relevant passages
    with numbered citations like [1], [2].
    """
    # query_en defaults to "" so a call without it still searches; the schema
    # bound to the model marks it required (see graph.MODEL_TOOLS).
    started = time.perf_counter()
    queries = search_queries(query, query_en, state["messages"])
    print(f"[search_documents] searching: {queries}")
    results = search_hybrid_multi(queries, top_k=5)

    parts = []
    artifact = []
    ranked = []  # for the trace only
    for rank, r in enumerate(results, start=1):
        number, is_new = citation_number_for((r.source, r.chunk_index))
        ranked.append(
            {
                "rank": rank,
                "marker": number,
                "new": is_new,  # False: already returned by an earlier search
                "source": r.source,
                "pages": r.pages,
                "level": r.level,
                "section": r.section,
                "sections": r.sections,
                "snippet": snippet(r.text),
                "rrf_score": round(r.rrf_score, 4),
                "vector_rank": r.vector_rank,
                "keyword_rank": r.keyword_rank,
            }
        )
        if is_new:
            parts.append(f"[{number}] (source: {r.source}, pages: {r.pages})\n{r.text}")
            artifact.append(
                {
                    "marker": number,
                    "source": r.source,
                    "pages": r.pages,
                    "section": r.section,
                    "level": r.level,
                    "sections": r.sections,
                    "text": r.text,
                }
            )
        else:
            # Its text is already in an earlier tool result for this question;
            # sending it again would only spend tokens.
            parts.append(f"[{number}] (same passage as returned by an earlier search)")

    # Each phrasing has a vector list and a keyword list. A passage first in
    # every list scores lists / (RRF_K + 1): the most any passage can score
    # in this search, which the panel scales its score bars to.
    ranked_lists = 2 * len(queries)
    record_tool_step(
        "search_documents",
        {
            "args": {"query": query, "query_en": query_en},
            "phrasings": search_phrasings(query, query_en, state["messages"]),
            "ranked_lists": ranked_lists,
            "max_rrf_score": round(ranked_lists / (RRF_K + 1), 4),
            "results": ranked,
            "duration_ms": _ms_since(started),
        },
        call_id=tool_call_id,
    )
    if not results:
        return "No relevant passages found in the university documents.", []
    return "\n\n".join(parts), artifact


@tool(response_format="content_and_artifact")
def query_courses(
    code: str,
    follow_prerequisites: bool = False,
    # Hidden from the model's schema, as in search_documents.
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None,
) -> tuple[str, list[dict]]:
    """Look up a specific AUI course by its code (e.g. "ACC 2302") in the structured
    course catalog. Returns its title, credits, and prerequisites/corequisites exactly
    as stated in the catalog.

    Set follow_prerequisites=True to also return the FULL prerequisite chain --
    every course referenced directly or indirectly, each with its own
    prerequisites in the catalog's wording -- for questions like "what do I
    need before taking X?".

    Use this tool, not search_documents, whenever the question names or implies a
    specific course code or asks about prerequisite chains.
    """
    started = time.perf_counter()
    text, artifact, lookup = _look_up_course(code, follow_prerequisites)
    record_tool_step(
        "query_courses",
        {
            "args": {"code": code, "follow_prerequisites": follow_prerequisites},
            **lookup,
            "duration_ms": _ms_since(started),
        },
        call_id=tool_call_id,
    )
    return text, artifact


def _look_up_course(code: str, follow_prerequisites: bool) -> tuple[str, list[dict], dict]:
    """query_courses' work: (the text the model reads, the citations, what was
    found, for the trace). `found` is "course", "no_description" (referenced
    as a prerequisite but with no course entry) or "not_found"."""
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
        is_referenced = conn.execute(
            "SELECT 1 FROM course_prerequisites WHERE prerequisite_code = %s LIMIT 1",
            (code,),
        ).fetchone()
        conn.close()
        if is_referenced:
            return (
                (
                    f"{code} is {NO_DESCRIPTION_NOTE}. Other parts of the catalog (e.g. program "
                    "requirements) may still mention it: try search_documents, or suggest "
                    "checking with an academic advisor."
                ),
                [],
                {"found": "no_description"},
            )
        return (
            f"No course found with code '{code}' in AUI's course catalog.",
            [],
            {"found": "not_found"},
        )

    code_, dept, title, credits, prereq_text, coreq_text, page = row
    # Same course looked up twice (e.g. again with follow_prerequisites) keeps
    # its number. The text is always sent in full: the chain part can differ.
    marker, _ = citation_number_for(("course", code_))
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

    chain_length = None  # not looked up
    if follow_prerequisites:
        chain = _prerequisite_chain(conn, code_)
        chain_length = len(chain)
        if chain:
            lines.append(
                f"Full prerequisite chain for [{marker}], each course listed once with its own "
                "prerequisites in the catalog's exact wording (step 1 = direct prerequisite). "
                'A course appearing here is not necessarily required: "or" in a course\'s '
                "wording marks alternatives."
            )
            lines.extend(_chain_line(*row) for row in chain)
        else:
            lines.append(
                "No further prerequisite chain found in the structured data (either this "
                "course has no prerequisites, or its prerequisites aren't other AUI courses)."
            )

    conn.close()
    text = "\n".join(lines)
    pages = [page] if page is not None else None
    # Returned on a repeated lookup too, unlike search_documents: the text can
    # differ (a second lookup may add the chain), and a claim citing [marker]
    # may rest on either version. keep_cited still lists the marker once.
    citation = {
        "marker": marker,
        "source": CATALOG_SOURCE,
        "pages": pages,
        "section": f"Course {code_}",  # shown on its source card
        "text": text,
    }
    lookup = {
        "found": "course",
        "marker": marker,
        "title": title,
        "pages": pages,
        "chain_length": chain_length,
    }
    return text, [citation], lookup


# Walks the prerequisite graph from one course. Each row carries the path
# walked so far; an edge leading back into its own path is a cycle and isn't
# followed, so a cycle in the data can't make the walk loop. The depth cap is
# only a backstop. A course reachable by several paths is walked once per path,
# then GROUP BY lists it once, at its shortest distance.
PREREQUISITE_CHAIN_SQL = """
    WITH RECURSIVE chain AS (
        SELECT prerequisite_code AS code, 1 AS depth,
               ARRAY[course_code, prerequisite_code] AS path
        FROM course_prerequisites
        WHERE course_code = %(code)s
        UNION ALL
        SELECT cp.prerequisite_code, chain.depth + 1, chain.path || cp.prerequisite_code
        FROM course_prerequisites cp
        JOIN chain ON cp.course_code = chain.code
        WHERE NOT cp.prerequisite_code = ANY(chain.path)
          AND chain.depth < 10
    )
    SELECT chain.code, min(chain.depth) AS depth, c.title, c.prerequisites_text
    FROM chain
    LEFT JOIN courses c ON c.code = chain.code
    GROUP BY chain.code, c.title, c.prerequisites_text
    ORDER BY depth, chain.code
"""


def _prerequisite_chain(conn, code: str) -> list[tuple]:
    """Every course in `code`'s prerequisite chain, once each:
    (code, depth, title, prerequisites_text). Title is None for a referenced
    code with no extracted course row (see schema.sql)."""
    return conn.execute(PREREQUISITE_CHAIN_SQL, {"code": code}).fetchall()


def _chain_line(code: str, depth: int, title: str | None, prereq_text: str | None) -> str:
    if title is None:
        return f"  - {code} (step {depth}) -- {NO_DESCRIPTION_NOTE}"
    return f"  - {code}: {title} (step {depth}) -- requires: {prereq_text or 'none listed'}"
