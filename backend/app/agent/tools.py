"""Tools available to the LangGraph agent."""

from langchain_core.tools import tool

from app.retrieval.hybrid_search import search_hybrid


@tool
def search_documents(query: str) -> str:
    """Search Al Akhawayn University's academic catalog and scholarship pages.

    Use this for any question about academic policies, course requirements,
    grading, registration, admissions, or scholarships/fellowships that might
    be described in official university documents. Returns relevant passages
    with numbered citations like [1], [2].
    """
    results = search_hybrid(query, top_k=5)
    if not results:
        return "No relevant passages found in the university documents."

    parts = [
        f"[{i}] (source: {r.source}, pages: {r.pages})\n{r.text}"
        for i, r in enumerate(results, start=1)
    ]
    return "\n\n".join(parts)
