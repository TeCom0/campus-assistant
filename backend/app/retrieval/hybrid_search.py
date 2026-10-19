"""Hybrid search: merge vector and keyword search results via Reciprocal Rank
Fusion (RRF).

RRF combines ranked lists using only each item's RANK in each list, not its
raw score -- necessary here because vector search's cosine distance and
keyword search's ts_rank are on incompatible scales (different units,
different ranges, not directly comparable or summable).
"""

from dataclasses import dataclass

from app.retrieval.keyword_search import search_keyword
from app.retrieval.vector_search import search_vector

# From Cormack et al. 2009 ("Reciprocal Rank Fusion outperforms Condorcet and
# individual Rank Learning Methods"), the standard constant for RRF: dampens
# the gap between e.g. rank 1 and rank 2, so one method's top result doesn't
# automatically dominate the merge.
RRF_K = 60

# How many candidates to pull from EACH method before merging -- wider than
# the final top_k we return, so RRF has a real pool to combine from.
CANDIDATE_POOL_SIZE = 20


@dataclass
class HybridResult:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    rrf_score: float
    # Best (lowest) rank in any query's vector / keyword list; None if in none.
    vector_rank: int | None
    keyword_rank: int | None


def _unique_queries(queries: list[str]) -> list[str]:
    """The queries in order, without blanks or repeats (ignoring case and spacing).

    For an English question the agent's English version is usually the query
    itself; searching it twice would double every score and change nothing.
    """
    unique, seen = [], set()
    for query in queries:
        key = " ".join(query.split()).casefold()
        if key and key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def search_hybrid_multi(queries: list[str], top_k: int = 5) -> list[HybridResult]:
    """Hybrid search for several phrasings of one search, fused into one ranking.

    Each query gets its own vector and keyword list, and RRF fuses all of
    them at once: a passage's score is the sum of 1 / (RRF_K + rank) over
    every list it appears in. A passage only one phrasing finds can still
    make the top_k (an English version finds what a French query can't: the
    documents are in English), and one several phrasings agree on rises.
    """
    scores: dict[tuple[str, int], float] = {}
    info: dict[tuple[str, int], object] = {}
    vector_ranks: dict[tuple[str, int], int] = {}
    keyword_ranks: dict[tuple[str, int], int] = {}

    for query in _unique_queries(queries):
        vector_results = search_vector(query, top_k=CANDIDATE_POOL_SIZE)
        keyword_results = search_keyword(query, top_k=CANDIDATE_POOL_SIZE)
        for results, ranks in ((vector_results, vector_ranks), (keyword_results, keyword_ranks)):
            for rank, r in enumerate(results, start=1):
                key = (r.source, r.chunk_index)
                scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)
                info.setdefault(key, r)
                ranks[key] = min(rank, ranks.get(key, rank))

    ranked_keys = sorted(scores, key=lambda k: scores[k], reverse=True)[:top_k]

    return [
        HybridResult(
            source=key[0],
            chunk_index=key[1],
            pages=info[key].pages,
            text=info[key].text,
            rrf_score=scores[key],
            vector_rank=vector_ranks.get(key),
            keyword_rank=keyword_ranks.get(key),
        )
        for key in ranked_keys
    ]


def search_hybrid(query: str, top_k: int = 5) -> list[HybridResult]:
    """Hybrid search for one query: its vector and keyword lists fused by RRF."""
    return search_hybrid_multi([query], top_k)


if __name__ == "__main__":
    for result in search_hybrid("How do I add or drop a course at AUI?", top_k=5):
        print(
            f"--- {result.source} chunk={result.chunk_index} pages={result.pages} "
            f"rrf={result.rrf_score:.4f} vector_rank={result.vector_rank} "
            f"keyword_rank={result.keyword_rank} ---"
        )
        print(result.text[:200])
        print()
