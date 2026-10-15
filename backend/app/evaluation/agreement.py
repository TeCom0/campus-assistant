"""How well the faithfulness judge agrees with the hand labels.

Compares the reference hand labels (run 1: the careful 40-claim sample) with
the judge's labels on the same claims. Reports raw agreement with a 95%
confidence interval (Wilson -- with 40 claims the uncertainty is wide, and
saying so is the honest version), Cohen's kappa (agreement corrected for the
agreement two labellers would reach by chance given how often each uses each
label), and the two error directions separately:

  lenient  judge "supported", human "unsupported" -- the dangerous one: it
           hides exactly the errors the evaluation exists to find
  strict   judge "unsupported", human "supported"

Measured separately:

  label agreement  the judge's own label vs. the human's: its judgement
  quote validity   of the judge's "supported" verdicts in the whole run, how
                   many quotes really are in the passages: its evidence
  final agreement  after the quote check (a "supported" whose quote isn't
                   found becomes "unsupported"): what report.py uses

each against the original reference labels and, once they exist, the
adjudicated ones (the original plus the decisions in adjudications_runN.json;
not blind, so both are always shown). Also: the "does the answer decline?"
agreement, and the human's self-agreement (quick full pass vs. careful sample)
on the same claims. Claims excluded from scoring (refusals, lead-ins) are left
out on both sides.

Usage (from backend/):
    python -m app.evaluation.agreement --run 1
"""

import argparse
import json
import math
import sys
from collections import Counter

from app.evaluation.adjudication import adjudications_path, blind_paths, check_decisions
from app.evaluation.generate_faithfulness_answers import RESULTS_DIR
from app.evaluation.hand_labels import labels_path, reference_is_sample

LABELS = ("supported", "unsupported", "no_claim")


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a proportion; sensible at small n, unlike p ± 2·SE."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def cohens_kappa(pairs: list[tuple[str, str]]) -> float:
    """(observed agreement - chance agreement) / (1 - chance agreement)."""
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    chance = sum(first[label] * second[label] for label in first) / (n * n)
    return 1.0 if chance == 1 else (observed - chance) / (1 - chance)


def compare(human: dict[str, str], judge: dict[str, str]) -> dict:
    """Agreement statistics over the claims both labelled."""
    ids = sorted(set(human) & set(judge))
    pairs = [(human[i], judge[i]) for i in ids]
    agree = sum(h == j for h, j in pairs)
    low, high = wilson_interval(agree, len(pairs))
    return {
        "n": len(pairs),
        "agree": agree,
        "agreement": agree / len(pairs),
        "ci95": [round(low, 3), round(high, 3)],
        "kappa": round(cohens_kappa(pairs), 3),
        "confusion": {f"{h} -> {j}": n for (h, j), n in sorted(Counter(pairs).items())},
        "lenient": [i for i in ids if judge[i] == "supported" and human[i] == "unsupported"],
        "strict": [i for i in ids if judge[i] == "unsupported" and human[i] == "supported"],
        "disagreements": [i for i in ids if human[i] != judge[i]],
    }


def unjudged(human: dict[str, str], judge: dict[str, str]) -> list[str]:
    """Reference claims the judge has no label for yet (e.g. it stopped early)."""
    return sorted(set(human) - set(judge))


def apply_adjudications(human: dict[str, str], decisions: dict) -> dict[str, str]:
    """The reference labels with each adjudicated claim's decision instead."""
    return {
        cid: decisions["claims"][cid]["decision"] if cid in decisions["claims"] else label
        for cid, label in human.items()
    }


def quote_validity(results: list[dict]) -> dict:
    """Of the judge's "supported" verdicts, how many quotes were found verbatim."""
    supported = [r for r in results if r["judge_label"] == "supported"]
    found = sum(1 for r in supported if r["flag"] != "quote_not_found")
    low, high = wilson_interval(found, len(supported))
    return {
        "supported_verdicts": len(supported),
        "quote_found": found,
        "rate": round(found / len(supported), 3) if supported else None,
        "ci95": [round(low, 3), round(high, 3)],
    }


def _line(name: str, stats: dict) -> str:
    low, high = stats["ci95"]
    return (
        f"  {name:<18} {stats['agree']:>2}/{stats['n']} = {100 * stats['agreement']:3.0f}% "
        f"({100 * low:.0f}-{100 * high:.0f}%)  kappa {stats['kappa']:>6}  "
        f"lenient {len(stats['lenient'])}  strict {len(stats['strict'])}"
    )


def _load_jsonl(path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run(run_number: int) -> dict:
    sample = reference_is_sample(run_number)
    reference = json.loads(labels_path(run_number, sample).read_text(encoding="utf-8"))
    claims = {c["claim_id"]: c for c in _load_jsonl(RESULTS_DIR / f"claims_run{run_number}.jsonl")}
    # Refusals and lead-ins aren't scored (split_claims.exclusion_reason), so they
    # aren't compared either -- on both sides, and for the quick pass too.
    excluded = sorted(cid for cid in reference["claims"] if claims[cid].get("exclude"))
    human = {cid: v["label"] for cid, v in reference["claims"].items() if cid not in excluded}
    notes = {cid: v.get("note", "") for cid, v in reference["claims"].items()}

    judgements_path = RESULTS_DIR / f"judgements_run{run_number}.jsonl"
    judgements = _load_jsonl(judgements_path) if judgements_path.exists() else []
    results = {c["claim_id"]: c for j in judgements for c in j["claims"]}
    judge_final = {cid: r["label"] for cid, r in results.items() if r["label"]}
    judge_own = {cid: r["judge_label"] for cid, r in results.items() if r["judge_label"]}
    # Statistics over part of the sample would look like a result but aren't one
    # (on 2026-10-12 a stopped judge left 4 of 40 claims: "75%, kappa 0.0").
    missing = unjudged(human, judge_final)
    if missing:
        raise SystemExit(
            f"The judge hasn't labelled {len(missing)} of the {len(human)} reference claims "
            f"yet; finish it first: python -m app.evaluation.judge_claims --run {run_number}"
        )
    claim_text = {cid: c["text"] for cid, c in claims.items()}

    references = {"original": human}
    decisions_path = adjudications_path(run_number)
    blind_path = blind_paths(run_number)[1]
    if decisions_path.exists():
        decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
        if blind_path.exists():  # the blind round's decisions add to the first round's
            blind = json.loads(blind_path.read_text(encoding="utf-8"))
            if check_decisions(blind):
                raise SystemExit(
                    f"{blind_path.name} isn't finished; check: python -m "
                    f"app.evaluation.adjudication --run {run_number} --blind --check"
                )
            decisions = {"claims": {**decisions["claims"], **blind["claims"]}}
        references["adjudicated"] = apply_adjudications(human, decisions)
    label = {name: compare(ref, judge_own) for name, ref in references.items()}
    final = {name: compare(ref, judge_final) for name, ref in references.items()}
    scored = [r for cid, r in results.items() if not claims[cid].get("exclude")]
    quotes = {
        "run": quote_validity(scored),
        "sample": quote_validity([results[cid] for cid in human]),
    }
    human_abstains = {a: v["abstains"] for a, v in reference["answers"].items()}
    judge_abstains = {j["id"]: j["abstains"] for j in judgements if j["id"] in human_abstains}
    abstains_agree = sum(human_abstains[a] == judge_abstains.get(a) for a in human_abstains)

    print(
        f"Reference: {labels_path(run_number, sample).name} ({len(human)} claims; "
        f"{len(excluded)} excluded from scoring and not compared)"
    )
    for cid in excluded:
        print(f"  excluded ({claims[cid]['exclude']}): {cid}  {claim_text[cid]!r}")
    if "adjudicated" in references:
        changed = sum(references["adjudicated"][c] != human[c] for c in human)
        files = decisions_path.name + (f" + {blind_path.name}" if blind_path.exists() else "")
        print(f"Adjudicated: {files} ({changed} labels differ from the original)")
    else:
        print(f"Adjudicated: none yet ({decisions_path.name} doesn't exist)")

    print("\nLabel agreement (the judge's own label):")
    for name, stats in label.items():
        print(_line(f"vs. {name}", stats))
    print("Final agreement (after the quote check, as the report uses):")
    for name, stats in final.items():
        print(_line(f"vs. {name}", stats))
    for scope, q in quotes.items():
        if q["supported_verdicts"]:
            low, high = q["ci95"]
            print(
                f"Quote validity ({scope}): {q['quote_found']}/{q['supported_verdicts']} "
                f"'supported' quotes found verbatim = {100 * q['rate']:.0f}% "
                f"({100 * low:.0f}-{100 * high:.0f}%)"
            )
    print(f"'Does the answer decline?': {abstains_agree}/{len(human_abstains)} agree")

    quick_path = labels_path(run_number, sample=False)
    quick = None
    if sample and quick_path.exists():
        quick_labels = json.loads(quick_path.read_text(encoding="utf-8"))["claims"]
        # Your self-agreement, on the same (non-excluded) claims as the judge.
        quick = compare(human, {cid: v["label"] for cid, v in quick_labels.items()})
        print(f"Your self-agreement (quick pass vs. careful sample): {quick['agree']}/{quick['n']}")

    shown = "adjudicated" if "adjudicated" in references else "original"
    shown_labels = references[shown]
    print(f"\nDisagreements (final label vs. {shown} labels):")
    for cid in final[shown]["disagreements"]:
        r = results[cid]
        print(
            f"\n- {cid}: you {shown_labels[cid]}, judge {r['judge_label']} -> {r['label']}"
            + (f" [{r['flag']}]" if r["flag"] else "")
        )
        print(f"  claim:  {claim_text.get(cid, '')}")
        print(f"  quote:  {r.get('evidence_quote') or '(none)'}")
        print(f"  judge:  {r.get('reason', '')}")
        if notes.get(cid):
            print(f"  your note: {notes[cid]}")

    summary = {
        "run": run_number,
        "reference": labels_path(run_number, sample).name,
        "adjudications": decisions_path.name if "adjudicated" in references else None,
        "excluded": {cid: claims[cid]["exclude"] for cid in excluded},
        "label_agreement": label,
        "final_agreement": final,
        "quote_validity": quotes,
        "abstains": {"agree": abstains_agree, "n": len(human_abstains)},
        "self_agreement": quick,
    }
    out = RESULTS_DIR / f"agreement_run{run_number}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {out.name}")
    return summary


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    run(parser.parse_args().run)
