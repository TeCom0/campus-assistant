"""Download raw source documents (see ../../../data/sources.md) into data/raw/."""

from pathlib import Path

import requests

# Mirrors data/sources.md. Kept as a plain list here (not parsed from the markdown)
# since there are only a handful of sources.
SOURCES = [
    {
        "filename": "academic_catalog_2024_2025.pdf",
        "url": "https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en",
    },
    {
        "filename": "prestigious_scholarships.html",
        "url": "https://aui.ma/prestigious-scholarship",
    },
    {
        "filename": "graduate_scholarships.html",
        "url": "https://aui.ma/admission-aid/graduates/scholarships",
    },
]

# data/raw/ lives at the repo root, three levels up from this file
# (ingestion -> app -> backend -> repo root).
DATA_RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def download_sources() -> None:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for source in SOURCES:
        dest = DATA_RAW_DIR / source["filename"]
        if dest.exists():
            print(f"skip (already downloaded): {dest.name}")
            continue

        print(f"downloading: {source['url']}")
        response = requests.get(source["url"], timeout=30, stream=True)
        response.raise_for_status()

        with open(dest, "wb") as f:
            f.writelines(response.iter_content(chunk_size=8192))

        print(f"saved: {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    download_sources()
