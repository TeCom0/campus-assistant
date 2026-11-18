"""Registry-driven ingestion and its gates (A2.4 step 2; CLAUDE.md, "A2.4 rule").

Runs on the fixture documents, which have their own registry file on the reserved
.invalid domain, so none of this needs data/raw, a database or the network.
"""

import hashlib
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from app.ingestion import gates
from app.ingestion.chunk import (
    CATALOG_RULES,
    LAYOUT_RULES,
    PLAIN_RULES,
    ChunkSettings,
    assign_sections,
    chunk_text,
    settings_for,
)
from app.ingestion.clean import clean_all, main
from app.ingestion.gates import IngestRefused, check_edition, ignored_files, load_edition_text
from app.registry import LAYOUTS, RegistryError, load_registry, read_documents, registry_of

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"
FIXTURE_REGISTRY = FIXTURES / "fixture_registry.toml"
FIXTURE_HOST = "fixtures.invalid"


def _fixture_registry():
    """The real registry with the fixture documents added: the fixtures alone have no
    course-tables edition, which a whole registry needs."""
    fixtures = read_documents(FIXTURE_REGISTRY, allowed_host=FIXTURE_HOST)
    return registry_of(load_registry().documents + fixtures)


def _fixture(edition_id: str):
    registry = _fixture_registry()
    return registry.document_of(edition_id), registry.edition(edition_id)


# --- The registry ------------------------------------------------------------------


def test_the_fixture_registry_reads_on_its_own_host():
    documents = read_documents(FIXTURE_REGISTRY, allowed_host=FIXTURE_HOST)
    assert [d.id for d in documents] == ["fixture_dining", "fixture_finance", "fixture_engineering"]


def test_the_fixture_registry_is_refused_on_the_real_host():
    with pytest.raises(RegistryError, match="must be https on aui.ma"):
        read_documents(FIXTURE_REGISTRY)


def test_the_real_registry_still_refuses_another_host(tmp_path):
    text = (FIXTURE_REGISTRY.parent / "fixture_registry.toml").read_text(encoding="utf-8")
    path = tmp_path / "registry.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(RegistryError, match="must be https on aui.ma"):
        load_registry(path)


def test_fixtures_join_the_real_registry_without_taking_the_course_tables():
    registry = _fixture_registry()
    assert len(registry.editions) == len(load_registry().editions) + 3
    assert registry.course_tables_edition() == load_registry().course_tables_edition()


def test_the_fixtures_alone_are_not_a_whole_registry():
    with pytest.raises(RegistryError, match="exactly one edition must have course_tables"):
        registry_of(read_documents(FIXTURE_REGISTRY, allowed_host=FIXTURE_HOST))


def test_only_the_catalog_has_the_catalog_layout():
    layouts = {edition.id: edition.layout for edition in load_registry().editions}
    catalog = load_registry().course_tables_edition().id
    assert layouts.pop(catalog) == "aui_catalog"
    assert set(layouts.values()) == {"plain"}
    assert all(e.layout == "plain" for e in _fixture_registry().editions if e.id.startswith("fix"))


def test_every_layout_name_has_chunking_rules():
    assert set(LAYOUT_RULES) == LAYOUTS


# --- The gates ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "edition_id", ["fixture_dining_guide", "fixture_finance_fees", "fixture_engineering_handbook"]
)
def test_each_fixture_passes_every_gate(edition_id):
    text = load_edition_text(_fixture_registry(), edition_id, FIXTURES)
    assert "TEST FIXTURE" in text


def test_a_non_public_document_is_refused():
    document, edition = _fixture("fixture_dining_guide")
    with pytest.raises(IngestRefused, match="isn't public"):
        check_edition(
            replace(document, visibility="non_public"), edition, FIXTURES / edition.filename
        )


def test_a_french_edition_is_refused_until_b3():
    document, edition = _fixture("fixture_dining_guide")
    with pytest.raises(IngestRefused, match="language 'fr'.*B3"):
        check_edition(document, replace(edition, language="fr"), FIXTURES / edition.filename)


def test_an_unknown_format_is_refused():
    document, edition = _fixture("fixture_dining_guide")
    with pytest.raises(IngestRefused, match="format 'docx' isn't supported"):
        check_edition(document, replace(edition, format="docx"), FIXTURES / "x.docx")


def test_a_missing_file_is_refused(tmp_path):
    document, edition = _fixture("fixture_dining_guide")
    with pytest.raises(IngestRefused, match="isn't there"):
        check_edition(document, edition, tmp_path / edition.filename)


def test_a_file_that_is_not_the_registered_one_is_refused(tmp_path):
    document, edition = _fixture("fixture_dining_guide")
    changed = tmp_path / edition.filename
    changed.write_bytes((FIXTURES / edition.filename).read_bytes() + b"\n")
    with pytest.raises(IngestRefused, match="sha256 is .* the registry says"):
        check_edition(document, edition, changed)


@pytest.mark.parametrize(
    ("edition_id", "format"), [("fixture_dining_guide", "html"), ("fixture_finance_fees", "pdf")]
)
def test_a_file_over_the_size_limit_is_refused(monkeypatch, edition_id, format):
    document, edition = _fixture(edition_id)
    path = FIXTURES / edition.filename
    monkeypatch.setitem(gates.MAX_FILE_BYTES, format, path.stat().st_size - 1)
    with pytest.raises(IngestRefused, match="over the .*-byte limit"):
        check_edition(document, edition, path)


def test_a_file_at_the_size_limit_passes(monkeypatch):
    document, edition = _fixture("fixture_dining_guide")
    path = FIXTURES / edition.filename
    monkeypatch.setitem(gates.MAX_FILE_BYTES, "html", path.stat().st_size)
    check_edition(document, edition, path)


def test_every_loader_format_has_a_size_limit():
    from app.ingestion.loaders import LOADERS

    assert {f for loader in LOADERS for f in loader.formats} == set(gates.MAX_FILE_BYTES)


def test_a_pdf_over_the_page_limit_is_refused(monkeypatch):
    document, edition = _fixture("fixture_finance_fees")  # two pages
    monkeypatch.setattr(gates, "MAX_PDF_PAGES", 1)
    with pytest.raises(IngestRefused, match="2 pages, over the 1-page limit"):
        check_edition(document, edition, FIXTURES / edition.filename)


def test_a_file_that_is_not_a_pdf_is_refused_not_crashed_on(tmp_path):
    document, edition = _fixture("fixture_finance_fees")
    path = tmp_path / edition.filename
    path.write_bytes(b"this is not a PDF")
    registered = replace(edition, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(IngestRefused, match="can't be read as a PDF"):
        check_edition(document, registered, path)


# --- Only registered files, and nothing written on a refusal -----------------------


def _raw_dir_with_fixtures(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    for path in FIXTURES.glob("fixture_*.*"):
        if path.suffix in (".html", ".pdf"):
            shutil.copy(path, raw / path.name)
    return raw


def _fixtures_as_a_registry():
    """The fixture documents as a whole registry of their own, for clean_all: one of
    them carries the course-tables flag every whole registry needs (nothing is seeded
    from it here)."""
    first, *rest = read_documents(FIXTURE_REGISTRY, allowed_host=FIXTURE_HOST)
    flagged = replace(first, editions=(replace(first.editions[0], course_tables=True),))
    return registry_of((flagged, *rest))


def test_a_stray_file_is_reported_and_never_read(tmp_path):
    raw = _raw_dir_with_fixtures(tmp_path)
    (raw / "notes.txt").write_text("not a source", encoding="utf-8")
    (raw / "dropped_in.html").write_text("<p>not registered</p>", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")
    assert ignored_files(_fixtures_as_a_registry(), raw) == ["dropped_in.html", "notes.txt"]


def test_clean_writes_each_registered_edition_and_names_the_ignored(tmp_path, capsys):
    raw, processed = _raw_dir_with_fixtures(tmp_path), tmp_path / "processed"
    (raw / "dropped_in.html").write_text("<p>not registered</p>", encoding="utf-8")
    clean_all(_fixtures_as_a_registry(), raw, processed)
    assert sorted(p.name for p in processed.iterdir()) == [
        "fixture_dining_guide.txt",
        "fixture_engineering_handbook.txt",
        "fixture_finance_fees.txt",
    ]
    out = capsys.readouterr().out
    assert "ignored (not in the registry): dropped_in.html" in out
    assert "not registered" not in (processed / "fixture_dining_guide.txt").read_text("utf-8")


def test_one_refusal_writes_nothing_and_exits_1(tmp_path, capsys):
    raw, processed = _raw_dir_with_fixtures(tmp_path), tmp_path / "processed"
    # The second edition in order is changed, so the first has already passed its gates.
    with open(raw / "fixture_finance_fees.pdf", "ab") as f:
        f.write(b"%")
    assert main(_fixtures_as_a_registry(), raw, processed) == 1
    assert not processed.exists()
    out = capsys.readouterr().out
    assert "refused: fixture_finance_fees" in out
    assert "Nothing changed." in out


def test_main_exits_0_when_every_edition_passes(tmp_path):
    raw, processed = _raw_dir_with_fixtures(tmp_path), tmp_path / "processed"
    assert main(_fixtures_as_a_registry(), raw, processed) == 0
    assert len(list(processed.iterdir())) == 3


# --- Chunking follows the edition's layout and language ----------------------------


def test_each_edition_gets_its_own_layout_rules_and_language():
    registry = _fixture_registry()
    catalog = registry.course_tables_edition()
    assert settings_for(registry.document_of(catalog.id), catalog).rules is CATALOG_RULES
    dining = registry.edition("fixture_dining_guide")
    settings = settings_for(registry.document_of(dining.id), dining)
    assert settings == ChunkSettings(starting_level="general", language="en", rules=PLAIN_RULES)
    handbook = registry.edition("fixture_engineering_handbook")  # audience: undergraduate
    assert settings_for(registry.document_of(handbook.id), handbook).starting_level == (
        "undergraduate"
    )


# A catalog part heading and a page header line, inside another kind of document.
LINES = [
    "The office opens at nine every weekday morning",
    "www.aui.ma",
    "Opening Hours",
    "The dining hall serves breakfast from seven until half past nine each day.",
    "AL AKHAWAYN GRADUATE STUDIES",
    "Lunch is served from noon until two in the afternoon on weekdays only.",
]


def test_catalog_rules_apply_only_with_the_catalog_layout():
    catalog = ChunkSettings("general", "en", CATALOG_RULES)
    plain = ChunkSettings("general", "en", PLAIN_RULES)
    # The catalog's page header ends a sentence there, so "Opening Hours" is a heading,
    # and its part heading switches the level.
    assert assign_sections("any", LINES, catalog)[2:5] == [
        ("general", "Opening Hours"),
        ("general", "Opening Hours"),
        ("graduate", None),
    ]
    # Plainly, "www.aui.ma" is only a line of text, so "Opening Hours" isn't a heading;
    # the part heading is only heading-shaped text, so it never switches the level.
    assert assign_sections("any", LINES, plain)[2:5] == [
        ("general", None),
        ("general", None),
        ("general", "AL AKHAWAYN GRADUATE STUDIES"),
    ]


def test_chunks_carry_the_editions_language():
    settings = ChunkSettings("general", "xx", PLAIN_RULES)
    [chunk] = chunk_text("any", "\n".join(LINES), settings=settings)
    assert chunk.language == "xx"
    assert chunk.level == "general"
