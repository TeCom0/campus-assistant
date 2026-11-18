"""Extract plain text from raw downloaded documents (data/raw/) into data/processed/.

The extraction itself is in loaders.py (one loader per format). This step still scans
the folder and skips unknown files, as before; A2.4 step 2 replaces the scan with the
registry, so only registered editions are read.
"""

from pathlib import Path

from app.ingestion.loaders import UnsupportedFormat, load_text

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def clean_all() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for raw_file in sorted(RAW_DIR.iterdir()):
        if raw_file.name == ".gitkeep":
            continue

        try:
            text = load_text(raw_file, raw_file.suffix.removeprefix("."))
        except UnsupportedFormat:
            print(f"skip (unknown type): {raw_file.name}")
            continue

        dest = PROCESSED_DIR / f"{raw_file.stem}.txt"
        dest.write_text(text, encoding="utf-8")
        print(f"extracted: {raw_file.name} -> {dest.name} ({len(text)} chars)")


if __name__ == "__main__":
    clean_all()
