"""The dry run: every check an edition must pass before it is written, and a verdict
(A2.4 step 5; docs/architecture.md, 4.3; CLAUDE.md, "A2.4 rule").

    python -m app.ingestion.ingest <edition id> [<edition id> ...] --dry-run
    python -m app.ingestion.ingest --all --dry-run

For each edition, in the order the pipeline will write it:

1. gates (gates.py): visibility, language, format, file, size, sha256, encrypted, pages.
   A refusal here stops that edition's report: its file can't be trusted or read.
2. sanitising (sanitise.py): what was removed is reported.
3. scan (scan.py) with the decisions in data/review/<edition id>.toml; redactions are
   applied to the text the next steps read.
4. near-empty and table-like pages (PDF only), and encoding errors (quality.py).
5. chunking, as chunk.py does it, then the token length of every chunk as embedded.
6. headings, and for the course-tables edition the courses: compared with the previous
   edition, the document's edition in force (read from the database, SELECT only), when
   there is one; otherwise reported only.

Every check runs even after one refuses, so one run shows everything to fix. The verdict
is "refused" if any check refused, "held" if a scan hit has no decision, else "pass".
Nothing is written, and the exit code is 0 only if every edition passed.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.ingestion import quality
from app.ingestion.chunk import Chunk, chunk_text, settings_for
from app.ingestion.clean import RAW_DIR
from app.ingestion.courses import extract_courses_from_text
from app.ingestion.gates import IngestRefused, extract_edition
from app.ingestion.scan import REVIEW_DIR, DecisionsError, load_decisions, review
from app.registry import Registry, load_registry

OUTCOMES = ("pass", "reported", "held", "refused")


@dataclass(frozen=True)
class Check:
    name: str
    outcome: str  # one of OUTCOMES; "reported": measured, with nothing to compare against
    summary: str  # one line, for people
    measured: dict = field(default_factory=dict)  # the numbers, for the quality report


@dataclass(frozen=True)
class Baseline:
    """The previous edition's numbers, measured the same way, on its own file."""

    edition_id: str
    headings: int
    courses: int | None  # None unless it is a course-tables edition


@dataclass
class DryRun:
    edition_id: str
    previous: str | None
    checks: list[Check]
    chunks: list[Chunk]

    @property
    def verdict(self) -> str:
        outcomes = {check.outcome for check in self.checks}
        return "refused" if "refused" in outcomes else "held" if "held" in outcomes else "pass"


TokenCounter = Callable[[list[str]], list[int]]


def _model_token_counter() -> tuple[TokenCounter, int]:
    """The embedding model's tokenizer and limit. Imported here: loading the model takes
    a few seconds, and the tests pass their own counter."""
    from app.embeddings import count_tokens, get_model, passage_text

    return (
        lambda texts: count_tokens([passage_text(t) for t in texts]),
        get_model().max_seq_length,
    )


def _share(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.1%})"


def _list(items: list, limit: int = 30) -> str:
    shown = ", ".join(str(item) for item in items[:limit])
    return shown + (f", and {len(items) - limit} more" if len(items) > limit else "")


def _scan_check(edition_id: str, text: str, review_dir: Path) -> tuple[Check, str]:
    """The scan's check, and the text after redaction (the input when it can't run)."""
    try:
        decisions = load_decisions(review_dir / f"{edition_id}.toml")
    except DecisionsError as e:
        return Check("scan", "refused", f"decisions file unusable: {e}"), text
    result = review(text, decisions)
    measured = {
        "hits": dict(Counter(hit.kind for hit in result.hits)),
        "refusals": result.refusals,
        "undecided": sorted({f"{hit.kind} {hit.value!r}" for hit in result.undecided}),
        "redacted": result.redacted,
        "unused_decisions": [f"{d.kind} {d.value!r}" for d in result.unused],
    }
    summary = f"{len(result.hits)} hits, {result.redacted} redacted"
    if result.unused:
        summary += f", {len(result.unused)} unused decisions"
    if result.refusals:
        outcome, summary = "refused", f"{summary}; {_list(result.refusals, 5)}"
    elif result.undecided:
        outcome, summary = "held", f"{summary}; no decision for {_list(measured['undecided'], 5)}"
    else:
        outcome = "pass"
    return Check("scan", outcome, summary, measured), result.text


def _page_checks(text: str, declared_headers: frozenset[str]) -> list[Check]:
    pages = quality.pages_of(text)
    if not pages:
        return []  # a web page: no pages to measure
    total = len(pages)
    headers = quality.header_lines(pages, declared_headers)

    empty = quality.near_empty_pages(pages, headers)
    near_empty = Check(
        "near-empty pages",
        "refused" if len(empty) / total > quality.NEAR_EMPTY_LIMIT else "pass",
        f"{_share(len(empty), total)}, limit {quality.NEAR_EMPTY_LIMIT:.1%}"
        + (f": pages {_list(empty)}" if empty else ""),
        {"pages": empty, "total": total, "header_lines": sorted(headers)},
    )
    tables = quality.table_like_pages(pages)
    table_like = Check(
        "table-like pages",
        "refused" if len(tables) / total > quality.TABLE_LIKE_LIMIT else "pass",
        f"{_share(len(tables), total)}, limit {quality.TABLE_LIKE_LIMIT:.1%}"
        + (f": pages {_list(tables)}" if tables else ""),
        {"pages": tables, "total": total},
    )
    return [near_empty, table_like]


def _encoding_check(text: str) -> Check:
    errors = quality.encoding_errors(text)
    per_10k = errors / max(len(text), 1) * 10_000
    return Check(
        "encoding",
        "refused" if per_10k > quality.ENCODING_LIMIT_PER_10K else "pass",
        f"{errors} replacement or mojibake sequences in {len(text):,} characters "
        f"({per_10k:.2f} per 10,000, limit {quality.ENCODING_LIMIT_PER_10K:g})",
        {"errors": errors, "characters": len(text)},
    )


def _token_check(chunks: list[Chunk], counter: TokenCounter, limit: int) -> Check:
    counts = counter([chunk.text for chunk in chunks])
    over = [(chunk, count) for chunk, count in zip(chunks, counts, strict=True) if count > limit]
    described = [
        f"chunk {chunk.chunk_index} (pages {chunk.pages or '-'}): {count} tokens"
        + (", a table too big for one chunk" if "\n|" in chunk.text else "")
        for chunk, count in over
    ]
    return Check(
        "tokens",
        "refused" if over else "pass",
        f"longest {max(counts)} of {limit}" + (f"; over: {_list(described, 5)}" if over else ""),
        {"longest": max(counts), "limit": limit, "over": [c.chunk_index for c, _ in over]},
    )


def _compared(name: str, found: int, previous: int | None, floor: float, unit: str) -> Check:
    if previous is None:
        return Check(name, "reported", f"{found} {unit} (no previous edition)", {"found": found})
    least = floor * previous
    return Check(
        name,
        "refused" if found < least else "pass",
        f"{found} {unit}, previous edition {previous}"
        + (f" (at least {least:g} needed)" if floor != 1 else ""),
        {"found": found, "previous": previous},
    )


def dry_run(
    registry: Registry,
    edition_id: str,
    raw_dir: Path = RAW_DIR,
    review_dir: Path = REVIEW_DIR,
    previous: Baseline | None = None,
    token_counter: tuple[TokenCounter, int] | None = None,
) -> DryRun:
    """Every check on one edition; writes nothing."""
    edition = registry.edition(edition_id)
    document = registry.document_of(edition_id)
    run = DryRun(edition_id, previous.edition_id if previous else None, [], [])
    try:
        extracted = extract_edition(registry, edition_id, raw_dir)
    except IngestRefused as e:
        run.checks.append(Check("gates", "refused", str(e)))
        return run
    run.checks.append(Check("gates", "pass", f"{edition.filename} is the registered file"))
    run.checks.append(
        Check(
            "sanitise",
            "reported",
            f"removed {extracted.invisible_characters} invisible characters, "
            f"{extracted.hidden_elements} hidden elements",
            {
                "invisible_characters": extracted.invisible_characters,
                "hidden_elements": extracted.hidden_elements,
            },
        )
    )

    scan, text = _scan_check(edition_id, extracted.text, review_dir)
    run.checks.append(scan)
    settings = settings_for(document, edition)
    run.checks.extend(_page_checks(text, settings.rules.page_header_lines))
    run.checks.append(_encoding_check(text))

    run.chunks = chunk_text(edition_id, text, "lines", settings)
    if not run.chunks:
        run.checks.append(Check("chunks", "refused", "no chunks: the edition has no text"))
        return run
    run.checks.append(Check("chunks", "pass", f"{len(run.chunks)} chunks"))
    counter, limit = token_counter or _model_token_counter()
    run.checks.append(_token_check(run.chunks, counter, limit))

    run.checks.append(
        _compared(
            "headings",
            quality.count_headings(text, settings),
            previous.headings if previous else None,
            quality.HEADINGS_FLOOR,
            "headings",
        )
    )
    if edition.course_tables:
        courses = extract_courses_from_text(edition_id, text)
        missing = sorted(quality.codes_in_text(text) - set(courses))
        check = _compared(
            "courses",
            len(courses),
            previous.courses if previous else None,
            1,
            "courses extracted",
        )
        run.checks.append(
            Check(
                check.name,
                check.outcome,
                f"{check.summary}; {len(missing)} codes in the text not extracted"
                + (f": {_list(missing)}" if missing else ""),
                {**check.measured, "codes_not_extracted": missing},
            )
        )
    return run


def measure_baseline(registry: Registry, edition_id: str, raw_dir: Path = RAW_DIR) -> Baseline:
    """The numbers a new edition is compared with, measured now on the previous edition's
    own file with today's code, so a parser change can't make the two differ."""
    edition = registry.edition(edition_id)
    text = extract_edition(registry, edition_id, raw_dir).text
    settings = settings_for(registry.document_of(edition_id), edition)
    courses = len(extract_courses_from_text(edition_id, text)) if edition.course_tables else None
    return Baseline(edition_id, quality.count_headings(text, settings), courses)


PREVIOUS_EDITION_SQL = """
    SELECT id FROM document_editions
    WHERE document_id = %s AND status = 'active' AND id <> %s
"""


def previous_edition(conn, document_id: str, edition_id: str) -> str | None:
    """The document's edition in force, if it is another one: what this edition would
    replace."""
    row = conn.execute(PREVIOUS_EDITION_SQL, (document_id, edition_id)).fetchone()
    return row[0] if row else None


def print_report(run: DryRun) -> None:
    against = run.previous or "none in force"
    print(f"== {run.edition_id} (previous edition: {against})")
    for check in run.checks:
        print(f"  {check.name}: {check.outcome}: {check.summary}")
    print(f"  verdict: {run.verdict}")


def main(argv: list[str] | None = None) -> int:
    from app.db.connection import get_owner_connection

    parser = argparse.ArgumentParser(description="Check editions before ingesting them.")
    parser.add_argument("editions", nargs="*")
    parser.add_argument("--all", action="store_true", help="every edition in the registry")
    parser.add_argument("--dry-run", action="store_true", help="check and report; write nothing")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("only --dry-run exists so far (writing a draft edition comes next)")
    registry = load_registry()
    edition_ids = [e.id for e in registry.editions] if args.all else args.editions
    if not edition_ids:
        parser.error("name an edition, or --all")

    conn = get_owner_connection()
    # The dry run only reads statuses: in a read-only transaction Postgres refuses any
    # write. Not in autocommit, where psycopg doesn't apply read_only (checked: a CREATE
    # went through).
    conn.autocommit = False
    conn.read_only = True
    try:
        previous = {e: previous_edition(conn, registry.document_of(e).id, e) for e in edition_ids}
    finally:
        conn.close()

    counter = _model_token_counter()
    all_passed = True
    for edition_id in edition_ids:
        before = previous[edition_id]
        baseline = measure_baseline(registry, before) if before else None
        run = dry_run(registry, edition_id, previous=baseline, token_counter=counter)
        print_report(run)
        all_passed = all_passed and run.verdict == "pass"
    print("Nothing changed.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
