"""Stage 3 of the faithfulness evaluation: an LLM judge labels each claim from
split_claims.py as supported / unsupported / no_claim against the passages it
is checked against.

The judge is Gemini, a different model family from the Groq model that wrote
the answers (a model judging its own family's output tends to be lenient).
Answers are judged ANSWERS_PER_CALL at a time, each in its own block: the
free tier allows only 20 requests a day (one call per answer = 32 calls per
run didn't fit). The output is forced into a JSON schema (BatchVerdict), so
it's validated, not parsed out of free text. Strict: partly supported is
unsupported. A "supported" verdict must quote its evidence verbatim, and code
checks the quote really is in that claim's passages; if not, the claim counts
as unsupported (flag quote_not_found) -- that also catches a judge leaning on a
passage the claim didn't cite.

Claims auto-labelled by split_claims.py (markers no tool returned) are never
sent. Run 1 is hand-labelled blind, so the judge refuses to run on it before
every claim in the labels file is labelled (hand_labels.py).

Usage (from backend/):
    python -m app.evaluation.judge_claims --calibration   # known answers, check the judge
    python -m app.evaluation.judge_claims --run 1 --dry-run --ids plagiarism_fr   # show prompt
    python -m app.evaluation.judge_claims --run 2
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.evaluation.generate_faithfulness_answers import EVAL_DIR, RESULTS_DIR
from app.evaluation.hand_labels import labels_complete, reference_labels_path

CALIBRATION_PATH = EVAL_DIR / "judge_calibration.json"
HAND_LABELLED_RUNS = {1}
# Failed attempts count toward the free tier's 20 requests/day (2026-10-12: 2
# successful calls + 18 failed 503s, then a daily 429), so retry rarely and wait
# long: 120 s, then 240 s. A 503 "high demand" spell lasts minutes; when it's
# still on after that, the batch stops and a later re-run resumes it.
RATE_LIMIT_WAIT_SECONDS = 120
RATE_LIMIT_RETRIES = 2
ANSWERS_PER_CALL = 4

JUDGE_INSTRUCTIONS = """You check whether the claims in a university assistant's answers are \
supported by the source passages the assistant was given. You are strict: students may act on \
these answers.

The input contains one or more independent ANSWER blocks. Passage numbers belong to their own \
block: [1] in one block has nothing to do with [1] in another. For each claim, use ONLY the \
passages of its own block listed for it under "check against". Never use outside knowledge, \
even when the claim is true.

Labels:
- supported: everything the claim states is stated in, or directly follows from, those \
passages. A paraphrase or a translation (e.g. a French claim from an English passage) is fine \
if the meaning is the same.
- unsupported: any part of the claim is missing from those passages or contradicts them. \
Partly supported counts as unsupported. Numbers, dates, grades, names and course codes must \
match exactly. A rule the passage states for a narrower group (e.g. graduate courses, one \
school, one program) but the claim presents as general, or as applying to a different group \
(e.g. the student asking), is unsupported.
- no_claim: the piece states no checkable fact about the university -- advice ("ask your \
advisor"), filler, a question, an introductory fragment ("You can transfer:"), or a statement \
about the assistant's own search ("I couldn't find ...").

evidence_quote: for supported, copy the shortest span that shows the support VERBATIM from one \
of the claim's passages, in the passage's own language (at most about 300 characters; you may \
join two spans with "..."). For unsupported and no_claim, use "".
reason: one short sentence; for unsupported, say what is missing or wrong.
abstains (one entry per answer block, by its answer id): true if that answer as a whole says \
it can't answer because the information isn't available; false otherwise.

Return exactly one verdict per claim id listed, using the ids as given, and one abstains entry \
per answer id."""


class ClaimVerdict(BaseModel):
    claim_id: str
    label: Literal["supported", "unsupported", "no_claim"]
    evidence_quote: str
    reason: str


class AnswerAbstains(BaseModel):
    answer_id: str
    abstains: bool


class BatchVerdict(BaseModel):
    answers: list[AnswerAbstains]
    verdicts: list[ClaimVerdict]


def build_prompt(items: list[dict]) -> str:
    """One block per answer: its question, the answer, its passages, its claims.

    Each item: {"id", "question", "answer", "passages", "claims"}, with the
    auto-labelled claims already left out.
    """
    lines = []
    for item in items:
        lines += [
            f"\n========== ANSWER {item['id']} ==========",
            f"QUESTION:\n{item['question']}",
            f"\nANSWER (for context):\n{item['answer']}",
            f"\nPASSAGES (of answer {item['id']} only):",
        ]
        for p in item["passages"]:
            text = "\n--- (same marker, returned again with more text) ---\n".join(p["texts"])
            lines.append(f"\n[{p['marker']}] (source: {p['source']}, pages: {p['pages']})\n{text}")
        lines.append(f"\nCLAIMS (of answer {item['id']}):")
        for c in item["claims"]:
            scope = ", ".join(f"[{m}]" for m in c["markers"]) if c["markers"] else "all passages"
            lines.append(f"- id: {c['claim_id']} | check against: {scope} | claim: {c['text']}")
    return "\n".join(lines).strip()


_QUOTE_CHARS = str.maketrans(
    {"’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"', "–": "-", "—": "-", "‑": "-",
     " ": " ", " ": " ", "*": None}
)  # fmt: skip


def normalize_for_quote(text: str) -> str:
    """Lowercase, one kind of quote/dash/space, single spaces: PDF text has line
    breaks where the judge's quote has spaces."""
    return " ".join(text.translate(_QUOTE_CHARS).split()).lower()


def quote_found(quote: str, texts: list[str]) -> bool:
    """Every part of the quote ("a ... b") appears, in order, in one of the texts."""
    parts = [normalize_for_quote(p) for p in re.split(r"\.\.\.|…", quote)]
    parts = [p for p in parts if p]
    if not parts:
        return False
    for text in texts:
        haystack, position = normalize_for_quote(text), 0
        for part in parts:
            position = haystack.find(part, position)
            if position < 0:
                break
            position += len(part)
        else:
            return True
    return False


def merge_verdicts(
    claims: list[dict], passages: list[dict], verdicts: list[ClaimVerdict]
) -> list[dict]:
    """One result per claim: the judge's label, the quote check, the final label."""
    texts_by_marker = {p["marker"]: p["texts"] for p in passages}
    all_texts = [t for p in passages for t in p["texts"]]
    by_id: dict[str, ClaimVerdict] = {}
    for v in verdicts:
        by_id.setdefault(v.claim_id, v)  # a duplicate verdict: the first one counts

    results = []
    for c in claims:
        result = {"claim_id": c["claim_id"], "kind": c["kind"], "markers": c["markers"]}
        if c["auto_label"]:
            results.append(
                {
                    **result,
                    "judge_label": None,
                    "label": c["auto_label"],
                    "flag": "invalid_citation",
                }
            )
            continue
        v = by_id.get(c["claim_id"])
        if v is None:
            results.append({**result, "judge_label": None, "label": None, "flag": "no_verdict"})
            continue
        texts = (
            [t for m in c["markers"] for t in texts_by_marker.get(m, [])]
            if c["markers"]
            else all_texts
        )
        label, flag = v.label, None
        if v.label == "supported" and not quote_found(v.evidence_quote, texts):
            label, flag = "unsupported", "quote_not_found"
        results.append(
            {
                **result,
                "judge_label": v.label,
                "label": label,
                "flag": flag,
                "evidence_quote": v.evidence_quote,
                "reason": v.reason,
            }
        )
    return results


def call_judge(client: genai.Client, prompt: str) -> tuple[BatchVerdict, int]:
    """One Gemini call. Waits out what clears by itself -- a per-minute rate limit
    (429) or the model being overloaded (503 "high demand", seen 2026-10-11) --
    and raises on a daily limit or after the retries."""
    config = genai_types.GenerateContentConfig(
        system_instruction=JUDGE_INSTRUCTIONS,
        response_mime_type="application/json",
        response_schema=BatchVerdict,
        temperature=0,
        automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
    )
    for attempt in range(1, RATE_LIMIT_RETRIES + 2):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt, config=config
            )
            break
        except (genai_errors.ClientError, genai_errors.ServerError) as e:
            per_day = "PerDay" in str(e) or "per day" in str(e).lower()
            transient = (e.code == 429 and not per_day) or e.code == 503
            if transient and attempt <= RATE_LIMIT_RETRIES:
                wait = RATE_LIMIT_WAIT_SECONDS * attempt
                print(f"  Gemini {e.code}, waiting {wait}s")
                time.sleep(wait)
                continue
            raise
    if response.parsed is None:
        raise ValueError(f"judge output didn't match the schema: {response.text[:300]!r}")
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    return response.parsed, tokens or 0


def judge_batch(client, answers: list[dict]) -> tuple[dict[str, tuple], int]:
    """Judge several answers in one call.

    Each answer: {"id", "question", "answer", "passages", "claims"} (all its
    claims, auto-labelled ones included). Returns {answer id: (abstains,
    per-claim results)} and the call's tokens. abstains is None if the judge
    skipped that answer; an answer with nothing to ask isn't sent.
    """
    items = [{**a, "claims": [c for c in a["claims"] if not c["auto_label"]]} for a in answers]
    items = [i for i in items if i["claims"]]
    verdict, tokens = call_judge(client, build_prompt(items)) if items else (None, 0)
    claim_verdicts = verdict.verdicts if verdict else []
    abstains = {a.answer_id: a.abstains for a in verdict.answers} if verdict else {}
    judged = {}
    for a in answers:
        results = merge_verdicts(a["claims"], a["passages"], claim_verdicts)
        judged[a["id"]] = (abstains.get(a["id"]), results)
    return judged, tokens


def _client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set (check .env)")
    return genai.Client(api_key=GEMINI_API_KEY)


def run_calibration() -> tuple[int, int]:
    """Judge hand-made claims with known labels; prints judge vs. expected."""
    cases = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    answers = [{**case, "answer": " ".join(c["text"] for c in case["claims"])} for case in cases]
    judged, tokens = judge_batch(_client(), answers)  # all cases in one call, as in a run
    print(f"{len(cases)} cases in one call, {tokens} tokens")
    agree, total = 0, 0
    for case in cases:
        _, results = judged[case["id"]]
        print(f"\n=== {case['id']}")
        for claim, r in zip(case["claims"], results, strict=True):
            ok = r["label"] == claim["expected"]
            agree, total = agree + ok, total + 1
            flag = f" [{r['flag']}]" if r["flag"] else ""
            print(
                f"  {'OK  ' if ok else 'MISS'} expected {claim['expected']:<11} got {r['label']}{flag}"
            )
            print(f"       claim:  {claim['text']}")
            print(f"       reason: {r.get('reason')}")
    print(f"\nCalibration: {agree}/{total} labels as expected.")
    return agree, total


def _load_jsonl(path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_judge(run: int, ids: list[str] | None, dry_run: bool) -> bool:
    """Judge the run's answers not judged yet; False if Gemini stopped it early."""
    answers = {a["id"]: a for a in _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")}
    claims_by_id = defaultdict(list)
    for c in _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl"):
        claims_by_id[c["id"]].append(c)
    out_path = RESULTS_DIR / f"judgements_run{run}.jsonl"
    done = {r["id"] for r in _load_jsonl(out_path)} if out_path.exists() else set()

    selected = [i for i in answers if i in claims_by_id and (not ids or i in ids)]
    for answer_id in selected:
        if answer_id in done:
            print(f"{answer_id:<28} already judged, skipped")
    todo = [{**answers[i], "claims": claims_by_id[i]} for i in selected if i not in done]
    batches = [todo[k : k + ANSWERS_PER_CALL] for k in range(0, len(todo), ANSWERS_PER_CALL)]
    if dry_run:
        first = [
            {**a, "claims": [c for c in a["claims"] if not c["auto_label"]]} for a in batches[0]
        ]
        print(JUDGE_INSTRUCTIONS, "\n\n" + "=" * 80 + "\n")
        print(build_prompt(first))
        return True

    client = _client()
    for batch in batches:
        batch_ids = [a["id"] for a in batch]
        try:
            judged, tokens = judge_batch(client, batch)
        except (genai_errors.ClientError, genai_errors.ServerError) as e:
            if e.code in (429, 503):
                print(
                    f"\nGemini unavailable at {batch_ids[0]} (daily limit, or still overloaded "
                    f"after the retries); stopping. Re-run to resume.\n{e}"
                )
                return False
            raise
        with out_path.open("a", encoding="utf-8") as f:
            for answer_id in batch_ids:
                abstains, results = judged[answer_id]
                record = {
                    "id": answer_id,
                    "run": run,
                    "judge_model": GEMINI_MODEL,
                    "batch": batch_ids,
                    "abstains": abstains,
                    "claims": results,
                    "batch_tokens": tokens,
                    "judged_at": datetime.now(UTC).isoformat(timespec="seconds"),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        # Counts only, no labels: keeps the terminal from showing verdicts by accident.
        n_claims = sum(len(judged[i][1]) for i in batch_ids)
        print(f"batch of {len(batch_ids)} answers: {n_claims} claims judged, {tokens} tokens")
    return True


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--calibration", action="store_true", help="Judge the calibration set")
    parser.add_argument("--run", type=int, help="Judge this run's claims")
    parser.add_argument("--ids", help="Comma-separated answer ids (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Print one prompt, call nothing")
    parser.add_argument(
        "--force", action="store_true", help="Judge a hand-labelled run before its labels exist"
    )
    args = parser.parse_args()

    if args.calibration:
        agree, total = run_calibration()
        sys.exit(0 if agree == total else 1)  # lets a script stop before a costly run
    elif args.run is None:
        parser.error("pass --calibration or --run N")
    else:
        blind = args.run in HAND_LABELLED_RUNS and not labels_complete(args.run)
        if blind and not args.dry_run and not args.force:
            parser.error(
                f"run {args.run} is hand-labelled blind: judge it after every claim in "
                f"{reference_labels_path(args.run).name} is labelled (check: python -m "
                f"app.evaluation.hand_labels --run {args.run} --check; --force to override)"
            )
        finished = run_judge(args.run, args.ids.split(",") if args.ids else None, args.dry_run)
        # Non-zero when stopped early, so "judge && agreement" can't go on with partial results.
        sys.exit(0 if finished else 1)
