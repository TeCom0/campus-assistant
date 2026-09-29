"""Vector similarity search over document_chunks using pgvector."""

from dataclasses import dataclass

from pgvector import Vector

from app.db.connection import get_connection
from app.embeddings import embed_query


@dataclass
class SearchResult:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    distance: float  # cosine distance: 0 = identical direction, 2 = opposite. Lower is better.


def search_vector(query: str, top_k: int = 5) -> list[SearchResult]:
    """Return the top_k chunks whose embeddings are closest (cosine distance) to the query."""
    query_vector = Vector(embed_query(query))

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT source, chunk_index, pages, text, embedding <=> %s AS distance
        FROM document_chunks
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (query_vector, query_vector, top_k),
    ).fetchall()
    conn.close()

    return [
        SearchResult(source=r[0], chunk_index=r[1], pages=r[2], text=r[3], distance=r[4])
        for r in rows
    ]


if __name__ == "__main__":
    for result in search_vector("How many credits can I transfer to AUI?", top_k=3):
        print(
            f"--- {result.source} chunk={result.chunk_index} "
            f"pages={result.pages} distance={result.distance:.4f} ---"
        )
        print(result.text[:200])
        print()
