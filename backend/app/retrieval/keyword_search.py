"""Keyword search over document_chunks using Postgres's built-in full-text
search (tsvector/GIN index + ts_rank).

Note: this is Postgres's own text-search ranking, not the Okapi BM25
algorithm specifically -- a related but different ranking function. Chosen
over a separate BM25 implementation/search engine to avoid new
infrastructure, per CLAUDE.md's "Postgres full-text search or BM25" note.
"""

from dataclasses import dataclass, field

from app.db.connection import get_connection


@dataclass
class SearchResult:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    score: float  # ts_rank: higher is better (unlike vector_search's distance)
    section: str | None = None  # nearest heading (app/ingestion/chunk.py), for source cards
    level: str = "general"  # general / undergraduate / graduate, for source cards
    sections: list[str] = field(default_factory=list)  # every heading spanned, for source cards


def search_keyword(query: str, top_k: int = 5) -> list[SearchResult]:
    """Return the top_k chunks ranked by Postgres full-text search relevance."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT source, chunk_index, pages, text,
               ts_rank(text_search, websearch_to_tsquery('english', %s)) AS score, section, level,
               sections
        FROM document_chunks
        WHERE text_search @@ websearch_to_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, query, top_k),
    ).fetchall()
    conn.close()

    return [
        SearchResult(
            source=r[0],
            chunk_index=r[1],
            pages=r[2],
            text=r[3],
            score=r[4],
            section=r[5],
            level=r[6],
            sections=r[7],
        )
        for r in rows
    ]


if __name__ == "__main__":
    for result in search_keyword("transfer credits maximum", top_k=3):
        print(
            f"--- {result.source} chunk={result.chunk_index} "
            f"pages={result.pages} score={result.score:.4f} ---"
        )
        print(result.text[:200])
        print()
