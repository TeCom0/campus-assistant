"""Faithfulness baseline report: from judged claims to the headline numbers.

Rolls claim labels up to answers, and answers up to groups:

  claim    final label = the judge's label after the quote check, or the
           auto label split_claims gave (a claim citing only markers no tool
           returned is "unsupported" without being judged)
  answer   crashed? declined to answer? how many cited claims, how many of
           them unsupported; the same for `own` claims only, and for uncited
  group    `main` (the baseline, also split EN / FR), `regression`,
           `unanswerable`; each run on its own and both runs together

Headline: % of answered questions with >=1 unsupported cited claim, with a
Wilson 95% interval (26 `main` answers per run is a small sample). Crashed
answers have no claims, so they're reported next to the headline, not in it.
Answers citing nothing are counted too: they can't have an unsupported cited
claim, so a model that stopped citing would otherwise look perfect.

For `unanswerable` questions the right behaviour is to decline: the report
shows how often it did, and how often answerable questions were declined.

Usage (from backend/):
    python -m app.evaluation.report --runs 1 2
"""

import argparse
import json
import sys
from collections import defaultdict

from app.evaluation.agreement import wilson_interval
from app.evaluation.generate_faithfulness_answers import EVAL_SET_PATH, RESULTS_DIR

CITED_KINDS = ("own", "block", "lead_in", "source_line")


def _load_jsonl(path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def final_labels(claims: list[dict], judgements: list[dict]) -> dict[str, str | None]:
    """claim_id -> final label; None if the claim still needs a judge."""
    judged = {c["claim_id"]: c["label"] for j in judgements for c in j["claims"]}
    return {c["claim_id"]: c["auto_label"] or judged.get(c["claim_id"]) for c in claims}


def summarize_answer(
    answer: dict, question: dict, claims: list[dict], labels: dict, abstains: bool | None
) -> dict:
    """One answer's numbers; claims are this answer's claims only."""

    def unsupported(kinds) -> int:
        return sum(
            1 for c in claims if c["kind"] in kinds and labels[c["claim_id"]] == "unsupported"
        )

    return {
        "id": answer["id"],
        "run": answer["run"],
        "language": question["language"],
        "set": question["set"],
        "expected_behavior": question["expected_behavior"],
        "error": answer["error"] is not None,
        "abstains": abstains,
        "cited_claims": sum(1 for c in claims if c["kind"] in CITED_KINDS),
        "unsupported_cited": unsupported(CITED_KINDS),
        "unsupported_own": unsupported(("own",)),
        "uncited_claims": sum(1 for c in claims if c["kind"] == "uncited"),
        "unsupported_uncited": unsupported(("uncited",)),
    }


def group_stats(answers: list[dict]) -> dict:
    """Headline numbers over a group of answer summaries."""
    answered = [a for a in answers if not a["error"]]
    n = len(answered)
    unfaithful = sum(1 for a in answered if a["unsupported_cited"] > 0)
    low, high = wilson_interval(unfaithful, n)
    declined = sum(1 for a in answered if a["abstains"])
    return {
        "answers": len(answers),
        "errors": len(answers) - n,
        "answered": n,
        # The headline: answers with at least one unsupported cited claim.
        "unfaithful": unfaithful,
        "unfaithful_pct": round(100 * unfaithful / n, 1) if n else None,
        "ci95_pct": [round(100 * low, 1), round(100 * high, 1)],
        "unfaithful_own_only": sum(1 for a in answered if a["unsupported_own"] > 0),
        "with_unsupported_uncited": sum(1 for a in answered if a["unsupported_uncited"] > 0),
        "citing_nothing": sum(1 for a in answered if a["cited_claims"] == 0),
        "declined": declined,
        "cited_claims": sum(a["cited_claims"] for a in answered),
        "unsupported_cited_claims": sum(a["unsupported_cited"] for a in answered),
    }


def grouped(answers: list[dict]) -> dict[str, dict]:
    """The groups the report shows, in display order."""
    groups = {
        "main": [a for a in answers if a["set"] == "main"],
        "main EN": [a for a in answers if a["set"] == "main" and a["language"] == "en"],
        "main FR": [a for a in answers if a["set"] == "main" and a["language"] == "fr"],
        "regression": [a for a in answers if a["set"] == "regression"],
        "unanswerable": [a for a in answers if a["set"] == "unanswerable"],
    }
    return {name: group_stats(group) for name, group in groups.items()}


def load_run(run: int, questions: dict[str, dict]) -> list[dict]:
    """Answer summaries for one run; refuses if any answered question is unjudged."""
    answers = _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")
    claims = _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl")
    judgements_path = RESULTS_DIR / f"judgements_run{run}.jsonl"
    judgements = _load_jsonl(judgements_path) if judgements_path.exists() else []

    labels = final_labels(claims, judgements)
    unlabelled = [cid for cid, label in labels.items() if label is None]
    if unlabelled:
        raise SystemExit(
            f"Run {run}: {len(unlabelled)} claims aren't judged yet; finish first: "
            f"python -m app.evaluation.judge_claims --run {run}"
        )
    abstains = {j["id"]: j["abstains"] for j in judgements}
    claims_by_answer = defaultdict(list)
    for c in claims:
        claims_by_answer[c["id"]].append(c)
    return [
        summarize_answer(
            a, questions[a["id"]], claims_by_answer[a["id"]], labels, abstains.get(a["id"])
        )
        for a in answers
    ]


def print_table(title: str, stats: dict[str, dict]) -> None:
    print(f"\n{title}")
    print(
        f"  {'group':<13} {'answered':>8} {'errors':>6}  {'unfaithful (95% CI)':<27}"
        f"{'own only':>8} {'uncited':>8} {'cite 0':>7} {'declined':>9}"
    )
    for name, s in stats.items():
        n = s["answered"]
        pct = f"{s['unfaithful']}/{n} = {s['unfaithful_pct']}%" if n else "-"
        low, high = s["ci95_pct"]
        print(
            f"  {name:<13} {n:>8} {s['errors']:>6}  {pct + f' ({low}-{high})':<27}"
            f"{s['unfaithful_own_only']:>8} {s['with_unsupported_uncited']:>8} "
            f"{s['citing_nothing']:>7} {s['declined']:>9}"
        )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, nargs="+", default=[1, 2])
    args = parser.parse_args()

    questions = {q["id"]: q for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))}
    by_run = {run: load_run(run, questions) for run in args.runs}

    report = {"runs": args.runs, "by_run": {}, "combined": None}
    for run, answers in by_run.items():
        report["by_run"][run] = grouped(answers)
        print_table(f"Run {run}", report["by_run"][run])
    if len(by_run) > 1:
        report["combined"] = grouped([a for answers in by_run.values() for a in answers])
        print_table(f"Runs {' + '.join(map(str, args.runs))} combined", report["combined"])
    print(
        "\nunfaithful = answers with >=1 unsupported cited claim; own only = the same, counting "
        "only claims with their own marker;\nuncited = answers with >=1 unsupported uncited "
        "claim; cite 0 = answers citing nothing; declined = judge says the answer declines."
    )
    report["answers"] = [a for answers in by_run.values() for a in answers]
    out = RESULTS_DIR / f"report_runs_{'_'.join(map(str, args.runs))}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {out.name}")
