"""Blind hand labels for the faithfulness evaluation.

Writes a self-contained HTML page (no server, no internet) for labelling one
run's claims by hand: for each answer, the question, the answer, its claims
with the passages each is checked against, and label buttons. Labels autosave
in the browser; "Export" downloads labels_runN.json, which goes in
eval/results/faithfulness/. The page holds no judge output, and not the
question's `set` either (knowing a question is a "regression" could tilt a
label).

Also checks that a labels file is complete -- the judge refuses to run on a
hand-labelled run before it is (judge_claims.py), and the agreement step
reads it.

Usage (from backend/):
    python -m app.evaluation.hand_labels --run 1           # write the page
    python -m app.evaluation.hand_labels --run 1 --check   # what's still unlabelled
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from app.evaluation.generate_faithfulness_answers import RESULTS_DIR

TEMPLATE_PATH = Path(__file__).with_name("labelling_template.html")
VALID_LABELS = {"supported", "unsupported", "no_claim"}


def labels_path(run: int) -> Path:
    return RESULTS_DIR / f"labels_run{run}.json"


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def labelling_items(answers: list[dict], claims: list[dict]) -> list[dict]:
    """What a human labels: each answer with the claims the judge would see.

    Claims auto-labelled in code (markers no tool returned) are left out, and
    so are answers left with nothing to label (e.g. ones that crashed).
    """
    to_label = defaultdict(list)
    for c in claims:
        if not c["auto_label"]:
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


def load_items(run: int) -> list[dict]:
    answers = _load_jsonl(RESULTS_DIR / f"answers_run{run}.jsonl")
    claims = _load_jsonl(RESULTS_DIR / f"claims_run{run}.jsonl")
    return labelling_items(answers, claims)


def labels_complete(run: int) -> bool:
    path = labels_path(run)
    if not path.exists():
        return False
    labels = json.loads(path.read_text(encoding="utf-8"))
    return labels.get("run") == run and not missing_labels(labels, load_items(run))


def write_page(run: int) -> Path:
    items = load_items(run)
    data = json.dumps({"run": run, "items": items}, ensure_ascii=False)
    # "</" inside the JSON would end the <script> element early.
    data = data.replace("</", "<\\/")
    page = TEMPLATE_PATH.read_text(encoding="utf-8").replace("__DATA__", data)
    out_path = RESULTS_DIR / f"labelling_run{run}.html"
    out_path.write_text(page, encoding="utf-8")
    n_claims = sum(len(i["claims"]) for i in items)
    print(f"{out_path} -- {len(items)} answers, {n_claims} claims to label")
    return out_path


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--check", action="store_true", help="List what's still unlabelled")
    args = parser.parse_args()

    if args.check:
        path = labels_path(args.run)
        if not path.exists():
            raise SystemExit(f"{path.name} not found: export it from the labelling page first")
        labels = json.loads(path.read_text(encoding="utf-8"))
        missing = missing_labels(labels, load_items(args.run))
        print(f"{len(missing)} missing" + (": " + ", ".join(missing[:20]) if missing else ""))
    else:
        write_page(args.run)
