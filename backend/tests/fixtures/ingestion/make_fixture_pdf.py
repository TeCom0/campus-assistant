"""Write fixture_finance_fees.pdf: a small two-page text PDF for the ingestion tests.

The PDF is written by hand (no library), so the fixture has no dependency and every
byte is explained here. Run it from anywhere, then update its sha256 in
fixture_registry.toml:

    python backend/tests/fixtures/ingestion/make_fixture_pdf.py

PDF basics used here: a file is numbered objects, then a cross-reference table giving
each object's byte offset, then a trailer naming the root. A page's text is a content
stream: BT ... ET is a text block, Tf picks the font and size, TL the line spacing, Td
moves to the first line, Tj draws a string, and T* moves to the next line.
"""

from pathlib import Path

OUT = Path(__file__).with_name("fixture_finance_fees.pdf")

PAGES = [
    [
        "Student Fees and Payments",
        "TEST FIXTURE: invented text for ingestion tests. This is not a university document.",
        "",
        "Payment deadlines",
        "Tuition for the fall semester must be paid in full before 15 September.",
        "Tuition for the spring semester must be paid in full before 31 January.",
        "A late payment fee of 500 MAD is charged once per semester on any unpaid balance.",
        "",
        "Installment plan",
        "Students may split tuition into three equal installments per semester.",
        "The installment plan must be requested from the Fixture Finance Office",
        "during the first two weeks of the semester.",
    ],
    [
        "Refunds",
        "A student who withdraws from the university before the first day of classes",
        "receives a full refund of tuition, minus a processing fee of 1,000 MAD.",
        "No tuition refund is given after the end of the fourth week of classes.",
        "",
        "Holds",
        "A student with an unpaid balance cannot register for the next semester",
        "and cannot receive an official transcript until the balance is paid.",
    ],
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content_stream(lines: list[str]) -> bytes:
    parts = ["BT", "/F1 11 Tf", "14 TL", "72 740 Td"]
    for n, line in enumerate(lines):
        if n:
            parts.append("T*")
        parts.append(f"({_escape(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1")


def build_pdf(pages: list[list[str]]) -> bytes:
    # Object numbers: 1 catalog, 2 page tree, 3 font, then a page and its content per page.
    page_ids = [4 + 2 * n for n in range(len(pages))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{p} 0 R" for p in page_ids)
            + f"] /Count {len(pages)} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_id, lines in zip(page_ids, pages, strict=True):
        stream = _content_stream(lines)
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        ).encode()
        objects[page_id + 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    count = max(objects) + 1
    out += f"xref\n0 {count}\n".encode()
    out += b"0000000000 65535 f \n"
    for number in range(1, count):
        out += f"{offsets[number]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


if __name__ == "__main__":
    OUT.write_bytes(build_pdf(PAGES))
    print(f"wrote {OUT.name}: {OUT.stat().st_size} bytes")
