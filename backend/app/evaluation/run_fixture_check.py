"""A2.4's fixture check on a scratch database (CLAUDE.md, "A2.4 rule", items 6-8, and
"Sub-step 7 method"). Local only: it reads the test fixtures, and touches no database but
`campus_scratch`, which it creates.

    python -m app.evaluation.run_fixture_check setup
        In the normal environment. Drops and creates campus_scratch on the same server,
        migrates it, copies the configured (dev) database's five content tables into it row
        for row, and compares the two content fingerprints. The dev database is only read.

    $env:POSTGRES_DB = "campus_scratch"; python -m app.evaluation.run_fixture_check run --out <file>
        Refuses unless POSTGRES_DB is campus_scratch. Syncs the fixture documents as drafts,
        then for dining, finance, engineering in turn: dry run, write_draft with real
        embeddings, activate, snapshot. Then items 6 and 7 at S3, and item 8 by withdrawing
        them in reverse order, each compared exactly with the snapshot before it was ingested.

Embeddings only: 0 LLM tokens. Exit code 0 only if every item passed.
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import config
from app.evaluation.run_retrieval_eval import contains_anchor, load_eval_set, rank_of_first_match
from app.retrieval.hybrid_search import search_hybrid, search_hybrid_multi
from app.retrieval.keyword_search import search_keyword
from app.retrieval.vector_search import search_vector

SCRATCH_DB = "campus_scratch"
BACKEND = Path(__file__).resolve().parents[2]
FIXTURES = BACKEND / "tests" / "fixtures" / "ingestion"
FIXTURE_REGISTRY = FIXTURES / "fixture_registry.toml"
FIXTURE_QUESTIONS = FIXTURES / "fixture_questions.json"
FIXTURE_HOST = "fixtures.invalid"
FINGERPRINT_SQL = BACKEND.parent / "deploy" / "backup" / "fingerprint.sql"
# In this order: each one is ingested and activated after the ones before it, and
# withdrawn in reverse, so each is the last one ingested of those in force (method, item 8).
FIXTURE_EDITIONS = ("fixture_dining_guide", "fixture_finance_fees", "fixture_engineering_handbook")
# Foreign keys first: editions need documents, chunks and courses need editions.
CONTENT_TABLES = (
    "documents",
    "document_editions",
    "document_chunks",
    "courses",
    "course_prerequisites",
)
TOP_K = 10
ACTIVATED_BY = "A2.4 step 7 fixture check (scratch database)"

METHODS = {
    "vector": lambda q, k: search_vector(q["question"], k),
    "keyword": lambda q, k: search_keyword(q["question"], k),
    "hybrid": lambda q, k: search_hybrid(q["question"], k),
    "hybrid + English": lambda q, k: search_hybrid_multi(
        [q["question"], q.get("question_en", q["question"])], k
    ),
}


# --- setup: the scratch database -----------------------------------------------------------


def _owner(dbname: str) -> psycopg.Connection:
    return psycopg.connect(
        make_conninfo(config.owner_database_url(), dbname=dbname), autocommit=True
    )


def fingerprint(conn: psycopg.Connection) -> list[tuple]:
    return conn.execute(FINGERPRINT_SQL.read_text(encoding="utf-8")).fetchall()


def _columns(conn: psycopg.Connection, table: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            # Not generated columns (text_search): COPY can't write them, and Postgres
            # computes them again from the copied text.
            "WHERE table_schema = 'public' AND table_name = %s AND is_generated = 'NEVER' "
            "ORDER BY ordinal_position",
            (table,),
        )
    ]


def copy_tables(source: psycopg.Connection, target: psycopg.Connection) -> None:
    """Every row of the content tables, binary COPY, vectors included: nothing re-embedded."""
    with target.transaction():
        for table in CONTENT_TABLES:
            columns = _columns(target, table)
            if columns != _columns(source, table):
                raise SystemExit(f"{table}: the two databases' columns differ. Nothing copied.")
            names = sql.SQL(", ").join(map(sql.Identifier, columns))
            out = sql.SQL("COPY {} ({}) TO STDOUT (FORMAT binary)").format(
                sql.Identifier(table), names
            )
            into = sql.SQL("COPY {} ({}) FROM STDIN (FORMAT binary)").format(
                sql.Identifier(table), names
            )
            with source.cursor().copy(out) as reading, target.cursor().copy(into) as writing:
                for data in reading:
                    writing.write(data)


def setup() -> int:
    from app.db.migrate import migrate

    source_db = config.POSTGRES_DB
    if source_db == SCRATCH_DB:
        print(f"setup copies from the configured database, which here is {SCRATCH_DB} itself.")
        return 2
    maintenance = _owner("postgres")
    maintenance.execute(
        sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(SCRATCH_DB))
    )
    maintenance.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(SCRATCH_DB)))
    maintenance.close()

    scratch, source = _owner(SCRATCH_DB), _owner(source_db)
    # The dev database is only read: a read-only transaction, where Postgres refuses any
    # write. Not autocommit, where psycopg ignores read_only (A2.4 step 5a).
    source.autocommit = False
    source.read_only = True
    try:
        migrate(scratch, config.CAMPUS_API_PASSWORD)
        copy_tables(source, scratch)
        before, after = fingerprint(source), fingerprint(scratch)
    finally:
        scratch.close()
        source.close()
    for row in after:
        print(f"  {SCRATCH_DB}: {row[0]}: {row[1]} rows, md5 {row[2]}")
    if before != after:
        print("FAILED: the scratch database's content fingerprint differs from the source's")
        return 1
    print(f"{SCRATCH_DB} created, migrated and filled; its content fingerprint is the source's")
    return 0


# --- run: the fixtures --------------------------------------------------------------------


def _score(result) -> float:
    for name in ("rrf_score", "distance", "score"):
        if hasattr(result, name):
            return getattr(result, name)
    raise AttributeError(type(result).__name__)


def snapshot(questions: list[dict], conn: psycopg.Connection) -> dict:
    """Every search the method names, and every edition's chunk count."""
    searches = {}
    for q in questions:
        for method, search in METHODS.items():
            results = search(q, TOP_K)
            searches[f"{q['id']} | {method}"] = {
                "results": [(r.source, r.chunk_index, repr(_score(r))) for r in results],
                "rank": rank_of_first_match(results, q["expected"]),
            }
    counts = dict(
        conn.execute(
            "SELECT source, count(*) FROM document_chunks GROUP BY source ORDER BY source"
        ).fetchall()
    )
    return {"searches": searches, "chunk_counts": counts}


def fixture_registry():
    from app.registry import load_registry, read_documents, registry_of

    fixtures = read_documents(FIXTURE_REGISTRY, allowed_host=FIXTURE_HOST)
    return registry_of(load_registry().documents + fixtures)


def ingest_fixture(conn, registry, edition_id: str) -> list[str]:
    from app.config import EMBEDDING_MODEL_NAME
    from app.embeddings import embed_passages
    from app.ingestion.ingest import _model_token_counter, dry_run, write_draft
    from app.ingestion.scan import REVIEW_DIR
    from app.registry import activate

    run = dry_run(registry, edition_id, FIXTURES, REVIEW_DIR, token_counter=_model_token_counter())
    lines = [f"  {c.name}: {c.outcome}: {c.summary}" for c in run.checks]
    if run.verdict != "pass":
        raise SystemExit(f"{edition_id}: dry run {run.verdict}\n" + "\n".join(lines))
    vectors = embed_passages([chunk.text for chunk in run.chunks])
    write_draft(conn, registry, run, vectors, EMBEDDING_MODEL_NAME)
    activation = activate(conn, edition_id, activated_by=ACTIVATED_BY)
    lines.append(f"  written and activated: {activation.chunks} chunks")
    return lines


def withdraw(conn, edition_id: str) -> None:
    """Scratch only, and exactly one row: the withdraw command itself belongs to A2.5."""
    changed = conn.execute(
        "UPDATE document_editions SET status = 'withdrawn' WHERE id = %s AND status = 'active'",
        (edition_id,),
    ).rowcount
    if changed != 1:
        raise SystemExit(f"withdrawing {edition_id} changed {changed} rows, not 1")


def attribution(questions: list[dict], card_titles: dict[str, str], registry) -> list[dict]:
    """Item 6: the anchor in hybrid + English's top 5, from the expected edition, which the
    API would show with that edition's card title."""
    rows = []
    for q in questions:
        results = METHODS["hybrid + English"](q, 5)
        rank = rank_of_first_match(results, q["expected"])
        hit = results[rank - 1] if rank else None
        expected_source = q["expected"][0]["source"]
        title = card_titles.get(hit.source) if hit else None
        rows.append(
            {
                "id": q["id"],
                "rank": rank,
                "source": hit.source if hit else None,
                "card_title": title,
                "passed": bool(
                    hit
                    and hit.source == expected_source
                    and any(contains_anchor(hit.source, hit.text, e) for e in q["expected"])
                    and title == registry.edition(expected_source).card_title
                ),
            }
        )
    return rows


def coexistence(real: list[dict], s0: dict, s3: dict) -> tuple[list[str], list[str]]:
    """Item 7: hits at 3 or 5 lost from S0 to S3 (failures), and every rank change (reported)."""
    lost, changed = [], []
    for q in real:
        for method in METHODS:
            key = f"{q['id']} | {method}"
            before, after = s0["searches"][key]["rank"], s3["searches"][key]["rank"]
            if before != after:
                changed.append(f"{key}: rank {before or '-'} -> {after or '-'}")
            for k in (3, 5):
                if before is not None and before <= k and (after is None or after > k):
                    lost.append(f"{key}: hit@{k} lost (rank {before} -> {after or '-'})")
    return lost, changed


def differences(before: dict, after: dict, withdrawn: str) -> list[str]:
    """Item 8: what differs from the snapshot before `withdrawn` was ingested."""
    found = [
        key
        for key in before["searches"]
        if before["searches"][key]["results"] != after["searches"][key]["results"]
    ]
    counts_before = {s: n for s, n in before["chunk_counts"].items() if s != withdrawn}
    counts_after = {s: n for s, n in after["chunk_counts"].items() if s != withdrawn}
    if counts_before != counts_after:
        found.append(f"chunk counts: {counts_before} -> {counts_after}")
    return found


def run(out: Path) -> int:
    from app.db.connection import get_owner_connection
    from app.registry import sync
    from app.sources import sources_from_rows

    if config.POSTGRES_DB != SCRATCH_DB:
        print(f"run refuses: POSTGRES_DB must be {SCRATCH_DB}. Nothing changed.")
        return 2
    report: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        report.append(line)

    real = load_eval_set()
    fixture_questions = json.loads(FIXTURE_QUESTIONS.read_text(encoding="utf-8"))
    questions = real + fixture_questions
    registry = fixture_registry()
    conn = get_owner_connection(register_vector_type=True)
    sync(conn, registry)

    snapshots = [snapshot(questions, conn)]
    say(
        f"S0: {len(snapshots[0]['searches'])} searches, chunk counts {snapshots[0]['chunk_counts']}"
    )
    for n, edition_id in enumerate(FIXTURE_EDITIONS, start=1):
        say(f"== ingest {edition_id}")
        for line in ingest_fixture(conn, registry, edition_id):
            say(line)
        snapshots.append(snapshot(questions, conn))
        say(f"S{n}: chunk counts {snapshots[n]['chunk_counts']}")

    from app.registry import read_source_rows

    card_titles = {k: v.title for k, v in sources_from_rows(read_source_rows(conn)).items()}
    say("\n== item 6, attribution at S3 (hybrid + English, top 5)")
    rows = attribution(fixture_questions, card_titles, registry)
    for row in rows:
        say(
            f"  {'pass' if row['passed'] else 'FAIL'} {row['id']:<38} rank {row['rank'] or '-'} "
            f"{row['source']} | {row['card_title']}"
        )
    item6 = all(row["passed"] for row in rows)

    say("\n== item 7, coexistence: S3 against S0, the 14 real questions")
    lost, changed = coexistence(real, snapshots[0], snapshots[3])
    for line in lost:
        say(f"  FAIL {line}")
    for line in changed:
        say(f"  rank change: {line}")
    say(f"  {len(lost)} hits lost, {len(changed)} rank changes")
    item7 = not lost

    say("\n== item 8, withdrawal in reverse order")
    item8 = True
    for n in range(len(FIXTURE_EDITIONS), 0, -1):
        edition_id = FIXTURE_EDITIONS[n - 1]
        withdraw(conn, edition_id)
        diffs = differences(snapshots[n - 1], snapshot(questions, conn), edition_id)
        item8 = item8 and not diffs
        say(
            f"  withdrew {edition_id}: against S{n - 1}, "
            + ("every search and chunk count identical" if not diffs else f"{len(diffs)} differ")
        )
        for diff in diffs[:20]:
            say(f"    {diff}")
    conn.close()

    say(
        f"\nitem 6 {'passed' if item6 else 'FAILED'}, item 7 {'passed' if item7 else 'FAILED'}, "
        f"item 8 {'passed' if item8 else 'FAILED'} (the A0 baseline comparison runs separately)"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"written: {out}")
    return 0 if item6 and item7 and item8 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A2.4's fixture check on campus_scratch.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return setup() if args.command == "setup" else run(args.out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
