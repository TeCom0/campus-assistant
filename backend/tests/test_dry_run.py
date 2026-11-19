"""The dry run (A2.4 step 5; CLAUDE.md, "A2.4 rule": check methods, items 1, 5 and 9).

Most tests build a small edition in a temporary folder (a PDF written by the fixture
generator, or an HTML page) and register it under a fixture document, with the file's
own sha256, so they need no data/raw, model or database. The token counter is a stand-in
(about four characters a token); the real tokenizer runs in the command and in the
real-data test at the end.
"""

import hashlib
import importlib.util
import io
import json
from dataclasses import asdict, replace
from pathlib import Path

import psycopg
import pytest
from edition_rows import add_edition
from pypdf import PdfReader, PdfWriter
from test_ingest_gates import FIXTURES, _fixture_registry

from app.db.connection import database_reachable, get_owner_connection, init_schema
from app.ingestion import ingest, quality
from app.ingestion.chunk import CHUNKS_PATH
from app.ingestion.clean import RAW_DIR
from app.ingestion.ingest import Baseline, dry_run, previous_edition
from app.registry import load_registry, registry_of

_spec = importlib.util.spec_from_file_location("make_pdf", FIXTURES / "make_fixture_pdf.py")
make_pdf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_pdf)

COUNTER = (lambda texts: [len(t) // 4 for t in texts], 512)
TEXT_LINE = "Students must register for courses during the registration period each term."
NO_DECISIONS = Path("no-decisions-here")


def _registered(tmp_path: Path, edition_id: str, content: bytes, **changes):
    """A registry where `edition_id` (a fixture edition) is this content, with its hash.
    Given course_tables, it takes the flag from the catalog: a registry has one."""
    path = tmp_path / f"{edition_id}.{_fixture_registry().edition(edition_id).format}"
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    documents = []
    for document in _fixture_registry().documents:
        editions = tuple(
            replace(e, sha256=digest, **changes)
            if e.id == edition_id
            else replace(e, course_tables=False)
            if changes.get("course_tables")
            else e
            for e in document.editions
        )
        documents.append(replace(document, editions=editions))
    return registry_of(tuple(documents))


def _pdf_run(tmp_path, pages: list[list[str]], **kwargs):
    registry = _registered(tmp_path, "fixture_finance_fees", make_pdf.build_pdf(pages))
    return dry_run(
        registry, "fixture_finance_fees", tmp_path, NO_DECISIONS, token_counter=COUNTER, **kwargs
    )


def _html_run(tmp_path, body: str, review_dir: Path = NO_DECISIONS, **kwargs):
    html = f"<html><body>{body}</body></html>".encode()
    registry = _registered(tmp_path, "fixture_dining_guide", html)
    kwargs.setdefault("token_counter", COUNTER)
    return dry_run(registry, "fixture_dining_guide", tmp_path, review_dir, **kwargs)


def _check(run, name):
    return next(check for check in run.checks if check.name == name)


def _page(n: int) -> list[str]:
    """A page of text whose lines are its own: identical lines on most pages would be
    taken for a running header."""
    return [f"Rule {n}.{line}: {TEXT_LINE}" for line in range(8)]


# --- The fixtures, and the order of a report -------------------------------------------


@pytest.mark.parametrize(
    "edition_id", ["fixture_dining_guide", "fixture_finance_fees", "fixture_engineering_handbook"]
)
def test_each_fixture_passes_the_dry_run(edition_id):
    run = dry_run(_fixture_registry(), edition_id, FIXTURES, NO_DECISIONS, token_counter=COUNTER)
    assert run.verdict == "pass", [c for c in run.checks if c.outcome != "pass"]
    assert run.chunks


def test_a_pdf_gets_page_checks_and_a_web_page_does_not():
    registry = _fixture_registry()
    pdf = dry_run(registry, "fixture_finance_fees", FIXTURES, NO_DECISIONS, token_counter=COUNTER)
    html = dry_run(registry, "fixture_dining_guide", FIXTURES, NO_DECISIONS, token_counter=COUNTER)
    names = ["near-empty pages", "table-like pages"]
    assert all(name in [c.name for c in pdf.checks] for name in names)
    assert not any(name in [c.name for c in html.checks] for name in names)


def test_a_gate_refusal_stops_the_report(tmp_path):
    registry = _registered(tmp_path, "fixture_dining_guide", b"<p>registered</p>")
    (tmp_path / "fixture_dining_guide.html").write_bytes(b"<p>changed since</p>")
    run = dry_run(registry, "fixture_dining_guide", tmp_path, NO_DECISIONS, token_counter=COUNTER)
    assert [c.name for c in run.checks] == ["gates"]
    assert run.verdict == "refused" and "sha256" in run.checks[0].summary
    assert run.chunks == []


def test_a_scan_refusal_still_runs_every_other_check(tmp_path):
    run = _html_run(tmp_path, f"<h1>Dining</h1><p>{TEXT_LINE} Lorem ipsum dolor.</p>")
    assert _check(run, "scan").outcome == "refused"
    assert run.verdict == "refused"
    assert {"encoding", "chunks", "tokens", "headings"} <= {c.name for c in run.checks}
    assert run.chunks


# --- Refusals (rule item 9) ----------------------------------------------------------------


def test_an_encrypted_pdf_is_refused(tmp_path):
    writer = PdfWriter(clone_from=PdfReader(FIXTURES / "fixture_finance_fees.pdf"))
    writer.encrypt(user_password="", owner_password="owner")  # opens with no password
    out = io.BytesIO()
    writer.write(out)
    registry = _registered(tmp_path, "fixture_finance_fees", out.getvalue())
    run = dry_run(registry, "fixture_finance_fees", tmp_path, NO_DECISIONS, token_counter=COUNTER)
    assert run.verdict == "refused"
    assert run.checks[0].summary.endswith("the PDF is encrypted")


def test_a_scanned_pdf_is_refused(tmp_path):
    # Pages with only a running header: text on the surface, empty underneath.
    header = ["Fixture University", "Page header 2026"]
    pages = [header + _page(1), header + _page(2), header, header, header]
    run = _pdf_run(tmp_path, pages)
    check = _check(run, "near-empty pages")
    assert check.outcome == "refused"
    assert check.measured["pages"] == [3, 4, 5]
    assert check.measured["header_lines"] == ["Fixture University", "Page header 2026"]


def test_near_empty_pages_up_to_the_limit_pass(tmp_path):
    # 1 of 20 is 5%, the limit: passes. 2 of 20 is over it.
    assert quality.NEAR_EMPTY_LIMIT == 0.05
    one = _pdf_run(tmp_path, [_page(n) for n in range(19)] + [[]])
    assert _check(one, "near-empty pages").outcome == "pass"
    two = _pdf_run(tmp_path, [_page(n) for n in range(18)] + [[], []])
    assert _check(two, "near-empty pages").outcome == "refused"


def test_a_page_header_alone_does_not_hide_an_empty_page():
    pages = [(1, ["Header", f"1 {TEXT_LINE}"]), (2, ["Header"]), (3, ["Header", f"3 {TEXT_LINE}"])]
    headers = quality.header_lines(pages, frozenset())
    assert headers == {"Header"}
    assert quality.near_empty_pages(pages, headers) == [2]
    assert quality.near_empty_pages([(1, ["x" * 49])], frozenset()) == [1]
    assert quality.near_empty_pages([(1, ["x" * 50])], frozenset()) == []


def test_a_single_page_has_no_header():
    pages = [(1, [TEXT_LINE])]
    assert quality.header_lines(pages, frozenset()) == frozenset()
    assert quality.near_empty_pages(pages, frozenset()) == []


def test_a_declared_page_header_is_used_as_is():
    pages = [(1, ["A", TEXT_LINE]), (2, ["A", TEXT_LINE])]
    assert quality.header_lines(pages, frozenset({"B"})) == {"B"}


def test_table_like_pages_follow_the_rule():
    short, long_ = "Fall 2026", TEXT_LINE
    assert quality.table_like_pages([(1, [short] * 9)]) == []  # under 10 short lines
    assert quality.table_like_pages([(1, [short] * 10 + [long_] * 7)]) == []  # 58.8%
    assert quality.table_like_pages([(1, [short] * 10 + [long_] * 6)]) == [1]  # 62.5%
    assert quality.table_like_pages([(1, ["one two three"] * 10)]) == [1]
    assert quality.table_like_pages([(1, ["one two three four"] * 10)]) == []


def test_a_table_heavy_pdf_is_refused(tmp_path):
    table_page = ["Course", "Credits", "Fall", "Spring"] * 3
    run = _pdf_run(tmp_path, [_page(n) for n in range(9)] + [table_page])  # 10%, over 3.2%
    assert _check(run, "table-like pages").outcome == "refused"
    passing = _pdf_run(tmp_path, [_page(n) for n in range(40)] + [table_page])  # 2.4%
    assert _check(passing, "table-like pages").outcome == "pass"


def test_broken_encoding_is_refused(tmp_path):
    assert quality.encoding_errors("caf� rÃ©sumÃ© â€™") == 4
    short = _html_run(tmp_path, f"<p>{TEXT_LINE * 20}</p><p>Ã</p>")  # 1 in ~1,600 chars
    assert _check(short, "encoding").outcome == "refused"
    long_ = _html_run(tmp_path, f"<p>{TEXT_LINE * 200}</p><p>Ã</p>")  # 1 in ~15,000
    assert _check(long_, "encoding").outcome == "pass"


def test_a_chunk_over_the_token_limit_is_refused(tmp_path):
    counter = (lambda texts: [600 if "Dining" in t else 10 for t in texts], 512)
    run = _html_run(tmp_path, f"<h1>Dining</h1><p>{TEXT_LINE}</p>", token_counter=counter)
    check = _check(run, "tokens")
    assert check.outcome == "refused" and check.measured["over"] == [0]
    assert "table" not in check.summary


def test_a_table_too_big_for_one_chunk_is_refused_and_named(tmp_path):
    rows = "".join(f"<tr><td>Meal {n}</td><td>{n * 10} MAD</td></tr>" for n in range(200))
    table = f"<table><tr><th>Meal</th><th>Price</th></tr>{rows}</table>"
    counter = (lambda texts: [len(t) // 4 for t in texts], 512)
    run = _html_run(tmp_path, f"<p>{TEXT_LINE}</p>{table}", token_counter=counter)
    check = _check(run, "tokens")
    assert check.outcome == "refused"
    assert "a table too big for one chunk" in check.summary


def test_an_edition_with_no_text_is_refused(tmp_path):
    run = _html_run(tmp_path, "")
    assert _check(run, "chunks").outcome == "refused"
    assert run.verdict == "refused"


# --- Holds and decisions -------------------------------------------------------------------


def test_an_undecided_hold_is_held_and_a_decision_passes_it(tmp_path):
    body = f"<p>{TEXT_LINE} Write to dining@fixtures.invalid for menus.</p>"
    assert _html_run(tmp_path, body).verdict == "held"
    review = tmp_path / "review"
    review.mkdir()
    (review / "fixture_dining_guide.toml").write_text(
        '[[decision]]\nkind = "email"\nvalue = "dining@fixtures.invalid"\n'
        'action = "allow"\nreason = "a service address"\nby = "test"\n',
        encoding="utf-8",
    )
    assert _html_run(tmp_path, body, review_dir=review).verdict == "pass"


def test_a_redaction_reaches_the_chunks(tmp_path):
    review = tmp_path / "review"
    review.mkdir()
    (review / "fixture_dining_guide.toml").write_text(
        '[[decision]]\nkind = "email"\nvalue = "*"\naction = "redact"\nreason = "r"\nby = "t"\n',
        encoding="utf-8",
    )
    run = _html_run(tmp_path, f"<p>{TEXT_LINE} Ask chef@fixtures.invalid.</p>", review_dir=review)
    assert run.verdict == "pass"
    text = "".join(chunk.text for chunk in run.chunks)
    assert "chef@" not in text and "[email removed]" in text


def test_an_unusable_decisions_file_refuses(tmp_path):
    review = tmp_path / "review"
    review.mkdir()
    (review / "fixture_dining_guide.toml").write_text("not = [toml", encoding="utf-8")
    run = _html_run(tmp_path, f"<p>{TEXT_LINE}</p>", review_dir=review)
    assert _check(run, "scan").outcome == "refused"


# --- Compared with the previous edition ----------------------------------------------------


def test_headings_are_reported_without_a_previous_edition(tmp_path):
    run = _html_run(tmp_path, f"<p>{TEXT_LINE}</p>")
    assert _check(run, "headings").outcome == "reported"
    assert run.verdict == "pass"


def test_headings_below_80_percent_of_the_previous_edition_are_refused(tmp_path):
    body = f"<p>{TEXT_LINE}</p>" + "".join(
        f"<h2>Meal Plan {name}</h2><p>{TEXT_LINE} {TEXT_LINE}</p>"
        for name in ("Alpha", "Beta", "Gamma", "Delta")
    )
    found = _check(_html_run(tmp_path, body), "headings").measured["found"]
    assert found == 4
    at_floor = _html_run(tmp_path, body, previous=Baseline("old", 5, None))  # 4 >= 4.0
    assert _check(at_floor, "headings").outcome == "pass"
    below = _html_run(tmp_path, body, previous=Baseline("old", 6, None))  # 4 < 4.8
    assert _check(below, "headings").outcome == "refused"


COURSE_PAGE = [
    "ACC 2301 Principles of Accounting (3 SCH)",
    TEXT_LINE,
    "Prerequisite: none",
    "ACC 2302 Managerial Accounting (3 SCH)",
    TEXT_LINE,
    "Prerequisite: ACC 2301 and FIN 1100",
] + _page(1)


def test_courses_are_counted_only_for_the_course_tables_edition(tmp_path):
    run = _pdf_run(tmp_path, [COURSE_PAGE])
    assert "courses" not in [c.name for c in run.checks]


def _course_run(tmp_path, previous=None):
    content = make_pdf.build_pdf([COURSE_PAGE])
    registry = _registered(tmp_path, "fixture_finance_fees", content, course_tables=True)
    return dry_run(
        registry,
        "fixture_finance_fees",
        tmp_path,
        NO_DECISIONS,
        previous=previous,
        token_counter=COUNTER,
    )


def test_fewer_courses_than_the_previous_edition_are_refused(tmp_path):
    reported = _check(_course_run(tmp_path), "courses")
    assert reported.outcome == "reported"
    assert reported.measured["found"] == 2
    assert reported.measured["codes_not_extracted"] == ["FIN 1100"]
    assert "FIN 1100" in reported.summary
    same = _check(_course_run(tmp_path, Baseline("old", 0, 2)), "courses")
    assert same.outcome == "pass"
    fewer = _check(_course_run(tmp_path, Baseline("old", 0, 3)), "courses")
    assert fewer.outcome == "refused"


# --- The edition it would replace (database) -----------------------------------------------


@pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")
def test_the_previous_edition_is_the_documents_other_active_one():
    conn = get_owner_connection()
    with conn.transaction(force_rollback=True):
        init_schema(conn)
        add_edition(conn, "test_old", document_id="test_doc", status="active")
        add_edition(conn, "test_new", document_id="test_doc", status="draft")
        add_edition(conn, "test_older", document_id="test_doc", status="superseded")
        assert previous_edition(conn, "test_doc", "test_new") == "test_old"
        assert previous_edition(conn, "test_doc", "test_old") is None  # itself in force
        conn.execute("UPDATE document_editions SET status = 'superseded' WHERE id = 'test_old'")
        assert previous_edition(conn, "test_doc", "test_new") is None
    conn.close()


@pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")
def test_the_command_reads_statuses_in_a_read_only_transaction(monkeypatch):
    seen = []

    def spy(conn, document_id, edition_id):
        # In a savepoint, so the refusal doesn't abort the reads that follow it.
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction), conn.transaction():
            conn.execute("CREATE TEMP TABLE should_not_exist (x int)")
        seen.append(edition_id)

    monkeypatch.setattr(ingest, "previous_edition", spy)
    monkeypatch.setattr(ingest, "dry_run", lambda *a, **k: ingest.DryRun(a[1], None, [], []))
    monkeypatch.setattr(ingest, "_model_token_counter", lambda: COUNTER)
    assert ingest.main(["prestigious_scholarships", "--dry-run"]) == 0
    assert seen == ["prestigious_scholarships"]


# --- Today's editions (rule items 1 and 5) -------------------------------------------------


def test_todays_editions_chunk_byte_identically_and_only_lorem_ipsum_is_refused():
    # data/raw is gitignored, so this runs where the files are, not in CI.
    if not RAW_DIR.exists() or not CHUNKS_PATH.exists():
        pytest.skip("data/raw or chunks.jsonl not present")
    registry = load_registry()
    lines, verdicts = [], {}
    for edition in sorted(registry.editions, key=lambda e: e.id):
        run = dry_run(registry, edition.id, token_counter=COUNTER)
        verdicts[edition.id] = run
        lines += [json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in run.chunks]
    assert lines == CHUNKS_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(lines) == 1161

    refused = {
        edition_id: [c for c in run.checks if c.outcome not in ("pass", "reported")]
        for edition_id, run in verdicts.items()
        if run.verdict != "pass"
    }
    assert list(refused) == ["graduate_scholarships"]
    [scan] = refused["graduate_scholarships"]
    assert scan.name == "scan" and scan.measured["refusals"] == [
        "boilerplate 'Lorem Ipsum' at line 4"
    ]
