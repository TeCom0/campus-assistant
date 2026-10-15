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

Declines are checked per answer against the question's expected_behavior
("answer" / "abstain"), using the judge's "does the answer decline?" verdict:
  false refusal   declined a question it should have answered
  missed refusal  answered a question it should have declined
Refusal sentences and short lead-ins ("The main options are:") are excluded
from faithfulness scoring (split_claims.exclusion_reason); these two counts
are what keeps an excluded refusal from hiding an error, and every excluded
claim is listed in the output.

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
    """claim_id -> final label for every scored (not excluded) claim; None if
    the claim still needs a judge."""
    judged = {c["claim_id"]: c["label"] for j in judgements for c in j["claims"]}
    return {
        c["claim_id"]: c["auto_label"] or judged.get(c["claim_id"])
        for c in claims
        if not c.get("exclude")
    }


def summarize_answer(
    answer: dict, question: dict, claims: list[dict], labels: dict, abstains: bool | None
) -> dict:
    """One answer's numbers; claims are this answer's claims only."""
    excluded = [c for c in claims if c.get("exclude")]
    claims = [c for c in claims if not c.get("exclude")]
    answered = answer["error"] is None

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
        "error": not answered,
        "abstains": abstains,
        "false_refusal": answered
        and question["expected_behavior"] == "answer"
        and abstains is True,
        "missed_refusal": (
            answered and question["expected_behavior"] == "abstain" and abstains is False
        ),
        "excluded_claims": len(excluded),
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
        "should_answer": sum(1 for a in answered if a["expected_behavior"] == "answer"),
        "false_refusals": [a["id"] for a in answered if a["false_refusal"]],
        "should_abstain": sum(1 for a in answered if a["expected_behavior"] == "abstain"),
        "missed_refusals": [a["id"] for a in answered if a["missed_refusal"]],
        # No "does it decline?" verdict: neither check can run on these.
        "no_decline_verdict": [a["id"] for a in answered if a["abstains"] is None],
        "excluded_claims": sum(a["excluded_claims"] for a in answered),
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


def load_run(run: int, questions: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Answer summaries for one run, and its excluded claims; refuses if any
    scored claim is unjudged."""
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
    summaries = [
        summarize_answer(
            a, questions[a["id"]], claims_by_answer[a["id"]], labels, abstains.get(a["id"])
        )
        for a in answers
    ]
    excluded = [
        {"claim_id": c["claim_id"], "exclude": c["exclude"], "text": c["text"]}
        for c in claims
        if c.get("exclude")
    ]
    return summaries, excluded


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


def print_refusal_checks(title: str, stats: dict[str, dict]) -> None:
    """False and missed refusals over all of a run's answered questions."""
    groups = [stats[name] for name in ("main", "regression", "unanswerable")]
    false_refusals = [i for g in groups for i in g["false_refusals"]]
    missed_refusals = [i for g in groups for i in g["missed_refusals"]]
    no_verdict = [i for g in groups for i in g["no_decline_verdict"]]
    should_answer = sum(g["should_answer"] for g in groups)
    should_abstain = sum(g["should_abstain"] for g in groups)
    print(f"\n{title} -- declines vs. expected behaviour:")
    print(
        f"  false refusals (declined, should answer):   "
        f"{len(false_refusals)}/{should_answer}  {false_refusals}"
    )
    print(
        f"  missed refusals (answered, should decline): "
        f"{len(missed_refusals)}/{should_abstain}  {missed_refusals}"
    )
    print(f"  no decline verdict: {len(no_verdict)}  {no_verdict}")


def print_excluded(title: str, excluded: list[dict]) -> None:
    print(f"\n{title} -- {len(excluded)} claims excluded from scoring:")
    for c in excluded:
        print(f"  {c['exclude']:<8} {c['claim_id']:<28} {c['text']!r}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, nargs="+", default=[1, 2])
    args = parser.parse_args()

    questions = {q["id"]: q for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))}
    loaded = {run: load_run(run, questions) for run in args.runs}
    by_run = {run: answers for run, (answers, _) in loaded.items()}

    report = {"runs": args.runs, "by_run": {}, "combined": None, "excluded": {}}
    for run, answers in by_run.items():
        report["by_run"][run] = grouped(answers)
        print_table(f"Run {run}", report["by_run"][run])
        print_refusal_checks(f"Run {run}", report["by_run"][run])
        report["excluded"][run] = loaded[run][1]
        print_excluded(f"Run {run}", loaded[run][1])
    if len(by_run) > 1:
        report["combined"] = grouped([a for answers in by_run.values() for a in answers])
        print_table(f"Runs {' + '.join(map(str, args.runs))} combined", report["combined"])
        print_refusal_checks(f"Runs {' + '.join(map(str, args.runs))}", report["combined"])
    print(
        "\nunfaithful = answers with >=1 unsupported cited claim; own only = the same, counting "
        "only claims with their own marker;\nuncited = answers with >=1 unsupported uncited "
        "claim; cite 0 = answers citing nothing; declined = judge says the answer declines."
    )
    report["answers"] = [a for answers in by_run.values() for a in answers]
    out = RESULTS_DIR / f"report_runs_{'_'.join(map(str, args.runs))}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {out.name}")
