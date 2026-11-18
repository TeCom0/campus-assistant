"""Extract the text of every registered edition (data/raw/) into data/processed/.

Driven by the registry (A2.4 step 2): each edition's file, data/raw/<id>.<format>, passes
the checks in gates.py, is read by its format's loader (loaders.py) and sanitised
(sanitise.py; what was removed is printed). A file the registry doesn't name is reported
as ignored and never read.

Every edition is checked and extracted before anything is written, so one refusal
leaves data/processed as it was: the command prints why and exits 1.
"""

import sys
from pathlib import Path

from app.ingestion.gates import IngestRefused, extract_edition, ignored_files
from app.registry import Registry, load_registry

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def clean_all(
    registry: Registry | None = None, raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR
) -> None:
    registry = load_registry() if registry is None else registry
    for name in ignored_files(registry, raw_dir):
        print(f"ignored (not in the registry): {name}")

    extracted = {
        edition.id: extract_edition(registry, edition.id, raw_dir) for edition in registry.editions
    }

    processed_dir.mkdir(parents=True, exist_ok=True)
    for edition in registry.editions:
        result = extracted[edition.id]
        dest = processed_dir / f"{edition.id}.txt"
        dest.write_text(result.text, encoding="utf-8")
        print(
            f"extracted: {edition.filename} -> {dest.name} ({len(result.text)} chars; "
            f"removed {result.invisible_characters} invisible characters, "
            f"{result.hidden_elements} hidden elements)"
        )


def main(
    registry: Registry | None = None, raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR
) -> int:
    """clean_all, with a refusal printed and turned into exit code 1."""
    try:
        clean_all(registry, raw_dir, processed_dir)
    except IngestRefused as e:
        print(f"refused: {e}\nNothing changed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
