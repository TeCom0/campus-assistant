"""Stage 3 of the faithfulness evaluation: an LLM judge labels each claim from
split_claims.py as supported / unsupported / no_claim against the passages it
is checked against.

The judge (JUDGE_PROVIDER) is Mistral Large, Qwen on Groq, or Gemini: in each
case a different model family from gpt-oss, which wrote the answers (a model
judging its own family's output tends to be lenient). Answers are judged
ANSWERS_PER_CALL at a time, each in its own block: one per call on Mistral and
Groq, four on Gemini (20 requests/day). The output must fit a JSON schema and
is validated, not parsed out of free text. Strict: partly supported is
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

import requests
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from groq import Groq
from groq import RateLimitError as GroqRateLimitError
from pydantic import BaseModel

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, MISTRAL_API_KEY
from app.evaluation.generate_faithfulness_answers import (
    EVAL_DIR,
    PER_MINUTE_RETRIES,
    PER_MINUTE_WAIT_SECONDS,
    RESULTS_DIR,
    is_per_minute_limit,
)
from app.evaluation.hand_labels import labels_complete, reference_labels_path
from app.evaluation.throttle import Throttle

CALIBRATION_PATH = EVAL_DIR / "judge_calibration.json"
HAND_LABELLED_RUNS = {1}

# Which judge: "mistral", "groq" (Qwen, Alibaba's family -- still not the
# generator's) or "gemini". Gemini's free tier answered 503 "high demand" to ~28
# of ~30 calls (2026-10-11..13); Qwen agreed with the hand labels only 25/40.
# Mistral since 2026-10-15 (pay-as-you-go: the free plan had no Large model).
JUDGE_PROVIDER = "mistral"
# An exact model id, never a "-latest" alias: an alias can move to another model
# between two runs, and the results must say which model judged them.
MISTRAL_MODEL = "mistral-large-2512"
JUDGE_MODEL = {
    "mistral": MISTRAL_MODEL,
    "groq": "qwen/qwen3.8-27b",
    "gemini": GEMINI_MODEL,
}[JUDGE_PROVIDER]
# Gemini allows 20 requests/day, so 4 answers per call. Groq allows 1,000/day
# but 8,000 tokens/minute, and the largest answer alone is ~5k: one per call.
# Mistral: one per call too, so a failed call costs one answer, not four.
ANSWERS_PER_CALL = {"mistral": 1, "groq": 1, "gemini": 4}[JUDGE_PROVIDER]
# Groq also caps Qwen's *output* at 1,000 tokens/minute, and a verdict takes
# ~100 tokens per claim: a long answer's claims go in groups of 6, each call
# with the whole answer and its passages. None = all of an answer's claims at once.
CLAIMS_PER_CALL = {"mistral": None, "groq": 6, "gemini": None}[JUDGE_PROVIDER]
GROQ_MAX_OUTPUT_TOKENS = 1000

# Mistral limits for mistral-large-2512 on this account, the stricter of the
# console's Limits page (1 request/s, 250k tokens/min) and the API's response
# headers (15 requests/min, 400k tokens/min), both seen 2026-10-15.
MISTRAL_REQUESTS_PER_SECOND = 15 / 60
MISTRAL_TOKENS_PER_MINUTE = 250_000
# ~100 tokens per claim verdict; the longest answer has ~15 claims.
MISTRAL_MAX_OUTPUT_TOKENS = 4000
# No tokenizer installed: estimate prompt tokens at 4 characters each (only
# used to decide how long to wait; the reply's real count replaces it).
CHARS_PER_TOKEN = 4
# Retries on 429 (rate limited) and 5xx (overloaded), waiting 15, 30, 60 s;
# then the run stops and a re-run resumes.
MISTRAL_RETRIES = 3
MISTRAL_RETRY_WAIT_SECONDS = 15
MISTRAL_TIMEOUT_SECONDS = 180
# USD per million tokens, from mistral.ai/pricing ("Mistral Large costs $0.5 /M
# tokens in and $1.5 /M tokens out"), checked 2026-10-15. Only for the cost
# estimate printed after a run; the console's billing page is the real number.
MISTRAL_USD_PER_M_INPUT = 0.50
MISTRAL_USD_PER_M_OUTPUT = 1.50

# Gemini only. Failed attempts count toward the free tier's 20 requests/day
# (2026-10-12: 2 successful calls + 18 failed 503s, then a daily 429), so retry
# rarely and wait long: 120 s, then 240 s. A 503 "high demand" spell lasts
# minutes; when it's still on after that, the batch stops and a re-run resumes.
RATE_LIMIT_WAIT_SECONDS = 120
RATE_LIMIT_RETRIES = 2

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


class SingleAnswerVerdict(BaseModel):
    """What Groq returns: it judges one answer per call, so no answer list. With
    the answer list, Qwen deterministically stopped after it on some answers
    (plagiarism_en, 2026-10-13) and never wrote the verdicts."""

    verdicts: list[ClaimVerdict]
    abstains: bool


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


def call_judge(client, prompt: str, answer_ids: list[str]) -> tuple[BatchVerdict, int]:
    """One judge call, to the provider JUDGE_PROVIDER names; answer_ids are the
    answers in the prompt."""
    if JUDGE_PROVIDER == "mistral":
        (answer_id,) = answer_ids  # one answer per call on Mistral
        return _call_mistral(client, prompt, answer_id)
    if JUDGE_PROVIDER == "groq":
        (answer_id,) = answer_ids  # one answer per call on Groq
        return _call_groq(client, prompt, answer_id)
    return _call_gemini(client, prompt)


def strict_json_schema(schema: dict) -> dict:
    """The schema with "additionalProperties": false on every object, which
    Groq's strict mode requires. Strict mode makes the model's output follow the
    schema exactly (2026-10-13 without it: Qwen once left out "verdicts")."""
    if isinstance(schema, dict):
        fixed = {key: strict_json_schema(value) for key, value in schema.items()}
        if fixed.get("type") == "object":
            fixed["additionalProperties"] = False
        return fixed
    if isinstance(schema, list):
        return [strict_json_schema(value) for value in schema]
    return schema


def _call_groq(client: Groq, prompt: str, answer_id: str) -> tuple[BatchVerdict, int]:
    """One Groq call about one answer. The reply must follow SingleAnswerVerdict's
    JSON schema (strict mode) and is validated here too, then returned as a
    BatchVerdict like Gemini's. Waits out a per-minute limit; raises on the
    daily one."""
    for attempt in range(1, PER_MINUTE_RETRIES + 2):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "SingleAnswerVerdict",
                        "schema": strict_json_schema(SingleAnswerVerdict.model_json_schema()),
                        "strict": True,
                    },
                },
                max_completion_tokens=GROQ_MAX_OUTPUT_TOKENS,
                temperature=0,
                reasoning_format="hidden",  # Qwen thinks first; keep only the JSON
            )
            break
        except GroqRateLimitError as e:
            if is_per_minute_limit(e) and attempt <= PER_MINUTE_RETRIES:
                print(f"  Groq per-minute limit, waiting {PER_MINUTE_WAIT_SECONDS}s")
                time.sleep(PER_MINUTE_WAIT_SECONDS)
                continue
            raise
    single = SingleAnswerVerdict.model_validate_json(response.choices[0].message.content)
    verdict = BatchVerdict(
        answers=[AnswerAbstains(answer_id=answer_id, abstains=single.abstains)],
        verdicts=single.verdicts,
    )
    return verdict, response.usage.total_tokens if response.usage else 0


def _call_gemini(client: genai.Client, prompt: str) -> tuple[BatchVerdict, int]:
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
                model=JUDGE_MODEL, contents=prompt, config=config
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


class MistralUnavailable(Exception):
    """Still rate limited or overloaded after the retries: the run stops here."""


class MistralClient:
    """Mistral's chat endpoint over plain HTTP (requests -- one endpoint doesn't
    need an SDK), plus the throttle and the token counts for the cost estimate."""

    URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(self, api_key: str, throttle: Throttle, sleep=time.sleep):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.throttle = throttle
        self.sleep = sleep
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.served_models: set[str] = set()  # as the API reports them

    def post(self, payload: dict) -> dict:
        """One request, throttled; retries 429/5xx/timeouts, then raises
        MistralUnavailable. Any other error (bad request, wrong key) raises at once."""
        estimate = (
            sum(len(m["content"]) for m in payload["messages"]) // CHARS_PER_TOKEN
            + payload["max_tokens"]
        )
        for attempt in range(1, MISTRAL_RETRIES + 2):
            call = self.throttle.wait_for_slot(estimate)
            try:
                response = self.session.post(
                    self.URL, json=payload, timeout=MISTRAL_TIMEOUT_SECONDS
                )
                problem = (
                    f"HTTP {response.status_code}"
                    if response.status_code == 429 or response.status_code >= 500
                    else None
                )
            except (requests.Timeout, requests.ConnectionError) as e:
                problem = type(e).__name__
            if problem is None:
                break
            if attempt > MISTRAL_RETRIES:
                raise MistralUnavailable(f"{problem} after {MISTRAL_RETRIES} retries")
            wait = MISTRAL_RETRY_WAIT_SECONDS * 2 ** (attempt - 1)
            print(f"  Mistral {problem}, waiting {wait}s")
            self.sleep(wait)
        if response.status_code != 200:  # Mistral's message says what was wrong
            raise RuntimeError(f"Mistral HTTP {response.status_code}: {response.text[:500]}")
        body = response.json()
        usage = body["usage"]
        self.throttle.record_actual(call, usage["total_tokens"])
        self.calls += 1
        self.input_tokens += usage["prompt_tokens"]
        self.output_tokens += usage["completion_tokens"]
        self.served_models.add(body["model"])
        print(
            f"  mistral call: {usage['prompt_tokens']} in + {usage['completion_tokens']} out tokens"
        )
        return body

    def cost_summary(self) -> str:
        cost = (
            self.input_tokens * MISTRAL_USD_PER_M_INPUT
            + self.output_tokens * MISTRAL_USD_PER_M_OUTPUT
        ) / 1_000_000
        return (
            f"Mistral usage: {self.calls} calls, {self.input_tokens} in + "
            f"{self.output_tokens} out tokens, served by {sorted(self.served_models)}; "
            f"estimated cost ${cost:.4f} (at ${MISTRAL_USD_PER_M_INPUT}/M in, "
            f"${MISTRAL_USD_PER_M_OUTPUT}/M out)"
        )


def _call_mistral(client: MistralClient, prompt: str, answer_id: str) -> tuple[BatchVerdict, int]:
    """One Mistral call about one answer, in Groq's shape: the reply must follow
    SingleAnswerVerdict's JSON schema (strict mode) and is validated here too."""
    body = client.post(
        {
            "model": JUDGE_MODEL,
            "messages": [
                {"role": "system", "content": JUDGE_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "SingleAnswerVerdict",
                    "schema": strict_json_schema(SingleAnswerVerdict.model_json_schema()),
                    "strict": True,
                },
            },
            "max_tokens": MISTRAL_MAX_OUTPUT_TOKENS,
            "temperature": 0,
        }
    )
    choice = body["choices"][0]
    if choice["finish_reason"] == "length":  # cut off: the JSON is incomplete
        raise ValueError(f"judge reply hit max_tokens ({MISTRAL_MAX_OUTPUT_TOKENS})")
    single = SingleAnswerVerdict.model_validate_json(choice["message"]["content"])
    verdict = BatchVerdict(
        answers=[AnswerAbstains(answer_id=answer_id, abstains=single.abstains)],
        verdicts=single.verdicts,
    )
    return verdict, body["usage"]["total_tokens"]


def claim_groups(items: list[dict]) -> list[list[dict]]:
    """What each call sends: all the items at once, or -- with CLAIMS_PER_CALL --
    each item's claims in groups of that size, every group with the item's full
    question, answer and passages."""
    if CLAIMS_PER_CALL is None:
        return [items]
    return [
        [{**item, "claims": item["claims"][k : k + CLAIMS_PER_CALL]}]
        for item in items
        for k in range(0, len(item["claims"]), CLAIMS_PER_CALL)
    ]


def judge_batch(client, answers: list[dict]) -> tuple[dict[str, tuple], int]:
    """Judge several answers (one call, or one per claim group).

    Each answer: {"id", "question", "answer", "passages", "claims"} (all its
    claims, auto-labelled ones included). Returns {answer id: (abstains,
    per-claim results)} and the calls' tokens. abstains is None if the judge
    skipped that answer; an answer with nothing to ask isn't sent.
    """
    items = [{**a, "claims": [c for c in a["claims"] if not c["auto_label"]]} for a in answers]
    items = [i for i in items if i["claims"]]
    claim_verdicts, abstains, tokens = [], {}, 0
    for group in claim_groups(items) if items else []:
        verdict, group_tokens = call_judge(client, build_prompt(group), [i["id"] for i in group])
        claim_verdicts += verdict.verdicts
        for a in verdict.answers:
            abstains.setdefault(a.answer_id, a.abstains)  # every group sees the whole answer
        tokens += group_tokens
    judged = {}
    for a in answers:
        results = merge_verdicts(a["claims"], a["passages"], claim_verdicts)
        judged[a["id"]] = (abstains.get(a["id"]), results)
    return judged, tokens


def _client():
    if JUDGE_PROVIDER == "mistral":
        if not MISTRAL_API_KEY:
            raise SystemExit("MISTRAL_API_KEY is not set (check .env)")
        throttle = Throttle(MISTRAL_REQUESTS_PER_SECOND, MISTRAL_TOKENS_PER_MINUTE)
        return MistralClient(MISTRAL_API_KEY, throttle)
    if JUDGE_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise SystemExit("GROQ_API_KEY is not set (check .env)")
        return Groq(api_key=GROQ_API_KEY)
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set (check .env)")
    return genai.Client(api_key=GEMINI_API_KEY)


def run_calibration() -> tuple[int, int]:
    """Judge hand-made claims with known labels; prints judge vs. expected."""
    cases = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    answers = [{**case, "answer": " ".join(c["text"] for c in case["claims"])} for case in cases]
    client, judged, tokens = _client(), {}, 0
    for k in range(0, len(answers), ANSWERS_PER_CALL):  # batched as in a run
        batch_judged, batch_tokens = judge_batch(client, answers[k : k + ANSWERS_PER_CALL])
        judged, tokens = {**judged, **batch_judged}, tokens + batch_tokens
    print(f"Judge: {JUDGE_PROVIDER} {JUDGE_MODEL}; {len(cases)} cases, {tokens} tokens")
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
    if isinstance(client, MistralClient):
        print(client.cost_summary())
    return agree, total


def _load_jsonl(path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_judge(run: int, ids: list[str] | None, dry_run: bool) -> bool:
    """Judge the run's answers not judged yet; False if the provider stopped it early."""
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
        except (
            genai_errors.ClientError,
            genai_errors.ServerError,
            GroqRateLimitError,
            MistralUnavailable,
        ) as e:
            if isinstance(e, (GroqRateLimitError, MistralUnavailable)) or e.code in (429, 503):
                if isinstance(client, MistralClient):
                    print(client.cost_summary())
                print(
                    f"\n{JUDGE_PROVIDER} unavailable at {batch_ids[0]} (daily limit, or still "
                    f"limited/overloaded after the retries); stopping. Re-run to resume.\n{e}"
                )
                return False
            raise
        with out_path.open("a", encoding="utf-8") as f:
            for answer_id in batch_ids:
                abstains, results = judged[answer_id]
                record = {
                    "id": answer_id,
                    "run": run,
                    "judge_provider": JUDGE_PROVIDER,
                    "judge_model": JUDGE_MODEL,
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
    if isinstance(client, MistralClient):
        print(client.cost_summary())
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
