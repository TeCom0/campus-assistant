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
    vector_rank: int | None
    keyword_rank: int | None


def search_hybrid(query: str, top_k: int = 5) -> list[HybridResult]:
    vector_results = search_vector(query, top_k=CANDIDATE_POOL_SIZE)
    keyword_results = search_keyword(query, top_k=CANDIDATE_POOL_SIZE)

    scores: dict[tuple[str, int], float] = {}
    info: dict[tuple[str, int], object] = {}
    vector_ranks: dict[tuple[str, int], int] = {}
    keyword_ranks: dict[tuple[str, int], int] = {}

    for rank, r in enumerate(vector_results, start=1):
        key = (r.source, r.chunk_index)
        scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)
        info.setdefault(key, r)
        vector_ranks[key] = rank

    for rank, r in enumerate(keyword_results, start=1):
        key = (r.source, r.chunk_index)
        scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)
        info.setdefault(key, r)
        keyword_ranks[key] = rank

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


if __name__ == "__main__":
    for result in search_hybrid("How do I add or drop a course at AUI?", top_k=5):
        print(
            f"--- {result.source} chunk={result.chunk_index} pages={result.pages} "
            f"rrf={result.rrf_score:.4f} vector_rank={result.vector_rank} "
            f"keyword_rank={result.keyword_rank} ---"
        )
        print(result.text[:200])
        print()
