"""Evaluate retrieval functions against the hand-labeled ground truth in
eval/retrieval_eval_set.json, reporting Hit Rate@k and Mean Reciprocal Rank (MRR),
overall and per language.

"hybrid + English" fuses the question with its English version
(`question_en`, set on the French questions: their English twins in the set),
as the search_documents tool does on a first turn. For an English question
both are the same query, so it equals "hybrid".
"""

import json
from collections.abc import Callable
from pathlib import Path

from app.retrieval.hybrid_search import search_hybrid, search_hybrid_multi
from app.retrieval.keyword_search import search_keyword
from app.retrieval.vector_search import search_vector

EVAL_SET_PATH = Path(__file__).resolve().parents[3] / "eval" / "retrieval_eval_set.json"
TOP_K = 10
HIT_RATE_KS = (3, 5)


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


def rank_of_first_match(results, expected: set[tuple[str, int]]) -> int | None:
    """1-based rank of the first result matching an expected chunk, or None if not found."""
    for i, r in enumerate(results, start=1):
        if (r.source, r.chunk_index) in expected:
            return i
    return None


def run_eval(search_fn: Callable[[dict, int], list], name: str, questions: list[dict]) -> dict:
    """search_fn gets the whole eval question, so a method can use question_en."""
    hit_counts = dict.fromkeys(HIT_RATE_KS, 0)
    reciprocal_ranks = []
    hits3_by_language: dict[str, list[bool]] = {}

    print(f"\n=== {name} ===")
    print(f"{'id':<28} {'lang':<5} {'rank':<6} {'hit@3':<6} {'hit@5':<6}")
    for q in questions:
        expected = {(e["source"], e["chunk_index"]) for e in q["expected"]}
        results = search_fn(q, TOP_K)
        rank = rank_of_first_match(results, expected)

        for k in HIT_RATE_KS:
            if rank is not None and rank <= k:
                hit_counts[k] += 1
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        hits3_by_language.setdefault(q["language"], []).append(bool(rank and rank <= 3))

        hit3 = "yes" if rank and rank <= 3 else "no"
        hit5 = "yes" if rank and rank <= 5 else "no"
        print(f"{q['id']:<28} {q['language']:<5} {rank or '-'!s:<6} {hit3:<6} {hit5:<6}")

    n = len(questions)
    summary = {
        "name": name,
        "hit_rate": {k: hit_counts[k] / n for k in HIT_RATE_KS},
        "mrr": sum(reciprocal_ranks) / n,
        "hit3_by_language": {
            lang: f"{sum(hits)}/{len(hits)}" for lang, hits in sorted(hits3_by_language.items())
        },
    }
    print()
    for k in HIT_RATE_KS:
        print(f"Hit Rate@{k}: {hit_counts[k]}/{n} ({100 * summary['hit_rate'][k]:.1f}%)")
    print(f"MRR (top_k={TOP_K}): {summary['mrr']:.3f}")
    return summary


if __name__ == "__main__":
    all_questions = load_eval_set()
    methods = {
        "vector": lambda q, k: search_vector(q["question"], k),
        "keyword": lambda q, k: search_keyword(q["question"], k),
        "hybrid": lambda q, k: search_hybrid(q["question"], k),
        "hybrid + English": lambda q, k: search_hybrid_multi(
            [q["question"], q.get("question_en", q["question"])], k
        ),
    }
    summaries = [run_eval(fn, name, all_questions) for name, fn in methods.items()]

    print("\n=== summary ===")
    print(f"{'method':<18} {'hit@3':<8} {'hit@5':<8} {'mrr':<7} hit@3 by language")
    for s in summaries:
        print(
            f"{s['name']:<18} {100 * s['hit_rate'][3]:<7.1f}% "
            f"{100 * s['hit_rate'][5]:<7.1f}% {s['mrr']:<7.3f} {s['hit3_by_language']}"
        )
