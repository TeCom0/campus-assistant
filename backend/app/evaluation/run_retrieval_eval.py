"""Evaluate a retrieval function against the hand-labeled ground truth in
eval/retrieval_eval_set.json, reporting Hit Rate@k and Mean Reciprocal Rank (MRR).
"""

import json
from pathlib import Path

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


def run_eval() -> None:
    questions = load_eval_set()
    hit_counts = dict.fromkeys(HIT_RATE_KS, 0)
    reciprocal_ranks = []

    print(f"{'id':<28} {'lang':<5} {'rank':<6} {'hit@3':<6} {'hit@5':<6}")
    for q in questions:
        expected = {(e["source"], e["chunk_index"]) for e in q["expected"]}
        results = search_vector(q["question"], top_k=TOP_K)
        rank = rank_of_first_match(results, expected)

        for k in HIT_RATE_KS:
            if rank is not None and rank <= k:
                hit_counts[k] += 1
        reciprocal_ranks.append(1 / rank if rank else 0.0)

        hit3 = "yes" if rank and rank <= 3 else "no"
        hit5 = "yes" if rank and rank <= 5 else "no"
        print(f"{q['id']:<28} {q['language']:<5} {rank or '-'!s:<6} {hit3:<6} {hit5:<6}")

    n = len(questions)
    print()
    for k in HIT_RATE_KS:
        print(f"Hit Rate@{k}: {hit_counts[k]}/{n} ({100 * hit_counts[k] / n:.1f}%)")
    print(f"MRR (top_k={TOP_K}): {sum(reciprocal_ranks) / n:.3f}")


if __name__ == "__main__":
    run_eval()
