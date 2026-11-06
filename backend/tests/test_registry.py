"""The registry file and its validation. No database and no network.

Every rule has a fixture that must fail: a rule nothing proves is a rule that can
quietly stop working.
"""

import dataclasses
import hashlib
from datetime import date
from pathlib import Path

import pytest

from app.registry import REGISTRY_PATH, RegistryError, load_registry

RAW_DIR = REGISTRY_PATH.parent / "raw"

# Today's document_chunks.source values. If an edition id changed, chunks and courses
# would point at nothing.
EDITION_IDS = {"academic_catalog_2024_2025", "graduate_scholarships", "prestigious_scholarships"}

VALID = """
[[document]]
id = "catalog"
title = { en = "Catalog", fr = "Catalogue" }
domain = "academic"
owning_department = "Registrar"
audience = "all"
visibility = "public"
time_sensitive = true

  [[document.edition]]
  id = "catalog_2024"
  label = "2024"
  card_title = "Catalog 2024"
  effective_from = "2024-08-01"
  review_by = "2027-08-01"
  retrieved_at = "2026-09-29"
  last_updated = "2025-01-15"
  language = "en"
  format = "pdf"
  source_url = "https://aui.ma/catalog.pdf"
  fallback_url = "https://www.aui.ma/catalogs"
  sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  course_tables = true

[[document]]
id = "page"
title = { en = "Page", fr = "Page" }
domain = "scholarships"
audience = "graduate"
visibility = "public"
time_sensitive = false

  [[document.edition]]
  id = "page_one"
  label = "retrieved"
  card_title = "Page (website)"
  retrieved_at = "2026-09-29"
  language = "fr"
  format = "html"
  source_url = "https://aui.ma/page"
  sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "registry.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _mutated(old: str, new: str) -> str:
    assert old in VALID, f"the fixture no longer contains {old!r}"
    return VALID.replace(old, new, 1)


def test_the_valid_fixture_loads_so_the_failures_below_mean_something(tmp_path):
    registry = load_registry(_write(tmp_path, VALID))
    assert [document.id for document in registry.documents] == ["catalog", "page"]
    first = registry.documents[0].editions[0]
    assert first.effective_from == date(2024, 8, 1)
    assert first.last_updated == date(2025, 1, 15)
    assert first.filename == "catalog_2024.pdf"
    assert first.course_tables is True
    # What may be left out comes back as None or False, not as a placeholder.
    page = registry.documents[1]
    assert page.owning_department is None
    assert page.editions[0].fallback_url is None
    assert page.editions[0].last_updated is None
    assert page.editions[0].course_tables is False


BAD_FILES = [
    ("repeated document id", 'id = "page"', 'id = "catalog"', "document id"),
    ("repeated edition id", 'id = "page_one"', 'id = "catalog_2024"', "edition id"),
    ("unknown domain", 'domain = "academic"', 'domain = "astrology"', "domain"),
    ("unknown audience", 'audience = "all"', 'audience = "everyone"', "audience"),
    ("unknown visibility", 'visibility = "public"', 'visibility = "secret"', "visibility"),
    ("non_public", 'visibility = "public"', 'visibility = "non_public"', "non_public"),
    ("unknown language", 'language = "en"', 'language = "de"', "language"),
    ("unknown format", 'format = "pdf"', 'format = "docx"', "format"),
    ("impossible date", 'review_by = "2027-08-01"', 'review_by = "2027-13-01"', "real date"),
    ("not a date", 'review_by = "2027-08-01"', 'review_by = "soon"', "YYYY-MM-DD"),
    ("compact date", 'review_by = "2027-08-01"', 'review_by = "20270801"', "YYYY-MM-DD"),
    ("native TOML date", 'review_by = "2027-08-01"', "review_by = 2027-08-01", "string"),
    ("bad retrieved_at", 'retrieved_at = "2026-09-29"', 'retrieved_at = "x"', "retrieved_at"),
    ("bad last_updated", 'last_updated = "2025-01-15"', 'last_updated = "x"', "last_updated"),
    ("bad effective_from", 'effective_from = "2024-08-01"', 'effective_from = "x"', "effective"),
    (
        "short sha256",
        '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
        '"aaaa"',
        "sha256",
    ),
    (
        "upper-case sha256",
        '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
        '"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"',
        "sha256",
    ),
    (
        "non-hex sha256",
        '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
        '"gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"',
        "sha256",
    ),
    ("http URL", '"https://aui.ma/catalog.pdf"', '"http://aui.ma/catalog.pdf"', "https"),
    ("another host", '"https://aui.ma/catalog.pdf"', '"https://example.com/c.pdf"', "https"),
    ("lookalike host", '"https://aui.ma/catalog.pdf"', '"https://aui.ma.example.com/c"', "https"),
    ("suffix host", '"https://aui.ma/catalog.pdf"', '"https://notaui.ma/c.pdf"', "https"),
    ("host in the path", '"https://aui.ma/catalog.pdf"', '"https://example.com/aui.ma"', "https"),
    ("userinfo", '"https://aui.ma/catalog.pdf"', '"https://aui.ma@example.com/c"', "character"),
    ("backslash", '"https://aui.ma/catalog.pdf"', r"'https://example.com\@aui.ma/c'", "character"),
    ("space in URL", '"https://aui.ma/catalog.pdf"', '"https://aui.ma/a b.pdf"', "character"),
    ("fallback on another host", '"https://www.aui.ma/catalogs"', '"https://x.test/c"', "fallback"),
    ("unknown document field", 'domain = "academic"', 'domain = "academic"\nowner = "x"', "owner"),
    ("typo in an edition field", "fallback_url =", "fallback_ulr =", "fallback_ulr"),
    ("missing required field", 'card_title = "Catalog 2024"', "", "card_title"),
    ("missing retrieved_at", 'retrieved_at = "2026-09-29"', "", "retrieved_at"),
    ("empty title text", 'en = "Catalog"', 'en = " "', "non-empty"),
    ("title without French", ', fr = "Catalogue"', "", "en and fr"),
    ("department not text", 'owning_department = "Registrar"', "owning_department = 1", "string"),
    ("non-boolean flag", "time_sensitive = true", 'time_sensitive = "yes"', "true or false"),
    ("id unsafe as a file name", 'id = "catalog_2024"', 'id = "../catalog"', "a-z"),
    ("no course_tables edition", "course_tables = true", "", "course_tables"),
    (
        "two course_tables editions",
        'format = "html"',
        'format = "html"\n  course_tables = true',
        "course_tables",
    ),
    ("broken TOML", 'domain = "academic"', 'domain = "academic', "valid TOML"),
    ("stray top-level key", "[[document]]", "stray = 1\n[[document]]", "nothing else"),
]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [row[1:] for row in BAD_FILES],
    ids=[row[0] for row in BAD_FILES],
)
def test_a_bad_file_fails_loudly(tmp_path, old, new, message):
    with pytest.raises(RegistryError, match=message):
        load_registry(_write(tmp_path, _mutated(old, new)))


def test_a_document_without_editions_fails(tmp_path):
    text = (
        '[[document]]\nid = "x"\ntitle = { en = "X", fr = "X" }\ndomain = "academic"\n'
        'audience = "all"\nvisibility = "public"\ntime_sensitive = true\nedition = []\n'
    )
    with pytest.raises(RegistryError, match="at least one edition"):
        load_registry(_write(tmp_path, text))


def test_an_empty_file_fails(tmp_path):
    with pytest.raises(RegistryError, match="nothing else"):
        load_registry(_write(tmp_path, ""))


def test_a_missing_file_fails(tmp_path):
    with pytest.raises(RegistryError, match="can't read"):
        load_registry(tmp_path / "nowhere.toml")


def test_the_loaded_registry_cannot_be_changed():
    edition = load_registry().editions[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        edition.source_url = "https://example.com"


def test_looking_up_an_unknown_edition_fails():
    with pytest.raises(RegistryError, match="no edition"):
        load_registry().document_of("not_an_edition")


# --- The real file ----------------------------------------------------------


def test_edition_ids_equal_todays_source_values():
    assert {edition.id for edition in load_registry().editions} == EDITION_IDS


def test_the_real_files_links_and_titles_are_todays_exactly():
    by_id = {edition.id: edition for edition in load_registry().editions}
    catalog = by_id["academic_catalog_2024_2025"]
    assert catalog.card_title == "Academic Catalog 2024–2025"  # an en dash
    assert catalog.source_url == "https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en"
    assert catalog.fallback_url == "https://aui.ma/academic-catalogs"
    assert catalog.format == "pdf"

    graduate = by_id["graduate_scholarships"]
    assert graduate.card_title == "Graduate Scholarships (AUI website)"
    assert graduate.source_url == "https://aui.ma/admission-aid/graduates/scholarships"
    assert graduate.fallback_url is None
    assert graduate.format == "html"

    prestigious = by_id["prestigious_scholarships"]
    assert prestigious.card_title == "Prestigious Scholarships (AUI website)"
    assert prestigious.source_url == "https://aui.ma/prestigious-scholarship"
    assert prestigious.fallback_url is None
    assert prestigious.format == "html"


def test_the_catalog_carries_the_course_tables():
    assert load_registry().course_tables_edition().id == "academic_catalog_2024_2025"


def test_no_edition_states_a_revision_date_it_does_not_have():
    # The catalog PDF's metadata says 2025-08-31, which isn't a revision the publisher
    # states. Only a date the publisher really gives may go in this field.
    assert all(edition.last_updated is None for edition in load_registry().editions)


def test_each_edition_has_a_retrieval_date():
    assert all(edition.retrieved_at == date(2026, 9, 29) for edition in load_registry().editions)


@pytest.mark.parametrize("edition", load_registry().editions, ids=lambda e: e.id)
def test_the_recorded_checksum_is_the_files(edition):
    # data/raw is gitignored, so this runs on a machine that has the files, not in CI.
    path = RAW_DIR / edition.filename
    if not path.exists():
        pytest.skip(f"{edition.filename} isn't downloaded here")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == edition.sha256
