"""Adjudicate the claims where the judge and the human reference labels disagree.

Writes two files for a run:
- adjudication_runN.md: one section per disagreement, for reading -- the
  question, the full answer, the claim, the full text of every passage it is
  checked against, the human label (and note), the judge's label, quote and
  reason, and whether the quote check passed.
- adjudications_runN.json: the decisions, filled in by hand ("decision": one of
  supported / unsupported / no_claim, plus an optional note). Never overwritten
  once it exists, so re-running can't lose decisions.

The original reference labels (labels_runN_sample.json) are only read: the
adjudicated labels live in their own file, so both can be reported.

Usage (from backend/):
    python -m app.evaluation.adjudication --run 1           # write both files
    python -m app.evaluation.adjudication --run 1 --check   # every decision filled in?
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.generate_faithfulness_answers import RESULTS_DIR
from app.evaluation.hand_labels import reference_labels_path

LABELS = ("supported", "unsupported", "no_claim")


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def adjudications_path(run: int) -> Path:
    return RESULTS_DIR / f"adjudications_run{run}.json"


def checked_against(claim: dict, passages: list[dict]) -> list[dict]:
    """The passages a claim is checked against, as the judge's quote check uses
    them: its markers, or every passage of the answer for an uncited claim."""
    if not claim["markers"]:
        return passages
    return [p for p in passages if p["marker"] in claim["markers"]]


def build_items(
    reference: dict, judge_results: dict[str, dict], claims: dict[str, dict], answers: dict
) -> list[dict]:
    """One item per disagreement (judge's final label != reference label)."""
    human = {cid: v["label"] for cid, v in reference["claims"].items()}
    judge = {cid: r["label"] for cid, r in judge_results.items() if r["label"]}
    items = []
    # Same definition as agreement.py: claims both labelled, with different labels.
    disagreements = [cid for cid in sorted(human) if cid in judge and human[cid] != judge[cid]]
    for cid in disagreements:
        claim, result = claims[cid], judge_results[cid]
        answer = answers[claim["id"]]
        items.append(
            {
                "claim_id": cid,
                "question": answer["question"],
                "answer": answer["answer"],
                "claim": claim["text"],
                "kind": claim["kind"],
                "markers": claim["markers"],
                "passages": checked_against(claim, answer["passages"]),
                "human_label": human[cid],
                "human_note": reference["claims"][cid].get("note", ""),
                "judge_label": result["judge_label"],
                "judge_final": result["label"],
                "flag": result["flag"],
                "evidence_quote": result.get("evidence_quote", ""),
                "reason": result.get("reason", ""),
            }
        )
    return items


def render_markdown(run: int, judge_model: str, items: list[dict]) -> str:
    lines = [
        f"# Adjudication, run {run}: {len(items)} disagreements",
        "",
        (
            f"Judge: {judge_model}. Decide each claim in {adjudications_path(run).name}"
            ' ("decision": supported / unsupported / no_claim, optional "note").'
        ),
        "Your original labels are not changed.",
    ]
    for n, item in enumerate(items, 1):
        scope = ", ".join(f"[{m}]" for m in item["markers"]) or "all passages"
        quote_check = {
            "quote_not_found": "FAILED -- quote not found in these passages",
            None: "passed" if item["judge_label"] == "supported" else "n/a (not supported)",
        }.get(item["flag"], item["flag"])
        note = f" -- note: {item['human_note']}" if item["human_note"] else ""
        quote = repr(item["evidence_quote"]) if item["evidence_quote"] else "(none)"
        judge = f"{item['judge_label']} -> final {item['judge_final']}"
        lines += [
            "",
            "---",
            "",
            f"## {n}. {item['claim_id']}",
            "",
            f"**Your label:** {item['human_label']}{note}",
            "",
            f"**Judge:** {judge} (quote check: {quote_check})",
            "",
            f"**Claim** ({item['kind']}, checked against {scope}):",
            "",
            f"> {item['claim']}",
            "",
            f"**Judge's quote:** {quote}",
            "",
            f"**Judge's reason:** {item['reason']}",
            "",
            f"**Question:** {item['question']}",
            "",
            "<details><summary>Full answer</summary>",
            "",
            "```text",
            item["answer"],
            "```",
            "",
            "</details>",
            "",
            "**Passages:**",
        ]  # fmt: skip
        for p in item["passages"]:
            lines += ["", f"[{p['marker']}] source: {p['source']}, pages: {p['pages']}", ""]
            for k, text in enumerate(p["texts"]):
                if k:
                    lines += ["(same marker, returned again with more text:)", ""]
                lines += ["```text", text, "```", ""]
    return "\n".join(lines) + "\n"


def decisions_template(run: int, judge_model: str, items: list[dict]) -> dict:
    return {
        "run": run,
        "judge_model": judge_model,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "claims": {
            item["claim_id"]: {
                "original": item["human_label"],
                "judge": item["judge_final"],
                "decision": None,
                "note": "",
            }
            for item in items
        },
    }


def check_decisions(decisions: dict) -> list[str]:
    """Problems with the decisions file: missing or invalid decisions."""
    return [
        f"{cid}: decision {entry['decision']!r} (expected one of {', '.join(LABELS)})"
        for cid, entry in decisions["claims"].items()
        if entry["decision"] not in LABELS
    ]


def write_files(run: int) -> None:
    reference = json.loads(reference_labels_path(run).read_text(encoding="utf-8"))
    judgements = _load_jsonl(RESULTS_DIR / f"judgements_run{run}.jsonl")
    judge_results = {c["claim_id"]: c for j in judgements for c in j["claims"]}
    claims = {c["claim_id"]: c for c in _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl")}
    answers = {a["id"]: a for a in _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")}
    judge_model = ", ".join(sorted({j["judge_model"] for j in judgements}))

    items = build_items(reference, judge_results, claims, answers)
    md_path = RESULTS_DIR / f"adjudication_run{run}.md"
    md_path.write_text(render_markdown(run, judge_model, items), encoding="utf-8")
    print(f"{len(items)} disagreements -> {md_path.name}")

    out = adjudications_path(run)
    if out.exists():
        print(f"{out.name} already exists: left unchanged (your decisions are kept)")
        return
    template = decisions_template(run, judge_model, items)
    out.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'-> {out.name}: fill in each "decision"')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--check", action="store_true", help="Check every decision is filled in")
    args = parser.parse_args()
    if args.check:
        decisions = json.loads(adjudications_path(args.run).read_text(encoding="utf-8"))
        problems = check_decisions(decisions)
        for p in problems:
            print(p)
        print(f"{len(decisions['claims']) - len(problems)}/{len(decisions['claims'])} decided")
        sys.exit(1 if problems else 0)
    write_files(args.run)
