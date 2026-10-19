"""Tests for RRF fusion in hybrid search, single and multi-query.

The vector and keyword searches are replaced by stubs returning fixed ranked
lists per query, so these need no database or embedding model.
"""

from dataclasses import dataclass

import pytest

from app.retrieval import hybrid_search
from app.retrieval.hybrid_search import RRF_K, search_hybrid, search_hybrid_multi


@dataclass
class _Hit:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    section: str | None = None
    level: str = "general"
    sections: tuple = ()


def _hits(*chunk_indexes: int) -> list[_Hit]:
    return [_Hit("catalog", i, [i], f"text {i}") for i in chunk_indexes]


@pytest.fixture
def stub_searches(monkeypatch):
    """Install stub searches; returns the list of (method, query) calls made."""
    calls: list[tuple[str, str]] = []

    def install(vector: dict[str, list[int]], keyword: dict[str, list[int]]):
        def search_vector(query, top_k):
            calls.append(("vector", query))
            return _hits(*vector.get(query, []))[:top_k]

        def search_keyword(query, top_k):
            calls.append(("keyword", query))
            return _hits(*keyword.get(query, []))[:top_k]

        monkeypatch.setattr(hybrid_search, "search_vector", search_vector)
        monkeypatch.setattr(hybrid_search, "search_keyword", search_keyword)
        return calls

    return install


def test_single_query_sums_one_over_k_plus_rank(stub_searches):
    stub_searches(vector={"q": [10, 20]}, keyword={"q": [20, 30]})
    results = search_hybrid("q", top_k=5)

    assert [r.chunk_index for r in results] == [20, 10, 30]  # in both lists -> first
    assert results[0].rrf_score == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert (results[0].vector_rank, results[0].keyword_rank) == (2, 1)
    assert (results[1].vector_rank, results[1].keyword_rank) == (1, None)


def test_single_query_is_multi_query_with_one_query(stub_searches):
    stub_searches(vector={"q": [3, 1, 2]}, keyword={"q": [2, 4]})
    assert search_hybrid("q", top_k=3) == search_hybrid_multi(["q"], top_k=3)


def test_a_passage_only_the_english_query_finds_reaches_the_top_k(stub_searches):
    # The French query finds only unrelated chunks; the English one finds 99.
    stub_searches(
        vector={"bourse": [1, 2, 3, 4, 5], "scholarship": [99, 1]},
        keyword={"scholarship": [99]},  # French words match no English text
    )
    results = search_hybrid_multi(["bourse", "scholarship"], top_k=5)

    assert results[0].chunk_index == 99  # top of two English lists
    assert len(results) == 5


def test_a_passage_found_by_both_queries_is_one_result_with_summed_score(stub_searches):
    stub_searches(vector={"fr": [7], "en": [8, 7]}, keyword={})
    results = search_hybrid_multi(["fr", "en"], top_k=5)

    sevens = [r for r in results if r.chunk_index == 7]
    assert len(sevens) == 1
    assert sevens[0].rrf_score == pytest.approx(1 / (RRF_K + 1) + 1 / (RRF_K + 2))
    assert sevens[0].vector_rank == 1  # the best rank over both queries


def test_repeated_queries_are_searched_once(stub_searches):
    calls = stub_searches(vector={"Repeat policy": [1]}, keyword={})
    search_hybrid_multi(["Repeat policy", "  repeat   POLICY ", "", "   "], top_k=5)

    assert calls == [("vector", "Repeat policy"), ("keyword", "Repeat policy")]


def test_no_queries_give_no_results(stub_searches):
    calls = stub_searches(vector={}, keyword={})
    assert search_hybrid_multi([], top_k=5) == []
    assert calls == []
