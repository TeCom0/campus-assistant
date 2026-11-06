"""Download the registry's documents (data/registry.toml) into data/raw/."""

from pathlib import Path

import requests

from app.registry import load_registry

# data/raw/ lives at the repo root, three levels up from this file
# (ingestion -> app -> backend -> repo root).
DATA_RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def download_sources() -> None:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for edition in load_registry().editions:
        dest = DATA_RAW_DIR / edition.filename
        if dest.exists():
            print(f"skip (already downloaded): {dest.name}")
            continue

        print(f"downloading: {edition.source_url}")
        response = requests.get(edition.source_url, timeout=30, stream=True)
        response.raise_for_status()

        with open(dest, "wb") as f:
            f.writelines(response.iter_content(chunk_size=8192))

        print(f"saved: {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    download_sources()
