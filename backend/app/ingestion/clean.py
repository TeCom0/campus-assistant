"""Extract plain text from raw downloaded documents (data/raw/) into data/processed/."""

from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def extract_pdf_text(path: Path) -> str:
    """Extract text page by page, keeping page markers for later citation metadata."""
    reader = PdfReader(path)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"--- page {page_number} ---\n{text}")
    return "\n\n".join(pages)


def extract_html_text(path: Path) -> str:
    """Strip script/style/nav/header/footer noise and return the remaining visible text."""
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)


def clean_all() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for raw_file in sorted(RAW_DIR.iterdir()):
        if raw_file.name == ".gitkeep":
            continue

        if raw_file.suffix == ".pdf":
            text = extract_pdf_text(raw_file)
        elif raw_file.suffix == ".html":
            text = extract_html_text(raw_file)
        else:
            print(f"skip (unknown type): {raw_file.name}")
            continue

        dest = PROCESSED_DIR / f"{raw_file.stem}.txt"
        dest.write_text(text, encoding="utf-8")
        print(f"extracted: {raw_file.name} -> {dest.name} ({len(text)} chars)")


if __name__ == "__main__":
    clean_all()
