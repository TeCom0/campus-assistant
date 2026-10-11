"""Blind hand labels for the faithfulness evaluation.

Writes a self-contained HTML page (no server, no internet) for labelling one
run's claims by hand: for each answer, the question, the answer, its claims
with the passages each is checked against, and label buttons. Labels autosave
in the browser; "Export" downloads the labels JSON, which goes in
eval/results/faithfulness/. The page holds no judge output, and not the
question's `set` either (knowing a question is a "regression" could tilt a
label).

Two label sets per run:
  full    every claim the judge sees           -> labels_runN.json
  sample  a stratified random sample of them  -> labels_runN_sample.json
Once a sample is drawn (sample_runN.json records it), the sample is the
REFERENCE: the judge's agreement is measured on it, and the judge refuses to
run on a hand-labelled run until the reference is complete (judge_claims.py).
Run 1's full pass (2026-10-11) took ~5 s per claim, too fast to read the
passages, so a careful 40-claim sample replaced it as the reference.

Usage (from backend/):
    python -m app.evaluation.hand_labels --run 1               # full page
    python -m app.evaluation.hand_labels --run 1 --sample 40   # draw the sample, write its page
    python -m app.evaluation.hand_labels --run 1 --check       # what the reference still lacks
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.evaluation.generate_faithfulness_answers import RESULTS_DIR

TEMPLATE_PATH = Path(__file__).with_name("labelling_template.html")
VALID_LABELS = {"supported", "unsupported", "no_claim"}
SAMPLE_SEED = 20261011
# So one long answer (15 claims) can't fill the sample on its own.
MAX_SAMPLED_PER_ANSWER = 3


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sample_path(run: int) -> Path:
    return RESULTS_DIR / f"sample_run{run}.json"


def set_name(run: int, sample: bool) -> str:
    return f"run{run}_sample" if sample else f"run{run}"


def labels_path(run: int, sample: bool) -> Path:
    return RESULTS_DIR / f"labels_{set_name(run, sample)}.json"


def reference_is_sample(run: int) -> bool:
    return sample_path(run).exists()


def reference_labels_path(run: int) -> Path:
    return labels_path(run, reference_is_sample(run))


def stratified_sample(claims: list[dict], n: int, seed: int = SAMPLE_SEED) -> list[str]:
    """`n` claim ids, allocated to (kind, language) groups in proportion to
    their size (largest remainder), drawn at random within each group, at most
    MAX_SAMPLED_PER_ANSWER per answer. Same claims + seed -> same sample."""
    rng = random.Random(seed)
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for c in claims:
        strata[(c["kind"], c["language"])].append(c)
    exact = {key: n * len(group) / len(claims) for key, group in strata.items()}
    allocation = {key: int(share) for key, share in exact.items()}
    by_remainder = sorted(exact, key=lambda key: (allocation[key] - exact[key], key))
    for key in by_remainder[: n - sum(allocation.values())]:
        allocation[key] += 1

    chosen, per_answer = [], Counter()
    for key in sorted(strata):
        pool = strata[key][:]
        rng.shuffle(pool)
        taken = 0
        for c in pool:
            if taken == allocation[key]:
                break
            if per_answer[c["id"]] < MAX_SAMPLED_PER_ANSWER:
                chosen.append(c["claim_id"])
                per_answer[c["id"]] += 1
                taken += 1
    return chosen


def labelling_items(
    answers: list[dict], claims: list[dict], only: set[str] | None = None
) -> list[dict]:
    """What a human labels: each answer with the claims the judge would see
    (or only the ones in `only`, for a sample).

    Claims auto-labelled in code (markers no tool returned) are left out, and
    so are answers left with nothing to label (e.g. ones that crashed).
    """
    to_label = defaultdict(list)
    for c in claims:
        if not c["auto_label"] and (only is None or c["claim_id"] in only):
            to_label[c["id"]].append(
                {k: c[k] for k in ("claim_id", "text", "kind", "markers", "block_type")}
            )
    return [
        {
            "id": a["id"],
            "language": a["language"],
            "question": a["question"],
            "answer": a["answer"],
            "passages": a["passages"],
            "claims": to_label[a["id"]],
        }
        for a in answers
        if to_label[a["id"]]
    ]


def missing_labels(labels: dict, items: list[dict]) -> list[str]:
    """Claim ids without a valid label, and answer ids without an abstains answer."""
    claim_labels = labels.get("claims", {})
    answer_labels = labels.get("answers", {})
    missing = []
    for item in items:
        if not isinstance(answer_labels.get(item["id"], {}).get("abstains"), bool):
            missing.append(f"{item['id']} (abstains)")
        for c in item["claims"]:
            if claim_labels.get(c["claim_id"], {}).get("label") not in VALID_LABELS:
                missing.append(c["claim_id"])
    return missing


def _run_files(run: int) -> tuple[list[dict], list[dict]]:
    answers = _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")
    claims = _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl")
    return answers, claims


def load_items(run: int, sample: bool) -> list[dict]:
    answers, claims = _run_files(run)
    only = None
    if sample:
        only = set(json.loads(sample_path(run).read_text(encoding="utf-8"))["claim_ids"])
    return labelling_items(answers, claims, only)


def labels_complete(run: int) -> bool:
    """Is the reference label set (the sample, if one was drawn) fully labelled?"""
    sample = reference_is_sample(run)
    path = labels_path(run, sample)
    if not path.exists():
        return False
    labels = json.loads(path.read_text(encoding="utf-8"))
    return labels.get("run") == run and not missing_labels(labels, load_items(run, sample))


def draw_sample(run: int, n: int) -> None:
    path = sample_path(run)
    if path.exists():
        raise SystemExit(f"{path.name} already exists: re-drawing would change a sample in use")
    _, claims = _run_files(run)
    labellable = [c for c in claims if not c["auto_label"]]
    claim_ids = stratified_sample(labellable, n)
    spec = {
        "run": run,
        "seed": SAMPLE_SEED,
        "n": n,
        "method": "proportional to (kind, language), largest remainder, "
        f"at most {MAX_SAMPLED_PER_ANSWER} per answer",
        "claim_ids": claim_ids,
    }
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chosen = [c for c in labellable if c["claim_id"] in set(claim_ids)]
    print(f"{path.name}: {len(claim_ids)} of {len(labellable)} claims")
    print("  by kind:", dict(sorted(Counter(c["kind"] for c in chosen).items())))
    print("  by language:", dict(sorted(Counter(c["language"] for c in chosen).items())))


def write_page(run: int, sample: bool) -> Path:
    items = load_items(run, sample)
    name = set_name(run, sample)
    data = json.dumps({"run": run, "name": name, "items": items}, ensure_ascii=False)
    # "</" inside the JSON would end the <script> element early.
    data = data.replace("</", "<\\/")
    page = TEMPLATE_PATH.read_text(encoding="utf-8").replace("__DATA__", data)
    out_path = RESULTS_DIR / f"labelling_{name}.html"
    out_path.write_text(page, encoding="utf-8")
    n_claims = sum(len(i["claims"]) for i in items)
    print(f"{out_path} -- {len(items)} answers, {n_claims} claims to label")
    return out_path


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--sample", type=int, metavar="N", help="Draw an N-claim sample")
    parser.add_argument("--check", action="store_true", help="What the reference still lacks")
    args = parser.parse_args()

    if args.check:
        sample = reference_is_sample(args.run)
        path = labels_path(args.run, sample)
        if not path.exists():
            raise SystemExit(f"{path.name} not found: export it from the labelling page first")
        labels = json.loads(path.read_text(encoding="utf-8"))
        missing = missing_labels(labels, load_items(args.run, sample))
        print(
            f"{path.name}: {len(missing)} missing" + (": " + ", ".join(missing) if missing else "")
        )
    elif args.sample:
        draw_sample(args.run, args.sample)
        write_page(args.run, sample=True)
    else:
        write_page(args.run, sample=False)
