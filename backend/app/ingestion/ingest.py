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
With --dry-run nothing is written, and the exit code is 0 only if every edition passed.

    python -m app.ingestion.ingest <edition id> [<edition id> ...]

Without --dry-run, an edition that passes is written as a draft (write_draft): its
chunks, embedded; its courses and prerequisite edges if it is the course-tables edition;
its parser_version and quality_report. One transaction, and only while the edition is a
draft in document_editions with the registry's sha256: an edition in force is never
replaced in place (A2.4 rule, decision 3). Students see it only after
`python -m app.registry activate`.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import bs4
import pypdf
from psycopg.types.json import Jsonb

from app.ingestion import quality
from app.ingestion.chunk import Chunk, chunk_text, settings_for
from app.ingestion.clean import RAW_DIR
from app.ingestion.courses import (
    extract_courses_from_text,
    extract_prerequisite_edges,
    replace_course_rows,
)
from app.ingestion.gates import IngestRefused, extract_edition
from app.ingestion.scan import REVIEW_DIR, DecisionsError, load_decisions, review
from app.ingestion.store import chunk_row, replace_rows
from app.registry import Registry, load_registry

OUTCOMES = ("pass", "reported", "held", "refused")

# Bump when a change to loading, sanitising, scanning or chunking changes what an
# edition's chunks are. tests/test_ingest_write.py pins the fixtures' chunks to this
# number, so a change that forgets the bump fails there.
PARSER_REVISION = 1


def parser_version() -> str:
    """What produced an edition's rows: this code's revision and the extractors' versions
    (a pypdf upgrade can change the text of a PDF without any change here)."""
    return f"ingest-{PARSER_REVISION} pypdf-{pypdf.__version__} bs4-{bs4.__version__}"


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
    # The course-tables edition's courses, from the same text as the chunks (after
    # redaction), so what is written is what was checked.
    courses: dict[str, dict] = field(default_factory=dict)

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
        courses = run.courses = extract_courses_from_text(edition_id, text)
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


EDITION_ROW_SQL = "SELECT status, sha256 FROM document_editions WHERE id = %s"


class WriteRefused(Exception):
    """An edition that may not be written; nothing was changed."""


def quality_report(run: DryRun) -> dict:
    """The dry run as stored with the edition: what was checked, and against what."""
    return {
        "parser_version": parser_version(),
        "verdict": run.verdict,
        "previous_edition": run.previous,
        "chunks": len(run.chunks),
        "checks": [asdict(check) for check in run.checks],
    }


def refusal_before_writing(status: str | None, sha256: str | None, registry_sha256: str) -> str:
    """Why an edition's row forbids writing it, or "" if it is a draft of the registered
    file. Checked before embedding (to fail fast) and again under the row lock."""
    if status is None:
        return "it isn't in document_editions: run `python -m app.registry sync` first"
    if status != "draft":
        return (
            f"it is {status}, and only a draft is written: a new file is a new edition "
            "(A2.4 rule, decision 3)"
        )
    if sha256 != registry_sha256:
        return "its sha256 in document_editions isn't the registry's: run sync first"
    return ""


def write_draft(conn, registry: Registry, run: DryRun, vectors: list, model_name: str) -> None:
    """Write a passing dry run's edition as a draft: chunks with their vectors, courses and
    edges for the course-tables edition, parser_version and quality_report.

    One transaction, after locking the edition's row: `activate` can't put it in force
    halfway through, and if any write fails, every one is undone. The draft's earlier rows,
    if it was ingested before, are replaced. Raises WriteRefused, changing nothing.
    """
    edition = registry.edition(run.edition_id)
    if run.verdict != "pass":
        raise WriteRefused(f"{run.edition_id}: the dry run's verdict is {run.verdict}")
    if edition.course_tables and not run.courses:
        raise WriteRefused(f"{run.edition_id}: the course-tables edition has no courses")
    courses = run.courses if edition.course_tables else {}
    edges = extract_prerequisite_edges(courses)
    rows = [
        chunk_row(asdict(chunk), vector, model_name)
        for chunk, vector in zip(run.chunks, vectors, strict=True)
    ]
    with conn.transaction():
        row = conn.execute(EDITION_ROW_SQL + " FOR UPDATE", (run.edition_id,)).fetchone()
        refusal = refusal_before_writing(*(row or (None, None)), edition.sha256)
        if refusal:
            raise WriteRefused(f"{run.edition_id}: {refusal}")
        replace_rows(conn, rows, model_name)
        if courses:
            replace_course_rows(conn, run.edition_id, courses, edges)
        conn.execute(
            "UPDATE document_editions SET parser_version = %s, quality_report = %s WHERE id = %s",
            (parser_version(), Jsonb(quality_report(run)), run.edition_id),
        )


WRITTEN_SQL = """
    SELECT e.status, e.parser_version, e.quality_report ->> 'verdict',
           (SELECT count(*) FROM document_chunks c WHERE c.source = e.id AND c.model_name = %s),
           (SELECT count(*) FROM courses c WHERE c.source = e.id),
           (SELECT count(*) FROM course_prerequisites p WHERE p.source = e.id)
    FROM document_editions e WHERE e.id = %s
"""


def print_written(conn, edition_id: str, model_name: str) -> None:
    """Proof, read back from the tables (CLAUDE.md: a clean exit proves nothing)."""
    status, version, verdict, chunks, courses, edges = conn.execute(
        WRITTEN_SQL, (model_name, edition_id)
    ).fetchone()
    print(
        f"  written: {edition_id} is {status}, {chunks} chunks, {courses} courses, {edges} "
        f"prerequisite edges; parser {version}; stored verdict {verdict}"
    )


def print_report(run: DryRun) -> None:
    against = run.previous or "none in force"
    print(f"== {run.edition_id} (previous edition: {against})")
    for check in run.checks:
        print(f"  {check.name}: {check.outcome}: {check.summary}")
    print(f"  verdict: {run.verdict}")


def _embed(chunks: list[Chunk]) -> list:
    from app.embeddings import embed_passages

    return embed_passages([chunk.text for chunk in chunks])


def main(argv: list[str] | None = None) -> int:
    from app.config import EMBEDDING_MODEL_NAME
    from app.db.connection import get_owner_connection

    parser = argparse.ArgumentParser(description="Check editions, and write those that pass.")
    parser.add_argument("editions", nargs="*")
    parser.add_argument("--all", action="store_true", help="every edition in the registry")
    parser.add_argument("--dry-run", action="store_true", help="check and report; write nothing")
    args = parser.parse_args(argv)
    registry = load_registry()
    edition_ids = [e.id for e in registry.editions] if args.all else args.editions
    if not edition_ids:
        parser.error("name an edition, or --all")

    conn = get_owner_connection()
    # Statuses are read in a read-only transaction, where Postgres refuses any write. Not
    # in autocommit, where psycopg doesn't apply read_only (checked: a CREATE went through).
    conn.autocommit = False
    conn.read_only = True
    try:
        previous = {e: previous_edition(conn, registry.document_of(e).id, e) for e in edition_ids}
        rows = {e: conn.execute(EDITION_ROW_SQL, (e,)).fetchone() for e in edition_ids}
    finally:
        conn.close()

    counter = _model_token_counter()
    all_passed = True
    for edition_id in edition_ids:
        before = previous[edition_id]
        baseline = measure_baseline(registry, before) if before else None
        run = dry_run(registry, edition_id, previous=baseline, token_counter=counter)
        print_report(run)
        if args.dry_run or run.verdict != "pass":
            all_passed = all_passed and run.verdict == "pass"
            continue
        refusal = refusal_before_writing(
            *(rows[edition_id] or (None, None)), registry.edition(edition_id).sha256
        )
        if refusal:  # checked again under the lock; here so as not to embed for nothing
            print(f"  not written: {refusal}")
            all_passed = False
            continue
        vectors = _embed(run.chunks)
        conn = get_owner_connection(register_vector_type=True)
        try:
            write_draft(conn, registry, run, vectors, EMBEDDING_MODEL_NAME)
            print_written(conn, edition_id, EMBEDDING_MODEL_NAME)
        except WriteRefused as e:
            print(f"  not written: {e}")
            all_passed = False
        finally:
            conn.close()
    if args.dry_run:
        print("Nothing changed.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
