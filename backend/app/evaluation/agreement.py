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

Also: what the quote check changed (judge's own label vs. final label), the
"does the answer decline?" agreement, and how the quick full pass compares
with the careful sample on the same claims.

Usage (from backend/):
    python -m app.evaluation.agreement --run 1
"""

import argparse
import json
import math
import sys
from collections import Counter

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

    final = compare(human, judge_final)
    before_quote_check = compare(human, judge_own)
    human_abstains = {a: v["abstains"] for a, v in reference["answers"].items()}
    judge_abstains = {j["id"]: j["abstains"] for j in judgements if j["id"] in human_abstains}
    abstains_agree = sum(human_abstains[a] == judge_abstains.get(a) for a in human_abstains)

    print(
        f"Reference: {labels_path(run_number, sample).name} ({final['n']} claims; "
        f"{len(excluded)} excluded from scoring and not compared)"
    )
    for cid in excluded:
        print(f"  excluded ({claims[cid]['exclude']}): {cid}  {claim_text[cid]!r}")
    low, high = final["ci95"]
    print(
        f"\nAgreement: {final['agree']}/{final['n']} = {100 * final['agreement']:.0f}% "
        f"(95% CI {100 * low:.0f}-{100 * high:.0f}%), Cohen's kappa {final['kappa']}"
    )
    print(f"  lenient (judge supported, you unsupported): {len(final['lenient'])}")
    print(f"  strict  (judge unsupported, you supported): {len(final['strict'])}")
    print("  you -> judge:", final["confusion"])
    print(
        f"Before the quote check: {before_quote_check['agree']}/{before_quote_check['n']} "
        f"(quote_not_found flags in the sample: "
        f"{sum(1 for i in human if results.get(i, {}).get('flag') == 'quote_not_found')})"
    )
    print(f"'Does the answer decline?': {abstains_agree}/{len(human_abstains)} agree")

    quick_path = labels_path(run_number, sample=False)
    quick = None
    if sample and quick_path.exists():
        quick_labels = json.loads(quick_path.read_text(encoding="utf-8"))["claims"]
        # Your self-agreement, on the same (non-excluded) claims as the judge.
        quick = compare(human, {cid: v["label"] for cid, v in quick_labels.items()})
        print(
            f"Quick full pass vs. careful sample, same claims: {quick['agree']}/{quick['n']} "
            f"agree (judge vs. careful sample: {final['agree']}/{final['n']})"
        )

    print("\nDisagreements:")
    for cid in final["disagreements"]:
        r = results[cid]
        print(
            f"\n- {cid}: you {human[cid]}, judge {r['label']}"
            + (f" [{r['flag']}]" if r["flag"] else "")
        )
        print(f"  claim:  {claim_text.get(cid, '')}")
        print(f"  judge:  {r.get('reason', '')}")
        if notes.get(cid):
            print(f"  your note: {notes[cid]}")

    summary = {
        "run": run_number,
        "reference": labels_path(run_number, sample).name,
        "excluded": {cid: claims[cid]["exclude"] for cid in excluded},
        "final": final,
        "before_quote_check": before_quote_check,
        "abstains": {"agree": abstains_agree, "n": len(human_abstains)},
        "quick_pass_vs_reference": quick,
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
