"""Write what query_courses returns for every course code, to compare before and after a change.

    python -m app.evaluation.dump_course_lookups --out 2026-11-15_a2_3_before

The A2.3 rule (CLAUDE.md) says per-edition course tables must not change a single lookup while
there is one edition. This calls the tool's own lookup function directly, so it costs 0 LLM
tokens, and writes one block per lookup: the text the model reads, then the citation and the
trace record, as sorted JSON. Two runs on the same data give the same bytes, so a plain file
comparison is the check.

The codes: every course in `courses`, every prerequisite code with no course row (the
"no_description" path), and two codes that exist nowhere (the "not_found" path), each looked
up with and without the prerequisite chain. The list of codes is written at the top, so a
lost or added course shows up there before any lookup differs.
"""

import argparse
import json
import sys
from pathlib import Path

from app.agent.citations import reset_citation_counter
from app.agent.tools import _look_up_course
from app.db.connection import get_connection

RESULTS_DIR = Path(__file__).resolve().parents[3] / "eval" / "results" / "courses"
NOT_FOUND_CODES = ("ACC 9999", "ZZZ 1000")


def lookup_codes(conn) -> tuple[list[str], list[str]]:
    """(codes with a course row, prerequisite codes without one), each sorted."""
    courses = [r[0] for r in conn.execute("SELECT code FROM courses ORDER BY code").fetchall()]
    referenced_only = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT prerequisite_code FROM course_prerequisites "
            "WHERE prerequisite_code NOT IN (SELECT code FROM courses) ORDER BY 1"
        ).fetchall()
    ]
    return courses, referenced_only


def lookup_block(code: str, follow_prerequisites: bool) -> str:
    # A fresh counter per lookup, as each request gets one, so every block starts at [1].
    reset_citation_counter()
    text, citations, lookup = _look_up_course(code, follow_prerequisites)
    meta = json.dumps(
        {"citations": citations, "lookup": lookup}, ensure_ascii=False, sort_keys=True
    )
    return f"=== {code} follow_prerequisites={follow_prerequisites}\n{text}\n{meta}\n"


def dump(out_path: Path) -> tuple[int, int, int]:
    conn = get_connection()
    try:
        courses, referenced_only = lookup_codes(conn)
    finally:
        conn.close()
    codes = courses + referenced_only + list(NOT_FOUND_CODES)
    parts = [
        f"courses: {len(courses)}\n",
        f"referenced without a course row: {len(referenced_only)} {referenced_only}\n",
        f"not found: {list(NOT_FOUND_CODES)}\n",
        f"codes: {courses}\n\n",
    ]
    for code in codes:
        for follow in (False, True):
            parts.append(lookup_block(code, follow))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(parts), encoding="utf-8", newline="\n")
    return len(courses), len(referenced_only), 2 * len(codes)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="Output file name, without .txt")
    args = parser.parse_args()
    out_path = RESULTS_DIR / f"{args.out}.txt"
    courses, referenced_only, lookups = dump(out_path)
    print(
        f"{courses} courses, {referenced_only} referenced without a course row, "
        f"{lookups} lookups -> {out_path} ({out_path.stat().st_size:,} bytes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
