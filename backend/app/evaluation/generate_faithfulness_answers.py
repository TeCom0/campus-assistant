"""Stage 1 of the faithfulness evaluation: generate answers to the questions in
eval/faithfulness_eval_set.json and save them with the passage text behind
each citation marker, for the judge (stage 2) and the hand labels.

Runs the real agent graph with the same pieces /chat uses (input messages,
language detection passed through the run config, the step limit, bracket
normalization), so what's measured is what students would see. /chat streams
the answer; this waits for the whole run -- the answer text is the same.

Each answer is appended to a JSONL file (one JSON object per line) as soon as
it's done, and a re-run skips ids already in the file: Groq's free tier allows
200k tokens per day, so a run may have to continue the next day. A rate-limit
error stops the run instead of being recorded as a failed answer.

Usage (from backend/):
    python -m app.evaluation.generate_faithfulness_answers --run 1
    python -m app.evaluation.generate_faithfulness_answers --run 1 --ids transfer_credits_en,mth1305_fr
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from groq import RateLimitError

from app.agent.citations import cited_markers, normalize_brackets, reset_citation_counter
from app.agent.graph import build_graph
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.config import GEMINI_MODEL, GROQ_MODEL, LLM_PROVIDER, MAX_AGENT_STEPS

EVAL_DIR = Path(__file__).resolve().parents[3] / "eval"
EVAL_SET_PATH = EVAL_DIR / "faithfulness_eval_set.json"
RESULTS_DIR = EVAL_DIR / "results" / "faithfulness"
GROQ_TOKENS_PER_DAY = 200_000  # free tier, openai/gpt-oss-20b (console.groq.com, 2026-10-11)
# The free tier also allows only 8,000 tokens per MINUTE, and one question can
# use more than that (add_drop_fr: 10,982 over 4 calls). That limit clears
# within a minute, so it means wait and retry the question, not stop for the day.
PER_MINUTE_WAIT_SECONDS = 60
PER_MINUTE_RETRIES = 3


def is_per_minute_limit(error: Exception) -> bool:
    """Groq names the limit in the message: "tokens per minute (TPM)", "per day (TPD)"..."""
    return "per minute" in str(error)


def answer_text(messages) -> str:
    """The answer as /chat streams it: the text of every agent message, in order."""
    parts = [m.content for m in messages if m.type == "ai" and isinstance(m.content, str)]
    return normalize_brackets("".join(parts))


def collect_passages(messages) -> list[dict]:
    """Every passage the tools returned, one entry per marker, sorted by marker.

    A marker can come back more than once (query_courses looked up again, e.g.
    with the prerequisite chain); each distinct text is kept, in the order
    returned, and the judge checks a claim against all of them combined.
    """
    by_marker: dict[int, dict] = {}
    for m in messages:
        if m.type != "tool":
            continue
        for citation in getattr(m, "artifact", None) or []:
            entry = by_marker.setdefault(
                citation["marker"],
                {
                    "marker": citation["marker"],
                    "source": citation["source"],
                    "pages": citation["pages"],
                    "texts": [],
                },
            )
            if citation["text"] not in entry["texts"]:
                entry["texts"].append(citation["text"])
    return [by_marker[marker] for marker in sorted(by_marker)]


def tool_calls(messages) -> list[dict]:
    return [
        {"name": tc["name"], "args": tc["args"]}
        for m in messages
        if m.type == "ai"
        for tc in m.tool_calls
    ]


def token_usage(messages) -> dict:
    """Tokens the provider reported for every LLM call in the run (input + output)."""
    usage = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for m in messages:
        if m.type == "ai" and m.usage_metadata:
            usage["llm_calls"] += 1
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                usage[key] += m.usage_metadata[key]
    return usage


def load_done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f if line.strip()}


def generate(questions: list[dict], out_path: Path, run: int) -> list[dict]:
    """Answer each question not yet in out_path; return the new records."""
    graph = build_graph()
    model = GROQ_MODEL if LLM_PROVIDER == "groq" else GEMINI_MODEL
    done = load_done_ids(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = []

    for q in questions:
        if q["id"] in done:
            print(f"{q['id']:<28} already in {out_path.name}, skipped")
            continue

        language = detect_language(q["question"])
        for attempt in range(1, PER_MINUTE_RETRIES + 2):
            reset_citation_counter()
            started = time.perf_counter()
            try:
                result = graph.invoke(
                    {"messages": build_input_messages(q["question"], None)},
                    config={
                        "recursion_limit": MAX_AGENT_STEPS,
                        "configurable": {"language": language},
                    },
                )
                messages, error = result["messages"], None
                break
            except RateLimitError as e:
                if is_per_minute_limit(e) and attempt <= PER_MINUTE_RETRIES:
                    print(f"{q['id']:<28} per-minute limit, waiting {PER_MINUTE_WAIT_SECONDS}s")
                    time.sleep(PER_MINUTE_WAIT_SECONDS)
                    continue
                # Daily limit (or still blocked after the retries): stop, so the
                # run can resume later instead of recording answers that never
                # got generated.
                print(f"\nGroq rate limit reached at {q['id']}; stopping. Re-run to resume.\n{e}")
                return records
            except Exception as e:  # noqa: BLE001 -- /chat shows any failure as an
                # interrupted answer; record it as one rather than dropping the question.
                messages, error = [], repr(e)
                break

        answer = answer_text(messages)
        record = {
            "id": q["id"],
            "run": run,
            "question": q["question"],
            "language": q["language"],
            "detected_language": language,
            "provider": LLM_PROVIDER,
            "model": model,
            "answer": answer,
            "cited_markers": sorted(cited_markers(answer)),
            "passages": collect_passages(messages),
            "tool_calls": tool_calls(messages),
            "usage": token_usage(messages),
            "seconds": round(time.perf_counter() - started, 1),
            "error": error,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        records.append(record)

        u = record["usage"]
        status = f"ERROR {error}" if error else f"{len(record['cited_markers'])} markers cited"
        print(
            f"{q['id']:<28} {u['llm_calls']} calls, {u['total_tokens']:>6} tokens, "
            f"{record['seconds']:>5}s, {status}"
        )
    return records


def print_budget(records: list[dict], n_questions: int) -> None:
    totals = [r["usage"]["total_tokens"] for r in records if not r["error"]]
    if not totals:
        return
    average = sum(totals) / len(totals)
    per_run = average * n_questions
    print(
        f"\n{len(totals)} answers: {sum(totals)} tokens, {average:.0f} per question on average "
        f"(min {min(totals)}, max {max(totals)})."
    )
    print(
        f"Estimate for one run of all {n_questions} questions: {per_run:,.0f} tokens = "
        f"{100 * per_run / GROQ_TOKENS_PER_DAY:.0f}% of the {GROQ_TOKENS_PER_DAY:,} daily limit."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1, help="Run number (1 or 2), one file each")
    parser.add_argument("--ids", help="Comma-separated question ids (default: all)")
    args = parser.parse_args()

    all_questions = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    selected = all_questions
    if args.ids:
        wanted = args.ids.split(",")
        unknown = set(wanted) - {q["id"] for q in all_questions}
        if unknown:
            parser.error(f"unknown ids: {sorted(unknown)}")
        selected = [q for q in all_questions if q["id"] in wanted]

    new_records = generate(selected, RESULTS_DIR / f"answers_run{args.run}.jsonl", args.run)
    print_budget(new_records, len(all_questions))
