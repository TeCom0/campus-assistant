"""The document registry: which documents exist, and where each one comes from.

data/registry.toml is the source for descriptive fields. This module reads and
validates it, once, at the boundary: a mistake stops here with a RegistryError
naming the problem, and everything past this point can trust the data.

The file is read only when a function asks for it, never at import. The API's
image doesn't contain it, and the API imports modules that use this one.

    python -m app.registry sync             # descriptive fields; new editions as draft
    python -m app.registry sync --initial   # once, on empty tables: every edition active

Sync copies the file to the documents and document_editions tables, run as the owner.
It never changes the status of an existing edition: status lives only in the database,
so a redeploy can't undo a rollback. It ends by printing the row counts of every table
the registry touches, as proof of what is there. Psycopg's messages can quote a
statement, so only their type is printed.
"""

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb

from app.db.connection import get_owner_connection

# backend/app/registry.py -> the repo root. In a container: /app/data/registry.toml.
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "registry.toml"

DOMAINS = {"academic", "scholarships", "finance", "housing", "dining", "student_life"}
AUDIENCES = {"all", "undergraduate", "graduate", "staff"}
LANGUAGES = {"en", "fr"}
FORMATS = {"pdf", "html"}
ALLOWED_HOST = "aui.ma"

# An id becomes a file name and part of a URL path.
ID_RE = re.compile(r"[a-z0-9_]+")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

_DOCUMENT_KEYS = {"id", "title", "domain", "audience", "visibility", "time_sensitive", "edition"}
_DOCUMENT_OPTIONAL_KEYS = {"owning_department"}
_EDITION_KEYS = {
    "id",
    "label",
    "card_title",
    "retrieved_at",
    "language",
    "format",
    "source_url",
    "sha256",
}
_EDITION_OPTIONAL_KEYS = {
    "effective_from",
    "review_by",
    "last_updated",
    "fallback_url",
    "course_tables",
}


class RegistryError(Exception):
    """The registry can't be used. The message says why; it holds no secrets."""


@dataclass(frozen=True)
class Edition:
    id: str
    document_id: str
    label: str
    card_title: str
    retrieved_at: date
    language: str
    format: str
    source_url: str
    sha256: str
    effective_from: date | None
    review_by: date | None
    last_updated: date | None
    fallback_url: str | None
    course_tables: bool

    @property
    def filename(self) -> str:
        """Its file in data/raw/."""
        return f"{self.id}.{self.format}"


@dataclass(frozen=True)
class Document:
    id: str
    title_en: str
    title_fr: str
    domain: str
    owning_department: str | None  # None until AUI confirms it, never a placeholder
    audience: str
    visibility: str
    time_sensitive: bool
    editions: tuple[Edition, ...]


@dataclass(frozen=True)
class Registry:
    documents: tuple[Document, ...]

    @property
    def editions(self) -> tuple[Edition, ...]:
        return tuple(edition for document in self.documents for edition in document.editions)

    def document_of(self, edition_id: str) -> Document:
        for document in self.documents:
            if any(edition.id == edition_id for edition in document.editions):
                return document
        raise RegistryError(f"no edition {edition_id!r} in the registry")

    def course_tables_edition(self) -> Edition:
        """The one edition the courses tables are extracted from (checked on load)."""
        return next(edition for edition in self.editions if edition.course_tables)


def _check_keys(table: dict, required: set[str], optional: set[str], where: str) -> None:
    # An unknown key is usually a typo, which would otherwise be dropped silently.
    unknown = set(table) - required - optional
    if unknown:
        raise RegistryError(f"{where}: unknown field(s) {sorted(unknown)}")
    missing = required - set(table)
    if missing:
        raise RegistryError(f"{where}: missing field(s) {sorted(missing)}")


def _text(table: dict, key: str, where: str) -> str:
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{where}: {key} must be a non-empty string")
    return value


def _optional_text(table: dict, key: str, where: str) -> str | None:
    return _text(table, key, where) if key in table else None


def _choice(table: dict, key: str, allowed: set[str], where: str) -> str:
    value = _text(table, key, where)
    if value not in allowed:
        raise RegistryError(f"{where}: {key} {value!r} isn't one of {sorted(allowed)}")
    return value


def _boolean(table: dict, key: str, where: str) -> bool:
    value = table[key]
    if not isinstance(value, bool):
        raise RegistryError(f"{where}: {key} must be true or false")
    return value


def _identifier(table: dict, where: str) -> str:
    value = _text(table, "id", where)
    if not ID_RE.fullmatch(value):
        raise RegistryError(f"{where}: id {value!r} may hold only a-z, 0-9 and _")
    return value


def _date(table: dict, key: str, where: str) -> date:
    # A strict YYYY-MM-DD: fromisoformat alone also accepts forms like 20240801.
    value = _text(table, key, where)
    if not ISO_DATE_RE.fullmatch(value):
        raise RegistryError(f"{where}: {key} {value!r} isn't a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RegistryError(f"{where}: {key} {value!r} isn't a real date") from None


def _optional_date(table: dict, key: str, where: str) -> date | None:
    return _date(table, key, where) if key in table else None


def _url(value: str, key: str, where: str) -> str:
    """An https URL on the university's own host, and nothing that could disguise one."""
    # Python and a browser can disagree on where the host of these ends.
    if "\\" in value or "@" in value or any(c.isspace() for c in value):
        raise RegistryError(f"{where}: {key} {value!r} holds a character a URL must not")
    parts = urlsplit(value)
    host = parts.hostname or ""
    if parts.scheme != "https" or not (host == ALLOWED_HOST or host.endswith(f".{ALLOWED_HOST}")):
        raise RegistryError(f"{where}: {key} {value!r} must be https on {ALLOWED_HOST}")
    return value


def _edition(table: object, document_id: str, position: int) -> Edition:
    where = f"document {document_id!r}, edition {position}"
    if not isinstance(table, dict):
        raise RegistryError(f"{where}: must be a table")
    _check_keys(table, _EDITION_KEYS, _EDITION_OPTIONAL_KEYS, where)
    edition_id = _identifier(table, where)
    where = f"edition {edition_id!r}"
    sha256 = _text(table, "sha256", where)
    if not SHA256_RE.fullmatch(sha256):
        raise RegistryError(f"{where}: sha256 must be 64 lowercase hex characters")
    fallback_url = _optional_text(table, "fallback_url", where)
    return Edition(
        id=edition_id,
        document_id=document_id,
        label=_text(table, "label", where),
        card_title=_text(table, "card_title", where),
        retrieved_at=_date(table, "retrieved_at", where),
        language=_choice(table, "language", LANGUAGES, where),
        format=_choice(table, "format", FORMATS, where),
        source_url=_url(_text(table, "source_url", where), "source_url", where),
        sha256=sha256,
        effective_from=_optional_date(table, "effective_from", where),
        review_by=_optional_date(table, "review_by", where),
        last_updated=_optional_date(table, "last_updated", where),
        fallback_url=_url(fallback_url, "fallback_url", where) if fallback_url else None,
        course_tables=_boolean(table, "course_tables", where)
        if "course_tables" in table
        else False,
    )


def _document(table: object, position: int) -> Document:
    where = f"document {position}"
    if not isinstance(table, dict):
        raise RegistryError(f"{where}: must be a table")
    _check_keys(table, _DOCUMENT_KEYS, _DOCUMENT_OPTIONAL_KEYS, where)
    document_id = _identifier(table, where)
    where = f"document {document_id!r}"

    title = table["title"]
    if not isinstance(title, dict) or set(title) != {"en", "fr"}:
        raise RegistryError(f"{where}: title must have exactly en and fr")

    # Fail closed: nothing downstream handles a non-public document yet (section 3.7).
    visibility = _choice(table, "visibility", {"public", "non_public"}, where)
    if visibility != "public":
        raise RegistryError(f"{where}: non_public documents are refused for now")

    tables = table["edition"]
    if not isinstance(tables, list) or not tables:
        raise RegistryError(f"{where}: needs at least one edition")

    return Document(
        id=document_id,
        title_en=_text(title, "en", where),
        title_fr=_text(title, "fr", where),
        domain=_choice(table, "domain", DOMAINS, where),
        owning_department=_optional_text(table, "owning_department", where),
        audience=_choice(table, "audience", AUDIENCES, where),
        visibility=visibility,
        time_sensitive=_boolean(table, "time_sensitive", where),
        editions=tuple(
            _edition(edition, document_id, n) for n, edition in enumerate(tables, start=1)
        ),
    )


def _check_whole_registry(documents: tuple[Document, ...]) -> None:
    for kind, ids in (
        ("document", [document.id for document in documents]),
        ("edition", [edition.id for document in documents for edition in document.editions]),
    ):
        repeated = sorted({value for value in ids if ids.count(value) > 1})
        if repeated:
            raise RegistryError(f"{kind} id(s) used more than once: {repeated}")

    with_courses = [e.id for document in documents for e in document.editions if e.course_tables]
    if len(with_courses) != 1:
        raise RegistryError(
            f"exactly one edition must have course_tables = true, found {with_courses}"
        )


def load_registry(path: Path | None = None) -> Registry:
    """Read and validate the registry file. Raises RegistryError on any problem."""
    path = REGISTRY_PATH if path is None else path
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except OSError as e:
        raise RegistryError(f"can't read {path}: {type(e).__name__}") from None
    except tomllib.TOMLDecodeError as e:
        raise RegistryError(f"{path} isn't valid TOML: {e}") from None

    if set(data) != {"document"} or not isinstance(data["document"], list) or not data["document"]:
        raise RegistryError(f"{path} must hold [[document]] entries and nothing else")

    documents = tuple(_document(table, n) for n, table in enumerate(data["document"], start=1))
    _check_whole_registry(documents)
    return Registry(documents)


# --- The synced tables: what the API reads -------------------------------------


@dataclass(frozen=True)
class SourceRow:
    """One edition as the API needs it, for source cards and links."""

    edition_id: str
    card_title: str
    source_url: str
    fallback_url: str | None
    format: str
    status: str


READ_SOURCE_ROWS_SQL = """
    SELECT e.id, e.card_title, e.source_url, e.fallback_url, e.format, e.status
    FROM document_editions e
    JOIN documents d ON d.id = e.document_id
    WHERE d.visibility = 'public'
"""


def read_source_rows(conn: psycopg.Connection) -> list[SourceRow]:
    """Every public edition, whatever its status: app/sources.py decides what each
    status means, so that rule can be tested without a database."""
    return [SourceRow(*row) for row in conn.execute(READ_SOURCE_ROWS_SQL).fetchall()]


# --- Sync: the file into the tables ------------------------------------------

UPSERT_DOCUMENT_SQL = """
    INSERT INTO documents
        (id, domain, owning_department, audience, visibility, time_sensitive, title)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        domain = EXCLUDED.domain,
        owning_department = EXCLUDED.owning_department,
        audience = EXCLUDED.audience,
        visibility = EXCLUDED.visibility,
        time_sensitive = EXCLUDED.time_sensitive,
        title = EXCLUDED.title
"""

# The update list is the rule in code: status, parser_version, quality_report and the
# activation fields aren't in it, so a sync can't change them on an existing edition.
UPSERT_EDITION_SQL = """
    INSERT INTO document_editions
        (id, document_id, label, card_title, effective_from, review_by, retrieved_at,
         last_updated, language, format, source_url, fallback_url, course_tables, sha256,
         status, parser_version, quality_report, activated_by, activated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, CASE WHEN %s THEN now() END)
    ON CONFLICT (id) DO UPDATE SET
        document_id = EXCLUDED.document_id,
        label = EXCLUDED.label,
        card_title = EXCLUDED.card_title,
        effective_from = EXCLUDED.effective_from,
        review_by = EXCLUDED.review_by,
        retrieved_at = EXCLUDED.retrieved_at,
        last_updated = EXCLUDED.last_updated,
        language = EXCLUDED.language,
        format = EXCLUDED.format,
        source_url = EXCLUDED.source_url,
        fallback_url = EXCLUDED.fallback_url,
        course_tables = EXCLUDED.course_tables,
        sha256 = EXCLUDED.sha256
"""

# Until A2.4's loaders produce real values (docs/architecture.md, section 3.2).
UNVERSIONED_PARSER = "unversioned"
INITIAL_ACTIVATOR = "registry sync --initial"

COUNTED_TABLES = (
    "documents",
    "document_editions",
    "document_chunks",
    "courses",
    "course_prerequisites",
)


def _upsert_document(conn: psycopg.Connection, document: Document) -> None:
    conn.execute(
        UPSERT_DOCUMENT_SQL,
        (
            document.id,
            document.domain,
            document.owning_department,
            document.audience,
            document.visibility,
            document.time_sensitive,
            Jsonb({"en": document.title_en, "fr": document.title_fr}),
        ),
    )


def _upsert_edition(conn: psycopg.Connection, edition: Edition, *, active: bool) -> None:
    conn.execute(
        UPSERT_EDITION_SQL,
        (
            edition.id,
            edition.document_id,
            edition.label,
            edition.card_title,
            edition.effective_from,
            edition.review_by,
            edition.retrieved_at,
            edition.last_updated,
            edition.language,
            edition.format,
            edition.source_url,
            edition.fallback_url,
            edition.course_tables,
            edition.sha256,
            "active" if active else "draft",
            UNVERSIONED_PARSER,
            Jsonb({}),
            INITIAL_ACTIVATOR if active else None,
            active,
        ),
    )


def _check_can_sync(registry: Registry, existing: int, *, initial: bool) -> None:
    if initial:
        if existing:
            raise RegistryError(
                f"--initial is only for empty tables, and document_editions has {existing} "
                "rows. Nothing changed. Use plain sync."
            )
        for document in registry.documents:
            if len(document.editions) > 1:
                raise RegistryError(
                    f"--initial marks every edition active, but document {document.id!r} has "
                    f"{len(document.editions)} and only one may be. Nothing changed."
                )
    elif not existing:
        # Everything would go in as draft: no edition would be live, and the exit code
        # would still say success.
        raise RegistryError(
            "document_editions is empty, so plain sync would leave nothing active. "
            "Nothing changed. Use sync --initial."
        )


def sync(conn: psycopg.Connection, registry: Registry, *, initial: bool = False) -> None:
    """Copy the registry to the tables, all of it or none of it."""
    with conn.transaction():
        existing = conn.execute("SELECT count(*) FROM document_editions").fetchone()[0]
        _check_can_sync(registry, existing, initial=initial)
        for document in registry.documents:
            _upsert_document(conn, document)
        for edition in registry.editions:
            _upsert_edition(conn, edition, active=initial)


def table_counts(conn: psycopg.Connection) -> dict[str, int]:
    # The names are this module's constants, never input.
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in COUNTED_TABLES
    }


def status_counts(conn: psycopg.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT status, count(*) FROM document_editions GROUP BY status ORDER BY status"
    ).fetchall()
    return dict(rows)


def editions_not_in_file(conn: psycopg.Connection, registry: Registry) -> list[str]:
    """Editions only the database has. Left as they are: status lives there."""
    known = {edition.id for edition in registry.editions}
    rows = conn.execute("SELECT id FROM document_editions ORDER BY id").fetchall()
    return [row[0] for row in rows if row[0] not in known]


def _run_sync(*, initial: bool) -> int:
    registry = load_registry()
    conn = get_owner_connection()
    try:
        sync(conn, registry, initial=initial)
        counts = table_counts(conn)
        statuses = status_counts(conn)
        only_in_database = editions_not_in_file(conn, registry)
    finally:
        conn.close()

    for table, count in counts.items():
        print(f"[registry] {table}: {count}")
    print(f"[registry] edition status: {statuses}")
    if only_in_database:
        print(f"[registry] in the database but not the file, left as they are: {only_in_database}")
    if not counts["documents"] or not counts["document_editions"]:
        print("[registry] FAILED: documents or document_editions has 0 rows")
        return 1
    print("[registry] sync done")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The document registry.")
    commands = parser.add_subparsers(dest="command", required=True)
    sync_command = commands.add_parser("sync", help="Copy data/registry.toml to the tables")
    sync_command.add_argument(
        "--initial",
        action="store_true",
        help="Only on empty tables: mark every edition in the file active",
    )
    args = parser.parse_args(argv)
    try:
        return _run_sync(initial=args.initial)
    except RegistryError as e:
        print(f"[registry] refused: {e}")
        return 1
    except psycopg.Error as e:
        print(f"[registry] failed: {type(e).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
