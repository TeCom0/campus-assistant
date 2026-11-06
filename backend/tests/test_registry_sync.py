"""Sync: data/registry.toml into the registry tables, and what the database itself
guarantees. Each database test runs in a transaction that is rolled back, starting
from empty registry tables, so it leaves the database as it found it.
"""

from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
import yaml

from app import registry as registry_module
from app.db.connection import database_reachable, get_owner_connection
from app.registry import (
    COUNTED_TABLES,
    Registry,
    RegistryError,
    editions_not_in_file,
    load_registry,
    status_counts,
    sync,
    table_counts,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = "academic_catalog_2024_2025"

needs_db = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")


@pytest.fixture
def conn():
    connection = get_owner_connection()
    with connection.transaction(force_rollback=True):
        connection.execute("DELETE FROM document_editions")
        connection.execute("DELETE FROM documents")
        yield connection
    connection.close()


def _edition_row(conn, edition_id: str = CATALOG) -> dict:
    cursor = conn.execute("SELECT * FROM document_editions WHERE id = %s", (edition_id,))
    names = [column.name for column in cursor.description]
    return dict(zip(names, cursor.fetchone(), strict=True))


def _with_second_catalog_edition(registry: Registry) -> Registry:
    """The real registry, plus a newer draft-to-be catalog edition."""
    catalog = registry.documents[0]
    newer = replace(catalog.editions[0], id="catalog_newer", label="newer", course_tables=False)
    return Registry(
        (replace(catalog, editions=(*catalog.editions, newer)), *registry.documents[1:])
    )


@needs_db
def test_initial_marks_every_edition_active_and_records_who(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    assert status_counts(conn) == {"active": len(registry.editions)}
    row = _edition_row(conn)
    assert row["activated_by"] == "registry sync --initial"
    assert row["activated_at"] is not None
    assert row["parser_version"] == "unversioned"
    assert row["quality_report"] == {}


@needs_db
def test_initial_copies_the_descriptive_fields_exactly(conn):
    sync(conn, load_registry(), initial=True)
    row = _edition_row(conn)
    assert row["card_title"] == "Academic Catalog 2024–2025"
    assert row["fallback_url"] == "https://aui.ma/academic-catalogs"
    assert row["last_updated"] is None
    assert row["course_tables"] is True
    title, department = conn.execute(
        "SELECT title, owning_department FROM documents WHERE id = 'academic_catalog'"
    ).fetchone()
    assert title == {"en": "Academic Catalog", "fr": "Catalogue académique"}
    assert department == "Office of the Registrar"


@needs_db
def test_a_department_nobody_confirmed_is_null_not_a_placeholder(conn):
    sync(conn, load_registry(), initial=True)
    department = conn.execute(
        "SELECT owning_department FROM documents WHERE id = 'prestigious_scholarships'"
    ).fetchone()[0]
    assert department is None


@needs_db
def test_initial_refuses_tables_that_already_have_editions_and_changes_nothing(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    conn.execute("UPDATE document_editions SET status = 'withdrawn' WHERE id = %s", (CATALOG,))
    with pytest.raises(RegistryError, match="only for empty tables"):
        sync(conn, registry, initial=True)
    assert _edition_row(conn)["status"] == "withdrawn"


@needs_db
def test_plain_sync_refuses_empty_tables(conn):
    # It would insert everything as draft: nothing live, and exit 0.
    with pytest.raises(RegistryError, match="sync --initial"):
        sync(conn, load_registry())
    assert table_counts(conn)["documents"] == 0
    assert table_counts(conn)["document_editions"] == 0


@needs_db
def test_initial_refuses_two_editions_of_one_document(conn):
    with pytest.raises(RegistryError, match="only one may be"):
        sync(conn, _with_second_catalog_edition(load_registry()), initial=True)
    assert table_counts(conn)["document_editions"] == 0


@needs_db
@pytest.mark.parametrize("status", ["draft", "active", "superseded", "withdrawn"])
def test_sync_never_changes_an_existing_editions_status(conn, status):
    registry = load_registry()
    sync(conn, registry, initial=True)
    conn.execute("UPDATE document_editions SET status = %s WHERE id = %s", (status, CATALOG))
    sync(conn, registry)
    assert _edition_row(conn)["status"] == status


@needs_db
def test_sync_keeps_the_activation_record(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    before = _edition_row(conn)
    sync(conn, registry)
    after = _edition_row(conn)
    assert after["activated_at"] == before["activated_at"]
    assert after["activated_by"] == before["activated_by"]


@needs_db
def test_sync_updates_descriptive_fields(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    catalog = registry.documents[0]
    relabelled = replace(catalog.editions[0], card_title="A new title")
    changed = Registry(
        (
            replace(catalog, editions=(relabelled,), owning_department=None),
            *registry.documents[1:],
        )
    )
    sync(conn, changed)
    row = _edition_row(conn)
    assert row["card_title"] == "A new title"
    assert row["status"] == "active"
    department = conn.execute(
        "SELECT owning_department FROM documents WHERE id = 'academic_catalog'"
    ).fetchone()[0]
    assert department is None


@needs_db
def test_a_new_edition_goes_in_as_draft_without_touching_the_active_one(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    sync(conn, _with_second_catalog_edition(registry))
    newer = _edition_row(conn, "catalog_newer")
    assert newer["status"] == "draft"
    assert newer["activated_by"] is None
    assert newer["activated_at"] is None
    assert _edition_row(conn)["status"] == "active"


@needs_db
def test_an_edition_only_the_database_has_is_reported_and_left_alone(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    sync(conn, _with_second_catalog_edition(registry))
    sync(conn, registry)
    assert editions_not_in_file(conn, registry) == ["catalog_newer"]
    assert _edition_row(conn, "catalog_newer")["status"] == "draft"


@needs_db
def test_a_failure_part_way_leaves_nothing_behind(conn, monkeypatch):
    registry = load_registry()
    real_upsert = registry_module._upsert_edition
    calls = []

    def fails_on_the_second(connection, edition, *, active):
        calls.append(edition.id)
        if len(calls) == 2:
            raise psycopg.errors.CheckViolation("simulated")
        real_upsert(connection, edition, active=active)

    monkeypatch.setattr(registry_module, "_upsert_edition", fails_on_the_second)
    with pytest.raises(psycopg.errors.CheckViolation):
        sync(conn, registry, initial=True)
    assert table_counts(conn)["documents"] == 0
    assert table_counts(conn)["document_editions"] == 0


@needs_db
def test_sync_changes_no_content_table(conn):
    before = table_counts(conn)
    sync(conn, load_registry(), initial=True)
    after = table_counts(conn)
    for table in ("document_chunks", "courses", "course_prerequisites"):
        assert after[table] == before[table]


# --- What the database itself guarantees --------------------------------------


@needs_db
def test_the_database_refuses_a_second_active_edition_of_a_document(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    sync(conn, _with_second_catalog_edition(registry))
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        conn.execute("UPDATE document_editions SET status = 'active' WHERE id = 'catalog_newer'")


@needs_db
def test_the_database_allows_many_editions_that_are_not_active(conn):
    registry = load_registry()
    sync(conn, registry, initial=True)
    sync(conn, _with_second_catalog_edition(registry))
    conn.execute("UPDATE document_editions SET status = 'superseded' WHERE id = %s", (CATALOG,))
    conn.execute("UPDATE document_editions SET status = 'superseded' WHERE id = 'catalog_newer'")
    assert status_counts(conn)["superseded"] == 2


@needs_db
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE document_editions SET status = 'live'",
        "UPDATE document_editions SET format = 'docx'",
        "UPDATE documents SET visibility = 'secret'",
    ],
)
def test_the_database_refuses_values_outside_the_fixed_sets(conn, statement):
    sync(conn, load_registry(), initial=True)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute(statement)


# --- The command --------------------------------------------------------------


class _NoClose:
    """The fixture's connection, which the command must not close under the test."""

    def __init__(self, connection):
        self._connection = connection

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def close(self):
        pass


@needs_db
def test_the_command_prints_proof_of_every_table(conn, monkeypatch, capfd):
    monkeypatch.setattr(registry_module, "get_owner_connection", lambda: _NoClose(conn))
    assert registry_module.main(["sync", "--initial"]) == 0
    output = capfd.readouterr().out
    for table in COUNTED_TABLES:
        assert f"[registry] {table}: " in output
    assert "[registry] documents: 3" in output
    assert "[registry] document_editions: 3" in output
    assert "{'active': 3}" in output
    assert "sync done" in output


@needs_db
def test_the_command_exits_non_zero_on_a_refusal(conn, monkeypatch, capfd):
    monkeypatch.setattr(registry_module, "get_owner_connection", lambda: _NoClose(conn))
    assert registry_module.main(["sync"]) == 1
    output = capfd.readouterr().out
    assert "refused" in output
    assert "sync done" not in output


def test_the_command_exits_non_zero_if_a_table_stays_empty(monkeypatch, capfd):
    monkeypatch.setattr(registry_module, "load_registry", load_registry)
    monkeypatch.setattr(registry_module, "get_owner_connection", lambda: _StubConnection())
    monkeypatch.setattr(registry_module, "sync", lambda *a, **k: None)
    monkeypatch.setattr(registry_module, "table_counts", lambda c: dict.fromkeys(COUNTED_TABLES, 0))
    monkeypatch.setattr(registry_module, "status_counts", lambda c: {})
    monkeypatch.setattr(registry_module, "editions_not_in_file", lambda c, r: [])
    assert registry_module.main(["sync"]) == 1
    output = capfd.readouterr().out
    assert "[registry] documents: 0" in output
    assert "FAILED" in output


class _StubConnection:
    def close(self):
        pass


def test_a_bad_registry_file_stops_the_command_before_the_database(monkeypatch, tmp_path, capfd):
    monkeypatch.setattr(registry_module, "REGISTRY_PATH", tmp_path / "nowhere.toml")

    def no_database():
        raise AssertionError("a bad file must stop before connecting")

    monkeypatch.setattr(registry_module, "get_owner_connection", no_database)
    assert registry_module.main(["sync"]) == 1
    assert "can't read" in capfd.readouterr().out


def test_a_database_error_prints_only_its_type(monkeypatch, capfd):
    def fails():
        raise psycopg.OperationalError("password SECRETMARKER rejected")

    monkeypatch.setattr(registry_module, "get_owner_connection", fails)
    assert registry_module.main(["sync"]) == 1
    output = capfd.readouterr().out
    assert "OperationalError" in output
    assert "SECRETMARKER" not in output


# --- The deployment files -----------------------------------------------------


def _compose() -> dict:
    return yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_sync_runs_as_the_owner_with_one_read_only_mount_of_the_file():
    service = _compose()["services"]["registry-sync"]
    assert service["volumes"] == ["./data/registry.toml:/app/data/registry.toml:ro"]
    assert service["command"] == ["python", "-m", "app.registry", "sync"]
    assert service["restart"] == "no"
    assert "POSTGRES_PASSWORD" not in service["environment"]  # keeps the owner's, from .env
    assert "ports" not in service
    assert service["depends_on"]["migrate"]["condition"] == "service_completed_successfully"


def test_the_mount_is_where_the_module_looks_inside_the_image():
    # WORKDIR /app/backend plus COPY app ./app puts registry.py at /app/backend/app/, and
    # REGISTRY_PATH is two levels above its folder, then data/registry.toml.
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "WORKDIR /app/backend" in dockerfile
    assert "COPY app ./app" in dockerfile
    relative = registry_module.REGISTRY_PATH.relative_to(REPO_ROOT)
    assert relative.as_posix() == "data/registry.toml"


def test_only_the_sync_service_gets_the_file():
    services = _compose()["services"]
    with_file = [
        name
        for name, service in services.items()
        if any("registry.toml" in str(volume) for volume in service.get("volumes", []))
    ]
    assert with_file == ["registry-sync"]


def test_the_api_starts_only_after_sync_has_succeeded():
    waits_for = _compose()["services"]["api"]["depends_on"]["registry-sync"]["condition"]
    assert waits_for == "service_completed_successfully"


def test_ci_syncs_after_migrating_and_before_the_tests():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    migrate = workflow.index("python -m app.db.migrate")
    sync_step = workflow.index("python -m app.registry sync --initial")
    tests = workflow.index("pytest -v")
    assert migrate < sync_step < tests
