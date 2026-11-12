"""Diagnosis, not a measurement: what the answers the gate rejected actually said.

    python -m app.evaluation.run_gate_diagnosis --out 2026-11-12_diagnosis --repeat 3 \
        transfer_credits_en academic_probation_fr

The retry rule failed on 2026-11-12 (CLAUDE.md, "A2.6b rule") with 2/12 replaced, but its records
hold only what the browser received, so the rejected texts were never seen. This runs the compiled
graph directly, as the faithfulness generator does, and keeps every attempt: the first answer and
the gate's verdict on it, the retry and its verdict, the markers the tools returned and the ones
each attempt cited. It decides nothing and counts toward no rule: it shows whether an uncited
answer is a refusal or a real answer missing its markers, and what an invented number looks like.

Calls the Groq API, and shares its daily quota with the live demo. Stops at --cap (checked before
each run, so it can go over by one answer) and at Groq's daily limit; waits out the per-minute one.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from groq import RateLimitError

from app.agent.citations import cited_markers, normalize_brackets, reset_citation_counter
from app.agent.gate import final_answer
from app.agent.graph import build_graph
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.config import MAX_AGENT_STEPS
from app.evaluation.generate_faithfulness_answers import (
    EVAL_SET_PATH,
    PER_MINUTE_RETRIES,
    PER_MINUTE_WAIT_SECONDS,
    is_per_minute_limit,
)

RESULTS_DIR = Path(__file__).resolve().parents[3] / "eval" / "results" / "gate"
DEFAULT_CAP = 30_000


def _cited(text: str | None, known: set[int]) -> dict:
    """The markers a text cites, and those no tool returned."""
    if text is None:
        return {"cited": None, "invented": None}
    cited = cited_markers(normalize_brackets(text))
    return {"cited": sorted(cited), "invented": sorted(cited - known)}


def attempts(messages) -> dict:
    """Every attempt in one run of the graph (one question, no history).

    The graph's messages come in this order: the agent's turns and the tools' results, the
    gate's template if it rejected the answer, the retry if there was one, and the second
    gate's template if it rejected the retry too.
    """
    known = {c["marker"] for m in messages if m.type == "tool" for c in m.artifact or []}
    queries = [tc["args"] for m in messages if m.type == "ai" for tc in m.tool_calls]

    first_parts: list[str] = []
    first_verdict = retry_text = retry_verdict = None
    seen_retry = False
    for m in messages:
        if m.type != "ai":
            continue
        meta = m.response_metadata
        if meta.get("retry"):
            seen_retry, retry_text = True, m.content
        elif meta.get("gate"):
            if seen_retry:
                retry_verdict = meta["gate"]
            else:
                first_verdict = meta["gate"]
        elif not seen_retry and first_verdict is None and isinstance(m.content, str):
            first_parts.append(m.content)
    first_text = "".join(first_parts)

    tokens = sum(
        m.usage_metadata["input_tokens"] + m.usage_metadata["output_tokens"]
        for m in messages
        if m.type == "ai" and m.usage_metadata
    )
    return {
        "queries": queries,
        "known_markers": sorted(known),
        "first_answer": first_text,
        "first_verdict": first_verdict,
        **{f"first_{k}": v for k, v in _cited(first_text, known).items()},
        "retried": seen_retry,
        "retry_answer": retry_text,
        "retry_verdict": retry_verdict,
        **{f"retry_{k}": v for k, v in _cited(retry_text, known).items()},
        "final_answer": final_answer(messages),
        "tokens": tokens,
    }


def run(graph, questions: list[dict], repeat: int, out_path: Path, cap: int) -> list[dict]:
    """Each question `repeat` times, appended to out_path as it goes."""
    records: list[dict] = []
    used = 0
    for q in questions:
        language = detect_language(q["question"])
        for n in range(1, repeat + 1):
            if used >= cap:
                print(f"\nStopped at the cap: {used:,} tokens.")
                return records
            for attempt in range(1, PER_MINUTE_RETRIES + 2):
                reset_citation_counter()
                try:
                    result = graph.invoke(
                        {"messages": build_input_messages(q["question"], None)},
                        config={
                            "recursion_limit": MAX_AGENT_STEPS,
                            "configurable": {"language": language},
                        },
                    )
                    break
                except RateLimitError as e:
                    if is_per_minute_limit(e) and attempt <= PER_MINUTE_RETRIES:
                        print(f"{q['id']:<24} per-minute limit, waiting {PER_MINUTE_WAIT_SECONDS}s")
                        time.sleep(PER_MINUTE_WAIT_SECONDS)
                        continue
                    print(f"\nGroq's limit reached at {q['id']} #{n}; stopping.")
                    return records
            record = {"id": q["id"], "n": n, "question": q["question"], "language": language}
            record |= attempts(result["messages"])
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            records.append(record)
            used += record["tokens"]
            retry = f" -> retry {record['retry_verdict'] or 'passed'}" if record["retried"] else ""
            print(
                f"{q['id']:<24} #{n} first {record['first_verdict'] or 'passed'}{retry}, "
                f"{record['tokens']:>6} tokens"
            )
    return records


def main_cli() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="+", help="Question ids from the faithfulness set")
    parser.add_argument("--out", required=True, help="Output file name, without .jsonl")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP)
    args = parser.parse_args()
    by_id = {q["id"]: q for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))}
    questions = [by_id[i] for i in args.ids]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records = run(
        build_graph(), questions, args.repeat, RESULTS_DIR / f"{args.out}.jsonl", args.cap
    )
    print(f"\n{len(records)} runs, {sum(r['tokens'] for r in records):,} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
