"""The checks a registered edition's file must pass before a parser reads it (A2.4 step 2).

Ingestion reads only the files of editions in the registry, and each one passes these,
in this order, or is refused with a message that says why:

1. visibility: the document is public. Any ingested passage can be sent to the LLM
   provider. The registry already refuses non_public; this is the second lock, in
   ingestion itself.
2. language: English only, until B3. Keyword search uses Postgres' `english` text-search
   configuration, which would stem French text wrongly and with no error.
3. format: one a loader exists for (loaders.UnsupportedFormat otherwise).
4. the file exists, and isn't over the size limit, checked before it is read.
5. its sha256 is the registry's: it is the file that was registered, not a re-download
   that changed or another file under the same name.
6. a PDF's page count is under the limit (reading the page tree, not the text).

Encrypted and scanned (near-empty) PDFs are checked by the dry run (step 5).
"""

import hashlib
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.loaders import Extracted, UnsupportedFormat, extract, loader_for
from app.registry import Document, Edition, Registry

MEGABYTE = 1024 * 1024
# Largest today: the catalog, 2.8 MB and 435 pages (CLAUDE.md, "A2.4 rule").
MAX_FILE_BYTES = {"pdf": 20 * MEGABYTE, "html": 2 * MEGABYTE}
MAX_PDF_PAGES = 1000
INGESTIBLE_LANGUAGES = {"en"}

# Files in data/raw that are never a source.
NOT_A_SOURCE = {".gitkeep"}


class IngestRefused(Exception):
    """An edition can't be ingested. The message names it and says why."""


def check_edition(document: Document, edition: Edition, path: Path) -> None:
    """Raise IngestRefused unless the edition's file passes every check."""
    where = f"{edition.id} ({path.name})"
    if document.visibility != "public":
        raise IngestRefused(f"{where}: document {document.id!r} isn't public")
    if edition.language not in INGESTIBLE_LANGUAGES:
        raise IngestRefused(
            f"{where}: language {edition.language!r} isn't ingested until French search "
            f"exists (B3); ingested: {', '.join(sorted(INGESTIBLE_LANGUAGES))}"
        )
    try:
        loader_for(edition.format, path)
    except UnsupportedFormat as e:
        raise IngestRefused(str(e)) from None
    if not path.is_file():
        raise IngestRefused(f"{where}: the file isn't there")

    size, limit = path.stat().st_size, MAX_FILE_BYTES[edition.format]
    if size > limit:
        raise IngestRefused(f"{where}: {size:,} bytes, over the {limit:,}-byte limit")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != edition.sha256:
        raise IngestRefused(
            f"{where}: sha256 is {digest}, the registry says {edition.sha256}. "
            "If the publisher changed the file, register it as a new edition"
        )

    if edition.format == "pdf":
        try:
            pages = len(PdfReader(path).pages)
        except PdfReadError as e:
            raise IngestRefused(f"{where}: can't be read as a PDF ({type(e).__name__})") from None
        if pages > MAX_PDF_PAGES:
            raise IngestRefused(f"{where}: {pages} pages, over the {MAX_PDF_PAGES}-page limit")


def extract_edition(registry: Registry, edition_id: str, raw_dir: Path) -> Extracted:
    """One registered edition's sanitised text, after its checks: data/raw/<id>.<format>
    only."""
    edition = registry.edition(edition_id)
    path = raw_dir / edition.filename
    check_edition(registry.document_of(edition_id), edition, path)
    return extract(path, edition.format)


def ignored_files(registry: Registry, raw_dir: Path) -> list[str]:
    """Files in raw_dir that no registered edition names: never read, only reported."""
    registered = {edition.filename for edition in registry.editions}
    return sorted(
        path.name
        for path in raw_dir.iterdir()
        if path.name not in registered and path.name not in NOT_A_SOURCE
    )
