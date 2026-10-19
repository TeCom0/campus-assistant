"""Evaluate retrieval functions against the hand-labeled ground truth in
eval/retrieval_eval_set.json, reporting Hit Rate@k and Mean Reciprocal Rank (MRR),
overall and per language.

Each question's expected answer is a text ANCHOR (a verbatim sentence of the
answer), not a chunk number: a result is a hit if it comes from the expected
source and its text contains the anchor (whitespace, case and curly quotes
ignored). Chunk numbers change whenever the documents are re-chunked; the
answer text doesn't. `--check-anchors` lists the chunks holding each anchor
and fails if one is in no chunk (e.g. split by a chunk boundary).

"hybrid + English" fuses the question with its English version
(`question_en`, set on the French questions: their English twins in the set),
as the search_documents tool does on a first turn. For an English question
both are the same query, so it equals "hybrid".
"""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from app.db.connection import get_connection
from app.retrieval.hybrid_search import search_hybrid, search_hybrid_multi
from app.retrieval.keyword_search import search_keyword
from app.retrieval.vector_search import search_vector

EVAL_SET_PATH = Path(__file__).resolve().parents[3] / "eval" / "retrieval_eval_set.json"
TOP_K = 10
HIT_RATE_KS = (3, 5)


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


_QUOTE_FIXES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def normalize_text(text: str) -> str:
    """Whitespace runs to one space, curly quotes to straight, case folded."""
    return " ".join(text.translate(_QUOTE_FIXES).split()).casefold()


def contains_anchor(source: str, text: str, expected: dict) -> bool:
    return source == expected["source"] and normalize_text(expected["anchor"]) in normalize_text(
        text
    )


def rank_of_first_match(results, expected: list[dict]) -> int | None:
    """1-based rank of the first result containing an expected anchor, or None if not found."""
    for i, r in enumerate(results, start=1):
        if any(contains_anchor(r.source, r.text, e) for e in expected):
            return i
    return None


def anchor_locations(questions: list[dict], chunks: list[tuple[str, int, str]]) -> list[dict]:
    """For each question's anchor: the chunk indexes (in its source) whose text holds it."""
    return [
        {
            "id": q["id"],
            "anchor": e["anchor"],
            "chunks": [i for source, i, text in chunks if contains_anchor(source, text, e)],
        }
        for q in questions
        for e in q["expected"]
    ]


def check_anchors(questions: list[dict]) -> bool:
    """Print where each anchor is in the database; False if one is in no chunk."""
    conn = get_connection()
    chunks = conn.execute("SELECT source, chunk_index, text FROM document_chunks").fetchall()
    conn.close()
    ok = True
    for loc in anchor_locations(questions, chunks):
        status = "OK  " if loc["chunks"] else "LOST"
        ok = ok and bool(loc["chunks"])
        print(f"{status} {loc['id']:<28} chunks {loc['chunks']}  {loc['anchor'][:60]!r}")
    return ok


# Targeted checks for Fix C (section context in chunks), defined before any
# variant was measured (CLAUDE.md, 2026-10-19).
REPEAT_QUERY = "What is the repeat policy for undergraduate students?"
UNDERGRADUATE_REPEAT_RULE = "a C- or lower has been earned"
GRADUATE_REPEAT_RULE = "a B- or lower has been earned"
NINE_SEMESTERS = "maximum of nine semesters"
NINE_SEMESTERS_SENTENCE = (
    "Undergraduate beneficiaries are eligible for AUI scholarship for a maximum of nine "
    "semesters (or eight semesters plus two summer sessions), while graduate scholarships are "
    "allowed to use their scholarship for a maximum of four semesters, including one semester "
    "at the Language Center."
)


def first_rank_with(results, fragment: str) -> int | None:
    """1-based rank of the first result whose text contains `fragment`."""
    for i, r in enumerate(results, start=1):
        if normalize_text(fragment) in normalize_text(r.text):
            return i
    return None


def repeat_policy_order(results) -> tuple[bool, int | None, int | None]:
    """Check 1: the undergraduate rule ranks above the graduate one (or that's absent)."""
    undergraduate = first_rank_with(results, UNDERGRADUATE_REPEAT_RULE)
    graduate = first_rank_with(results, GRADUATE_REPEAT_RULE)
    ok = undergraduate is not None and (graduate is None or undergraduate < graduate)
    return ok, undergraduate, graduate


def nine_semesters_whole(texts: list[str]) -> tuple[bool, int, int]:
    """Check 2: every chunk with "maximum of nine semesters" holds its full sentence."""
    with_phrase = [t for t in texts if normalize_text(NINE_SEMESTERS) in normalize_text(t)]
    whole = [t for t in with_phrase if normalize_text(NINE_SEMESTERS_SENTENCE) in normalize_text(t)]
    return bool(with_phrase) and len(whole) == len(with_phrase), len(with_phrase), len(whole)


def run_targeted_checks() -> bool:
    ok1, undergraduate, graduate = repeat_policy_order(search_hybrid(REPEAT_QUERY, TOP_K))
    print(
        f"{'PASS' if ok1 else 'FAIL'} check 1, repeat policy order for {REPEAT_QUERY!r}: "
        f"undergraduate rule (C-) at rank {undergraduate}, graduate rule (B-) at rank {graduate}"
    )
    conn = get_connection()
    texts = [r[0] for r in conn.execute("SELECT text FROM document_chunks").fetchall()]
    conn.close()
    ok2, with_phrase, whole = nine_semesters_whole(texts)
    print(
        f"{'PASS' if ok2 else 'FAIL'} check 2, nine-semesters sentence: {whole} of {with_phrase} "
        f"chunks with {NINE_SEMESTERS!r} hold the full sentence"
    )
    return ok1 and ok2


def run_eval(search_fn: Callable[[dict, int], list], name: str, questions: list[dict]) -> dict:
    """search_fn gets the whole eval question, so a method can use question_en."""
    hit_counts = dict.fromkeys(HIT_RATE_KS, 0)
    reciprocal_ranks = []
    hits3_by_language: dict[str, list[bool]] = {}

    print(f"\n=== {name} ===")
    print(f"{'id':<28} {'lang':<5} {'rank':<6} {'hit@3':<6} {'hit@5':<6}")
    for q in questions:
        results = search_fn(q, TOP_K)
        rank = rank_of_first_match(results, q["expected"])

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
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check-anchors", action="store_true", help="Only check each anchor is in some chunk"
    )
    parser.add_argument(
        "--targeted", action="store_true", help="Only run Fix C's two targeted checks"
    )
    args = parser.parse_args()
    all_questions = load_eval_set()
    if args.check_anchors:
        sys.exit(0 if check_anchors(all_questions) else 1)
    if args.targeted:
        sys.exit(0 if run_targeted_checks() else 1)
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
