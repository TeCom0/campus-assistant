"""Writing an edition (A2.4 step 5b): parser_version, quality_report and draft-only ingest.

An edition that passes its dry run is written as a draft, in one transaction: chunks,
courses for the course-tables edition, parser_version and quality_report. An edition in
force (or superseded, or withdrawn) is never written in place, nor is one whose dry run
didn't pass, or whose row isn't the registered file. A failure part-way leaves everything
as it was.

The database tests run as the owner in a transaction that is always rolled back, with the
fixture editions and a stand-in vector (no model). Skipped when Postgres isn't reachable.
"""

import hashlib
import json
from dataclasses import asdict

import pytest
from edition_rows import add_edition
from test_dry_run import (
    COUNTER,
    COURSE_PAGE,
    NO_DECISIONS,
    TEXT_LINE,
    _course_run,
    _html_run,
    _registered,
    make_pdf,
)
from test_ingest_gates import FIXTURES, _fixture_registry

from app.config import EMBEDDING_DIM
from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.ingestion import ingest
from app.ingestion.ingest import (
    PARSER_REVISION,
    Check,
    DryRun,
    WriteRefused,
    dry_run,
    parser_version,
    write_draft,
)

MODEL = "test-model"
VECTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
FIXTURE_EDITIONS = ("fixture_dining_guide", "fixture_engineering_handbook", "fixture_finance_fees")

needs_db = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")


# --- parser_version (no database) -----------------------------------------------------------

# The fixtures' chunks under each parser revision. A change to loading, sanitising, scanning
# or chunking that changes them fails here until PARSER_REVISION is bumped and its
# fingerprint added: rows written before and after then carry different versions.
CHUNKS_FINGERPRINT = {
    1: "352396a575c72a0c67047e6843f597aa509f7cc0ec7714eedc0c11233f3397c6",
}


def test_the_fixtures_chunks_are_pinned_to_the_parser_revision():
    registry = _fixture_registry()
    lines = []
    for edition_id in FIXTURE_EDITIONS:
        run = dry_run(registry, edition_id, FIXTURES, NO_DECISIONS, token_counter=COUNTER)
        lines += [json.dumps(asdict(c), ensure_ascii=False) for c in run.chunks]
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    assert CHUNKS_FINGERPRINT.get(PARSER_REVISION) == digest, (
        "the fixtures' chunks changed: bump PARSER_REVISION in app/ingestion/ingest.py and "
        f"add {{{PARSER_REVISION + 1}: {digest!r}}} here"
    )


def test_the_parser_version_names_the_revision_and_the_extractors():
    import bs4
    import pypdf

    assert parser_version() == (
        f"ingest-{PARSER_REVISION} pypdf-{pypdf.__version__} bs4-{bs4.__version__}"
    )


# --- Writing a draft (database) ------------------------------------------------------------


@pytest.fixture
def conn():
    connection = get_owner_connection(register_vector_type=True)
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        yield connection
    connection.close()


def _register(conn, registry, edition_id: str, status: str = "draft") -> None:
    """The edition's row as `registry sync` writes it: the registry's sha256."""
    add_edition(conn, edition_id, status=status)
    conn.execute(
        "UPDATE document_editions SET sha256 = %s WHERE id = %s",
        (registry.edition(edition_id).sha256, edition_id),
    )


def _fixture_run(edition_id: str = "fixture_dining_guide"):
    registry = _fixture_registry()
    return registry, dry_run(registry, edition_id, FIXTURES, NO_DECISIONS, token_counter=COUNTER)


def _write(conn, registry, run) -> None:
    write_draft(conn, registry, run, [VECTOR] * len(run.chunks), MODEL)


def _row(conn, edition_id: str) -> dict:
    status, version, report = conn.execute(
        "SELECT status, parser_version, quality_report FROM document_editions WHERE id = %s",
        (edition_id,),
    ).fetchone()
    chunks = conn.execute(
        "SELECT chunk_index, text FROM document_chunks WHERE source = %s ORDER BY chunk_index",
        (edition_id,),
    ).fetchall()
    courses = conn.execute(
        "SELECT count(*) FROM courses WHERE source = %s", (edition_id,)
    ).fetchone()[0]
    edges = conn.execute(
        "SELECT count(*) FROM course_prerequisites WHERE source = %s", (edition_id,)
    ).fetchone()[0]
    return {
        "status": status,
        "version": version,
        "report": report,
        "chunks": chunks,
        "courses": courses,
        "edges": edges,
    }


def _stale_chunks(conn, edition_id: str, n: int) -> None:
    for index in range(n):
        conn.execute(
            "INSERT INTO document_chunks (source, chunk_index, text, language, model_name, "
            "embedding) VALUES (%s, %s, 'stale', 'en', %s, %s::vector)",
            (edition_id, index, MODEL, str(VECTOR)),
        )


@needs_db
def test_a_passing_draft_is_written_with_its_version_and_report(conn):
    registry, run = _fixture_run()
    _register(conn, registry, run.edition_id)
    _write(conn, registry, run)

    row = _row(conn, run.edition_id)
    assert row["status"] == "draft"  # written, not put in force
    assert [text for _, text in row["chunks"]] == [c.text for c in run.chunks]
    assert row["version"] == parser_version()
    report = row["report"]
    assert report["verdict"] == "pass" and report["chunks"] == len(run.chunks)
    assert report["parser_version"] == parser_version()
    assert [c["name"] for c in report["checks"]] == [c.name for c in run.checks]
    assert report["checks"] == json.loads(json.dumps([asdict(c) for c in run.checks]))


@needs_db
def test_writing_a_draft_again_replaces_its_rows(conn):
    registry, run = _fixture_run()
    _register(conn, registry, run.edition_id)
    _stale_chunks(conn, run.edition_id, len(run.chunks) + 5)
    _write(conn, registry, run)
    assert [text for _, text in _row(conn, run.edition_id)["chunks"]] == [
        c.text for c in run.chunks
    ]


@needs_db
@pytest.mark.parametrize("status", ["active", "superseded", "withdrawn"])
def test_an_edition_that_is_not_a_draft_is_never_written(conn, status):
    registry, run = _fixture_run()
    _register(conn, registry, run.edition_id, status=status)
    _stale_chunks(conn, run.edition_id, 2)
    before = _row(conn, run.edition_id)
    with pytest.raises(WriteRefused, match=f"it is {status}"):
        _write(conn, registry, run)
    assert _row(conn, run.edition_id) == before


@needs_db
def test_an_edition_missing_from_the_table_is_refused(conn):
    registry, run = _fixture_run()
    with pytest.raises(WriteRefused, match="registry sync"):
        _write(conn, registry, run)
    assert (
        conn.execute(
            "SELECT count(*) FROM document_chunks WHERE source = %s", (run.edition_id,)
        ).fetchone()[0]
        == 0
    )


@needs_db
def test_a_row_for_another_file_is_refused(conn):
    registry, run = _fixture_run()
    _register(conn, registry, run.edition_id)
    conn.execute(
        "UPDATE document_editions SET sha256 = 'an older file' WHERE id = %s", (run.edition_id,)
    )
    before = _row(conn, run.edition_id)
    with pytest.raises(WriteRefused, match="sha256"):
        _write(conn, registry, run)
    assert _row(conn, run.edition_id) == before


@needs_db
def test_a_dry_run_that_did_not_pass_is_never_written(conn, tmp_path):
    run = _html_run(tmp_path, f"<h1>Dining</h1><p>{TEXT_LINE} Lorem ipsum dolor.</p>")
    assert run.verdict == "refused"
    registry = _fixture_registry()
    _register(conn, registry, run.edition_id)
    before = _row(conn, run.edition_id)
    with pytest.raises(WriteRefused, match="verdict is refused"):
        _write(conn, registry, run)
    assert _row(conn, run.edition_id) == before


def _course_edition(tmp_path):
    """A course-tables edition of two courses (test_dry_run's COURSE_PAGE)."""
    content = make_pdf.build_pdf([COURSE_PAGE])
    registry = _registered(tmp_path, "fixture_finance_fees", content, course_tables=True)
    return registry, _course_run(tmp_path)


@needs_db
def test_the_course_tables_edition_writes_its_courses_and_edges(conn, tmp_path):
    registry, run = _course_edition(tmp_path)
    assert run.verdict == "pass" and len(run.courses) == 2
    _register(conn, registry, run.edition_id)
    _write(conn, registry, run)
    row = _row(conn, run.edition_id)
    assert row["courses"] == 2 and row["edges"] == 2  # ACC 2301 and FIN 1100


@needs_db
def test_a_course_tables_edition_without_courses_is_refused(conn, tmp_path):
    registry, run = _course_edition(tmp_path)
    run.courses = {}
    _register(conn, registry, run.edition_id)
    before = _row(conn, run.edition_id)
    with pytest.raises(WriteRefused, match="no courses"):
        _write(conn, registry, run)
    assert _row(conn, run.edition_id) == before


@needs_db
def test_a_failure_part_way_leaves_the_edition_as_it_was(conn, tmp_path, monkeypatch):
    registry, run = _course_edition(tmp_path)
    _register(conn, registry, run.edition_id)
    _stale_chunks(conn, run.edition_id, 3)
    before = _row(conn, run.edition_id)

    def fail(*_args):  # after the chunks were replaced, before the courses
        raise RuntimeError("injected")

    monkeypatch.setattr(ingest, "replace_course_rows", fail)
    with pytest.raises(RuntimeError, match="injected"):
        _write(conn, registry, run)
    assert _row(conn, run.edition_id) == before


# --- The command -----------------------------------------------------------------------------


@needs_db
def test_the_command_refuses_an_edition_in_force_before_embedding(monkeypatch):
    # prestigious_scholarships is active once the registry is synced, and missing from an
    # unsynced database: refused either way, before the model loads.
    passing = Check("gates", "pass", "")
    monkeypatch.setattr(ingest, "dry_run", lambda *a, **k: DryRun(a[1], None, [passing], []))
    monkeypatch.setattr(ingest, "_model_token_counter", lambda: COUNTER)

    def no_embedding(_chunks):
        raise AssertionError("embedded an edition that can't be written")

    monkeypatch.setattr(ingest, "_embed", no_embedding)
    monkeypatch.setattr(ingest, "write_draft", no_embedding)
    assert ingest.main(["prestigious_scholarships"]) == 1


@needs_db
def test_a_dry_run_writes_nothing_even_when_it_passes(monkeypatch):
    passing = Check("gates", "pass", "")
    monkeypatch.setattr(ingest, "dry_run", lambda *a, **k: DryRun(a[1], None, [passing], []))
    monkeypatch.setattr(ingest, "_model_token_counter", lambda: COUNTER)

    def no_write(*_args):
        raise AssertionError("a dry run wrote")

    monkeypatch.setattr(ingest, "_embed", no_write)
    monkeypatch.setattr(ingest, "write_draft", no_write)
    assert ingest.main(["prestigious_scholarships", "--dry-run"]) == 0
