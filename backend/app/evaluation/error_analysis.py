"""Error analysis: why did answers fail? One cause per failure, confirmed by hand.

Collects, for a run, every failure worth a cause:
  claim          an unsupported cited claim in a `main` answer (the headline's failures)
  false_refusal  an answer that declined a question it should have answered
  crash          an answer that ended in an error (no claims at all)

and writes error_analysis_runN.md: each failure with its question, the claim,
the full text of the passages it cites, and the judge's label, quote check and
reason. The causes live in error_causes_runN.json: a proposed cause per
failure (written by hand from reading the md) and a "confirmed" cause set by
the human. `--counts` tallies the confirmed causes, per failure and per answer,
so a before/after comparison doesn't rest only on the judge.

Causes:
  grad_undergrad      graduate rules given as general / undergraduate (or reverse)
  heading_split       a chunk boundary cut a rule from its heading or its numbers
  french_retrieval    a French question's searches missed the passage that answers it
  citation_placement  the fact is in a retrieved passage, but not the one cited
  crash               the forced-final-answer error (no answer)
  embellishment       the model added a gloss, hedge or detail no passage gives
  uncitable_tool      a tool result the model couldn't cite (query_courses "no description")
  judge_artifact      the claim IS supported; it failed only in the judge or quote check

Usage (from backend/):
    python -m app.evaluation.error_analysis --run 1            # write the md
    python -m app.evaluation.error_analysis --run 1 --counts   # tally confirmed causes
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from app.evaluation.adjudication import checked_against
from app.evaluation.generate_faithfulness_answers import EVAL_SET_PATH, RESULTS_DIR
from app.evaluation.report import CITED_KINDS

CAUSES = (
    "grad_undergrad",
    "heading_split",
    "french_retrieval",
    "citation_placement",
    "crash",
    "embellishment",
    "uncitable_tool",
    "judge_artifact",
)


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def causes_path(run: int) -> Path:
    return RESULTS_DIR / f"error_causes_run{run}.json"


def collect_failures(
    answers: list[dict], claims: list[dict], judgements: list[dict], questions: dict
) -> list[dict]:
    """Every failure of the run, in answer order: unsupported cited claims of
    `main` answers, false refusals (any set), crashes (any set)."""
    results = {c["claim_id"]: c for j in judgements for c in j["claims"]}
    abstains = {j["id"]: j["abstains"] for j in judgements}
    failures = []
    for a in answers:
        q = questions[a["id"]]
        if a["error"]:
            failures.append({"id": a["id"], "type": "crash", "answer": a["id"]})
            continue
        if q["expected_behavior"] == "answer" and abstains.get(a["id"]) is True:
            failures.append({"id": a["id"], "type": "false_refusal", "answer": a["id"]})
        if q["set"] != "main":
            continue
        for c in claims:
            if c["id"] != a["id"] or c.get("exclude") or c["kind"] not in CITED_KINDS:
                continue
            label = c["auto_label"] or results.get(c["claim_id"], {}).get("label")
            if label == "unsupported":
                failures.append({"id": c["claim_id"], "type": "claim", "answer": a["id"]})
    return failures


def count_causes(failures: list[dict], causes: dict) -> dict:
    """Confirmed causes per failure, and the answers still failing once
    judge artifacts are set aside (by hand, not by the judge)."""
    confirmed = {f["id"]: causes[f["id"]]["confirmed"] for f in failures}
    by_cause = Counter(confirmed.values())
    real = {
        f["answer"]
        for f in failures
        if f["type"] == "claim" and confirmed[f["id"]] != "judge_artifact"
    }
    judged = {f["answer"] for f in failures if f["type"] == "claim"}
    return {
        "by_cause": dict(sorted(by_cause.items())),
        "failing_answers_judge": len(judged),
        "failing_answers_by_hand": len(real),
        "judge_artifact_only": sorted(judged - real),
    }


def unconfirmed(failures: list[dict], causes: dict) -> list[str]:
    return [f["id"] for f in failures if causes.get(f["id"], {}).get("confirmed") not in CAUSES]


def render_markdown(
    run: int, failures: list[dict], answers: dict, claims: dict, results: dict, causes: dict
) -> str:
    lines = [
        f"# Error analysis, run {run}: {len(failures)} failures",
        "",
        (
            f'Confirm each cause in {causes_path(run).name} ("confirmed": one of '
            f"{', '.join(CAUSES)})."
        ),
    ]
    for n, f in enumerate(failures, 1):
        a = answers[f["answer"]]
        cause = causes.get(f["id"], {})
        lines += [
            "", "---", "",
            f"## {n}. {f['id']} ({f['type']})",
            "",
            f"**Proposed cause:** {cause.get('proposed', '?')} -- {cause.get('why', '')}",
            "",
            f"**Question:** {a['question']}",
            "",
            f"**Searches:** {[(t.get('tool'), t.get('args')) for t in a.get('tool_calls', [])]}",
        ]  # fmt: skip
        if f["type"] == "crash":
            lines += ["", f"**Error:** {a['error'][:300]}"]
            continue
        if f["type"] == "false_refusal":
            lines += ["", "**Answer:**", "", "```text", a["answer"], "```"]
            passages = a["passages"]
        else:
            c, r = claims[f["id"]], results.get(f["id"], {})
            scope = ", ".join(f"[{m}]" for m in c["markers"])
            lines += [
                "",
                f"**Claim** ({c['kind']}, cites {scope}):",
                "",
                f"> {c['text']}",
                "",
                f"**Judge:** {r.get('judge_label')} -> {r.get('label') or c['auto_label']}"
                + (f" [{r['flag']}]" if r.get("flag") else ""),
                "",
                f"**Judge's quote:** {r.get('evidence_quote') or '(none)'}",
                "",
                f"**Judge's reason:** {r.get('reason', '')}",
            ]
            passages = checked_against(c, a["passages"])
        lines += ["", "**Passages:**"]
        for p in passages:
            lines += ["", f"[{p['marker']}] source: {p['source']}, pages: {p['pages']}", ""]
            for text in p["texts"]:
                lines += ["```text", text, "```", ""]
    return "\n".join(lines) + "\n"


def load(run: int) -> tuple:
    answers = _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")
    claims = _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl")
    judgements = _load_jsonl(RESULTS_DIR / f"judgements_run{run}.jsonl")
    questions = {q["id"]: q for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))}
    failures = collect_failures(answers, claims, judgements, questions)
    path = causes_path(run)
    causes = json.loads(path.read_text(encoding="utf-8"))["causes"] if path.exists() else {}
    return answers, claims, judgements, failures, causes


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--counts", action="store_true", help="Tally the confirmed causes")
    args = parser.parse_args()
    answers, claims, judgements, failures, causes = load(args.run)
    if args.counts:
        missing = unconfirmed(failures, causes)
        if missing:
            raise SystemExit(f"{len(missing)} failures have no confirmed cause yet: {missing}")
        print(json.dumps(count_causes(failures, causes), indent=2))
    else:
        results = {c["claim_id"]: c for j in judgements for c in j["claims"]}
        md = render_markdown(
            args.run,
            failures,
            {a["id"]: a for a in answers},
            {c["claim_id"]: c for c in claims},
            results,
            causes,
        )
        out = RESULTS_DIR / f"error_analysis_run{args.run}.md"
        out.write_text(md, encoding="utf-8")
        print(f"{len(failures)} failures -> {out.name}")
