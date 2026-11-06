"""Rules that keep the registry the only list: enforced here, not only written down.

No aui.ma URL and no edition id appears in backend/app outside the registry module, and
importing the API never reads the file its image doesn't hold.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.ingestion import courses, load
from app.ingestion.chunk import assign_sections
from app.ingestion.courses import extract_courses
from app.registry import REGISTRY_PATH, RegistryError, load_registry

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
REPO_ROOT = BACKEND.parent

AUI_URL_RE = re.compile(r"https?://(?:[\w-]+\.)*aui\.ma\b", re.IGNORECASE)


def _forbidden_in(text: str, edition_ids: set[str]) -> list[str]:
    found = AUI_URL_RE.findall(text)
    found += [edition_id for edition_id in edition_ids if edition_id in text]
    return found


def _app_files() -> list[Path]:
    return [
        path
        for path in APP.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path != APP / "registry.py"
    ]


def test_no_aui_url_or_edition_id_in_the_app_outside_the_registry_module():
    edition_ids = {edition.id for edition in load_registry().editions}
    assert _app_files(), "the scan must look at something"
    offenders = {
        str(path.relative_to(BACKEND)): found
        for path in _app_files()
        if (found := _forbidden_in(path.read_text(encoding="utf-8"), edition_ids))
    }
    assert offenders == {}


@pytest.mark.parametrize(
    "text",
    [
        'URL = "https://aui.ma/some-page"',
        'URL = "http://aui.ma/some-page"',
        'URL = "https://www.aui.ma/some-page"',
        'URL = "HTTPS://AUI.MA/SOME-PAGE"',
        'SOURCE = "catalog_2024"',
    ],
)
def test_the_scan_catches_what_it_is_meant_to(text):
    assert _forbidden_in(text, {"catalog_2024"})


@pytest.mark.parametrize(
    "text",
    [
        # The catalog's page header, a line of its text and not a URL: chunk.py needs it.
        'PAGE_HEADER_LINES = {"www.aui.ma"}',
        "straight to aui.ma, so that if the catalog PDF moves",
        'URL = "https://example.com/aui.ma"',
    ],
)
def test_the_scan_leaves_alone_what_is_not_a_url_on_that_host(text):
    assert not _forbidden_in(text, {"catalog_2024"})


def test_importing_the_api_never_reads_the_registry_file():
    # The API's image doesn't contain the file. Reading it at import would stop the API
    # from starting, and app.main imports app.ingestion.chunk through app.sources.
    code = (
        "import tomllib\n"
        "def refuse(*args, **kwargs):\n"
        "    raise AssertionError('the registry was read at import')\n"
        "tomllib.load = refuse\n"
        "tomllib.loads = refuse\n"
        "import app.main\n"
        "print('imported without reading it')\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert "imported without reading it" in done.stdout


def test_the_control_reading_the_registry_does_trigger_the_refusal():
    code = (
        "import tomllib\n"
        "def refuse(*args, **kwargs):\n"
        "    raise AssertionError('the registry was read')\n"
        "tomllib.load = refuse\n"
        "from app.registry import load_registry\n"
        "load_registry()\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode != 0
    assert "the registry was read" in done.stderr


def test_the_registry_path_is_outside_the_folder_the_image_copies():
    assert APP not in REGISTRY_PATH.parents


# --- data/sources.md is a pointer, so there's one list -----------------------------


def test_sources_md_points_to_the_registry_and_holds_no_list_of_its_own():
    text = (REPO_ROOT / "data" / "sources.md").read_text(encoding="utf-8")
    assert "data/registry.toml" in text
    assert "http://" not in text
    assert "https://" not in text


# --- What each module now reads from it --------------------------------------------


@pytest.mark.parametrize(
    ("source", "level"),
    [
        ("academic_catalog_2024_2025", "general"),
        ("graduate_scholarships", "graduate"),
        ("prestigious_scholarships", "general"),
    ],
)
def test_a_documents_starting_level_is_what_it_was(source, level):
    assert assign_sections(source, ["a", "b"])[0][0] == level


def test_an_audience_that_is_not_a_level_starts_at_the_default(monkeypatch, tmp_path):
    path = tmp_path / "registry.toml"
    path.write_text(
        '[[document]]\nid = "staff_page"\ntitle = { en = "S", fr = "S" }\ndomain = "academic"\n'
        'audience = "staff"\nvisibility = "public"\ntime_sensitive = false\n'
        '[[document.edition]]\nid = "staff_page"\nlabel = "x"\ncard_title = "S"\n'
        'retrieved_at = "2026-09-29"\nlanguage = "en"\nformat = "html"\n'
        f'source_url = "https://aui.ma/s"\nsha256 = "{"a" * 64}"\ncourse_tables = true\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("app.registry.REGISTRY_PATH", path)
    assert assign_sections("staff_page", ["a", "b"])[0][0] == "general"


def test_chunking_a_source_that_is_not_in_the_registry_fails():
    with pytest.raises(RegistryError, match="no edition"):
        assign_sections("not_in_the_registry", ["a", "b"])


def test_the_courses_come_from_the_edition_the_registry_names_and_are_labelled_with_it():
    edition = load_registry().course_tables_edition()
    extracted = extract_courses(edition.id)
    assert len(extracted) == 660
    assert {course["source"] for course in extracted.values()} == {edition.id}


def test_seeding_reads_the_edition_from_the_registry(monkeypatch):
    asked_for = []

    def stop_after_recording(edition_id):
        asked_for.append(edition_id)
        raise RuntimeError("stop before the database")

    monkeypatch.setattr(courses, "extract_courses", stop_after_recording)
    with pytest.raises(RuntimeError, match="stop before the database"):
        courses.seed_courses()
    assert asked_for == [load_registry().course_tables_edition().id]


class _FakeResponse:
    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        return [b"content"]


def test_the_download_list_is_the_registry(monkeypatch, tmp_path):
    requested = []

    def fake_get(url, **kwargs):
        requested.append(url)
        return _FakeResponse()

    monkeypatch.setattr(load.requests, "get", fake_get)
    monkeypatch.setattr(load, "DATA_RAW_DIR", tmp_path)
    load.download_sources()
    editions = load_registry().editions
    assert requested == [edition.source_url for edition in editions]
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        edition.filename for edition in editions
    )


def test_a_file_already_downloaded_is_skipped(monkeypatch, tmp_path):
    def no_network(url, **kwargs):
        raise AssertionError("must not download a file it already has")

    for edition in load_registry().editions:
        (tmp_path / edition.filename).write_bytes(b"already here")
    monkeypatch.setattr(load.requests, "get", no_network)
    monkeypatch.setattr(load, "DATA_RAW_DIR", tmp_path)
    load.download_sources()
