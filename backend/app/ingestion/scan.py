"""Scanning an edition's text before it can go live (A2.4 step 4; docs/architecture.md, 4.4).

Every line a student could be shown, and that is sent to the LLM provider, is read for
what shouldn't be there. A hit is either refused outright or held for a person:

- refuse: a Moroccan national ID (CIN), and placeholder text (lorem ipsum). No decision
  can allow these.
- hold: phone numbers, email addresses, student numbers, bank account numbers, an
  honorific followed by a name, and instructions aimed at a model. Each needs a decision
  recorded in data/review/<edition id>.toml: allow, redact (the value is replaced in the
  text) or refuse (the whole edition). A hold without a decision refuses the edition.

Scanning supports human review; it doesn't replace it. Someone determined can word an
instruction so no pattern matches, which is why the other layers in section 2.5 exist.
The patterns were fixed in CLAUDE.md ("A2.4 rule") before they ran on any real file; a
pattern changed after seeing hits is changed in the open, with the reason.

    python -m app.ingestion.scan <edition id> [<edition id> ...]
    python -m app.ingestion.scan --all

prints each edition's hits and verdict, changes nothing, and exits 1 unless all pass.
"""

import argparse
import bisect
import re
import sys
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REVIEW_DIR = REPO_ROOT / "data" / "review"

# A separator inside a number: a space, dot or dash on the same line.
_SEP = r"[ .\-]?"

PATTERNS: dict[str, tuple[str, re.Pattern]] = {
    # kind: (action, pattern)
    "national_id": ("refuse", re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}\d{5,6}(?![A-Za-z0-9])")),
    "boilerplate": ("refuse", re.compile(r"lorem\s+ipsum|dolor\s+sit\s+amet", re.IGNORECASE)),
    "phone": (
        "hold",
        re.compile(rf"(?:\+212|(?<![\d+])0){_SEP}(?:\(0\){_SEP})?[5-7](?:{_SEP}\d){{8}}(?!\d)"),
    ),
    "email": ("hold", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    "student_number": (
        "hold",
        re.compile(r"student\s+(?:id|number|no\.?)\s*[:#]?\s*\d{4,}", re.IGNORECASE),
    ),
    "iban": ("hold", re.compile(r"(?<![A-Za-z0-9])MA(?:[ ]?\d){26}(?!\d)")),
    "rib": ("hold", re.compile(r"(?<![\d])\d(?:[ ]?\d){23}(?!\d)")),
    "honorific_name": ("hold", re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof)\b\.?[ ]+[A-Z][a-z]+")),
    "instruction": (
        "hold",
        re.compile(
            r"\b(?:ignore|disregard)\b[^.\n]{0,40}?\b(?:previous|prior|above)\b[^.]{0,20}?"
            r"\binstructions?\b"
            r"|\b(?:ignorez|oubliez)\b[^.]{0,40}?\binstructions?\b"
            r"|\byou\s+are\s+now\b"
            r"|\bsystem\s+prompt\b"
            r"|^[ \t]*(?:system|assistant|user)[ \t]*:"
            r"|<\|im_start\|>|\[INST\]|<<SYS>>",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
}
HOLD_KINDS = {kind for kind, (action, _) in PATTERNS.items() if action == "hold"}
DECISION_ACTIONS = {"allow", "redact", "refuse"}
PAGE_MARKER_RE = re.compile(r"^--- page (\d+) ---$", re.MULTILINE)


@dataclass(frozen=True)
class Hit:
    kind: str
    action: str  # "refuse" or "hold"
    value: str  # the match, whitespace collapsed (an email lower-cased)
    start: int  # offset in the text
    end: int
    line: int  # 1-based line of the text
    page: int | None  # PDF page, or None for a web page
    context: str  # the text around it, on one line


@dataclass(frozen=True)
class Decision:
    kind: str
    value: str  # an fnmatch pattern: "registrar@aui.ma", or "*@aui.ma"
    action: str  # allow, redact or refuse
    reason: str
    by: str


class DecisionsError(Exception):
    """The decisions file can't be used. The message says why."""


def _value(kind: str, matched: str) -> str:
    value = " ".join(matched.split())
    return value.lower() if kind == "email" else value


def scan_text(text: str) -> list[Hit]:
    """Every hit in a text, in order. Locations come from the text's own line breaks and
    "--- page N ---" markers (loaders.to_chunker_text writes them)."""
    line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
    pages = [(m.start(), int(m.group(1))) for m in PAGE_MARKER_RE.finditer(text)]
    page_offsets = [offset for offset, _ in pages]

    hits = []
    for kind, (action, pattern) in PATTERNS.items():
        for match in pattern.finditer(text):
            at = bisect.bisect_right(page_offsets, match.start()) - 1
            context = text[max(0, match.start() - 40) : match.end() + 40]
            hits.append(
                Hit(
                    kind=kind,
                    action=action,
                    value=_value(kind, match.group()),
                    start=match.start(),
                    end=match.end(),
                    line=bisect.bisect_right(line_starts, match.start()),
                    page=pages[at][1] if at >= 0 else None,
                    context=" ".join(context.split()),
                )
            )
    return sorted(hits, key=lambda h: (h.start, h.kind))


def load_decisions(path: Path) -> list[Decision]:
    """The recorded decisions for one edition; none if the file doesn't exist."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise DecisionsError(f"{path.name} isn't valid TOML: {e}") from None
    if set(data) - {"decision"}:
        raise DecisionsError(f"{path.name} must hold [[decision]] entries and nothing else")
    decisions = []
    for n, entry in enumerate(data.get("decision", []), start=1):
        where = f"{path.name}, decision {n}"
        if not isinstance(entry, dict) or set(entry) != {"kind", "value", "action", "reason", "by"}:
            raise DecisionsError(f"{where}: needs exactly kind, value, action, reason and by")
        if not all(isinstance(v, str) and v.strip() for v in entry.values()):
            raise DecisionsError(f"{where}: every field must be non-empty text")
        if entry["kind"] not in HOLD_KINDS:
            raise DecisionsError(
                f"{where}: kind {entry['kind']!r} can't be decided; held kinds: "
                f"{', '.join(sorted(HOLD_KINDS))} (a national ID or placeholder text is always refused)"
            )
        if entry["action"] not in DECISION_ACTIONS:
            raise DecisionsError(f"{where}: action must be one of {sorted(DECISION_ACTIONS)}")
        decisions.append(Decision(**entry))
    return decisions


@dataclass(frozen=True)
class ScanResult:
    hits: list[Hit]
    refusals: list[str]  # why the edition is refused; empty if it isn't
    undecided: list[Hit]  # held hits with no decision
    redacted: int  # how many values were replaced in the text
    unused: list[Decision]  # decisions that matched no hit: stale, to remove
    text: str  # the text after redaction

    @property
    def passed(self) -> bool:
        return not self.refusals and not self.undecided


def review(text: str, decisions: list[Decision]) -> ScanResult:
    """Scan a text and apply the recorded decisions: the first decision (in file order)
    whose kind and value pattern match a hit decides it."""
    hits = scan_text(text)
    refusals, undecided, to_redact, used = [], [], [], set()
    for hit in hits:
        if hit.action == "refuse":
            refusals.append(f"{hit.kind} {hit.value!r} at {_where(hit)}")
            continue
        n, decision = next(
            (
                (n, d)
                for n, d in enumerate(decisions)
                if d.kind == hit.kind and fnmatchcase(hit.value, d.value)
            ),
            (None, None),
        )
        if decision is None:
            undecided.append(hit)
            continue
        used.add(n)
        if decision.action == "refuse":
            refusals.append(f"{hit.kind} {hit.value!r} at {_where(hit)}: refused by decision")
        elif decision.action == "redact":
            to_redact.append(hit)

    redacted_text = text
    for hit in sorted(to_redact, key=lambda h: h.start, reverse=True):
        redacted_text = (
            redacted_text[: hit.start] + f"[{hit.kind} removed]" + redacted_text[hit.end :]
        )
    unused = [d for n, d in enumerate(decisions) if n not in used]
    return ScanResult(hits, refusals, undecided, len(to_redact), unused, redacted_text)


def _where(hit: Hit) -> str:
    return f"page {hit.page}, line {hit.line}" if hit.page is not None else f"line {hit.line}"


def print_report(edition_id: str, result: ScanResult) -> None:
    by_kind: dict[str, list[Hit]] = {}
    for hit in result.hits:
        by_kind.setdefault(hit.kind, []).append(hit)
    print(f"== {edition_id}: {len(result.hits)} hits")
    for kind, hits in by_kind.items():
        values = sorted({h.value for h in hits})
        print(f"  {kind} ({PATTERNS[kind][0]}): {len(hits)} hits, {len(values)} distinct")
        for value in values:
            first = next(h for h in hits if h.value == value)
            count = sum(1 for h in hits if h.value == value)
            print(f"    {value!r} x{count}, first at {_where(first)}: ...{first.context}...")
    for refusal in result.refusals:
        print(f"  REFUSED: {refusal}")
    undecided_values = sorted({(h.kind, h.value) for h in result.undecided})
    for kind, value in undecided_values:
        print(f"  NO DECISION: {kind} {value!r}")
    for decision in result.unused:
        print(f"  UNUSED DECISION (matches nothing): {decision.kind} {decision.value!r}")
    if result.redacted:
        print(f"  redacted: {result.redacted}")
    verdict = "pass" if result.passed else "refused" if result.refusals else "held"
    print(f"  verdict: {verdict}")


def main(argv: list[str] | None = None) -> int:
    # Imported here: gates reads PDFs, and nothing else in this module needs it.
    from app.ingestion.clean import RAW_DIR
    from app.ingestion.gates import IngestRefused, extract_edition
    from app.registry import load_registry

    parser = argparse.ArgumentParser(description="Scan editions; changes nothing.")
    parser.add_argument("editions", nargs="*")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    registry = load_registry()
    edition_ids = [e.id for e in registry.editions] if args.all else args.editions
    if not edition_ids:
        parser.error("name an edition, or --all")

    all_passed = True
    for edition_id in edition_ids:
        try:
            text = extract_edition(registry, edition_id, RAW_DIR).text
            decisions = load_decisions(REVIEW_DIR / f"{edition_id}.toml")
        except (IngestRefused, DecisionsError) as e:
            print(f"== {edition_id}: refused before scanning: {e}")
            all_passed = False
            continue
        result = review(text, decisions)
        print_report(edition_id, result)
        all_passed = all_passed and result.passed
    print("Nothing changed.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
