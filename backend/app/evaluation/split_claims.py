"""Stage 2 of the faithfulness evaluation: split each saved answer into claims
and decide which passages each claim is checked against. Deterministic (no
LLM), so it can be re-run at any time for free; the judge and the hand labels
both read its output, so their claim ids match.

An answer is first cut into blocks (paragraphs, list items, table rows), then
blocks into sentences. Each sentence is a candidate claim. Which citation
covers it -- what a student would read it as backed by -- is decided by the
first rule that applies:

  own          the sentence has its own [N] markers
  block        another sentence of the same paragraph / list item / table row
               has markers ("A. B [2]." -- [2] covers both sentences)
  lead_in      a list item or table row with no markers takes the markers of
               the nearest preceding cited block in the same section (the
               "...among three courses:" sentence before a list or table)
  source_line  blocks that say where the answer comes from rather than state
               a fact: a "Source: ... [1]" line, markers alone on a line, a
               closing "This information is taken from the catalog [5]", a
               citation key ("Holds and form requirement: [4]"), a reference
               entry ("[1] (repeat policy: ...)"), or an item under a
               "Sources" / "Key citations" heading. Their markers together
               cover every claim still unassigned. (All seen in run 1.)
  uncited      none of the above; judged against all of the answer's passages
               and reported separately

Prose paragraphs don't inherit (lead_in): a new paragraph usually starts a new
point, so carrying a marker over would credit a citation the model never gave.
Headings, table header rows and source lines aren't claims. Filler and advice
("check with an advisor") can't be told apart from facts reliably in code;
the judge and the hand labels mark those "no_claim" instead.

Two kinds of sentence state nothing about the university and are excluded
from faithfulness scoring (field `exclude`; never judged, never counted):
  refusal   "I couldn't find ..." / "Je ne dispose pas ..." -- whether the
            answer should have declined is checked per answer instead
            (report.py: false and missed refusals)
  lead_in   a short "The main options are:" introducing a list
Both rules are deliberately tight (see exclusion_reason): keeping a fragment
only adds a no_claim for the judge, but dropping a fact could hide an
unsupported claim. Exclusion adds a field; claim ids never change.

Usage (from backend/):
    python -m app.evaluation.split_claims --run 1
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

from app.agent.citations import CITATION_MARKER_RE, cited_markers
from app.evaluation.generate_faithfulness_answers import EVAL_SET_PATH, RESULTS_DIR

HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
# A line that is only bold text, e.g. "**Eligibility:**", used as a heading.
BOLD_HEADING_RE = re.compile(r"^(\*\*|__)[^*_]+\1\s*:?$")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+(.*)$")
HORIZONTAL_RULE_RE = re.compile(r"^([-*_])(\s*\1){2,}$")
TABLE_SEPARATOR_RE = re.compile(r"^\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?$")
TABLE_LINE_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_MARKERS = r"(?:\s*" + CITATION_MARKER_RE.pattern + r")+"

# Not claims but statements of where claims come from; their markers cover the
# answer's otherwise uncited claims (rule source_line):
# "Source: AUI catalog [1]" / "Sources : [1], [3]"
SOURCE_LINE_RE = re.compile(r"^(sources?|références?|references?)\s*:", re.IGNORECASE)
# items under a heading such as "Sources", "Key citations", "Références"
SOURCE_HEADING_RE = re.compile(
    r"^((key|main)\s+)?(sources?|références?|references?|citations?)\b", re.IGNORECASE
)
# a citation key, "Holds and form requirement: [4]": a short label, a colon,
# then only markers. Unlike a lead-in, "You need one of these [3]:", whose
# marker comes before the colon.
CITATION_KEY_RE = re.compile(r"^[^.!?\[\]]{1,80}:" + _MARKERS + r"\s*$")
# a reference entry, "[1] (repeat policy: "...")": starts with its marker
REFERENCE_ENTRY_RE = re.compile(r"^" + CITATION_MARKER_RE.pattern)
# a closing attribution, "This information is taken from the AUI academic
# catalog. [5]" / "Ces informations proviennent du catalogue [2]."
ATTRIBUTION_RE = re.compile(
    r"^(this|the above|these|all (of )?this|ces|cette|les|toutes ces)\s+"
    r"(information|informations|details|détails|rules|règles|answer|réponse)\b"
    r".{0,60}\b(from|based on|according to|provien\w*|tir[ée]\w*|issu\w*|extrait\w*|"
    r"selon|d[’']après)\b",
    re.IGNORECASE,
)

# Markers placed after the sentence's punctuation (".[2]", ". [2]", " .[2]")
# belong to that sentence: moved before the punctuation before splitting.
_MARKERS_AFTER_PUNCTUATION_RE = re.compile(r"\s*([.!?])(" + _MARKERS + r")")
# A sentence ends at . ! or ? (plus closing quotes / Markdown emphasis), then
# whitespace, then something that starts a sentence. French puts a space
# before ? and ! and inside guillemets ("« C'est la règle. »"), which the
# optional \s? allow. "3.50" never matches: no space after the ".".
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s?[\"'”»’)*_])*\s+(?=[\"'«“(*_]*\s?[A-ZÀ-ÖØ-Þ0-9])")
ABBREVIATIONS = {
    "e.g.", "i.e.", "etc.", "vs.", "no.", "dr.", "mr.", "mrs.", "ms.", "st.",
    "p.", "pp.", "ex.", "cf.", "approx.", "min.", "max.", "art.",
}  # fmt: skip

# Exclusions (see the module docstring). A refusal must START the sentence --
# after at most an apology and a "based on ...," clause -- so a sentence that
# speculates first and refuses at the end ("Il est possible que ... mais je ne
# dispose pas de sources", run 1 fulbright_fr#2) is still judged.
REFUSAL_RE = re.compile(
    r"^(?:I'm sorry,? but |je suis désolée?,? mais )?(?:based on [^,]+, )?"
    r"(?:I (?:could not|couldn't|can't|cannot|did not|didn't|was unable to) find"
    r"|I (?:don't|do not) have"
    r"|je n'ai (?:pas )?trouvé|je ne dispose (?:pas|d'aucune)|je ne sais pas)\b",
    re.IGNORECASE,
)
LEAD_IN_MAX_WORDS = 6
# A digit (course codes included) makes a lead-in a fact ("ACC 2301 requires one of:").
DIGIT_RE = re.compile(r"\d")
# Typographic apostrophes and narrow/non-breaking spaces, as the model writes them.
_TYPOGRAPHY = str.maketrans({"’": "'", " ": " ", " ": " "})


@dataclass
class Block:
    type: str  # paragraph | list_item | table_row | table_header | heading | source_line
    text: str
    header: list[str] = field(default_factory=list)  # table rows: the header's cells


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _without_emphasis(text: str) -> str:
    return text.replace("*", "").replace("_", "").strip()


def _plain(text: str) -> str:
    """Text without markers and Markdown emphasis, for the source-line checks."""
    return _without_emphasis(CITATION_MARKER_RE.sub("", text)).lstrip("( ")


def parse_blocks(answer: str) -> list[Block]:
    blocks: list[Block] = []
    open_block: Block | None = None  # paragraph or list item taking continuation lines
    table_header: list[str] | None = None

    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            open_block, table_header = None, None
            continue
        if stripped.startswith("|"):
            open_block = None
            if TABLE_SEPARATOR_RE.match(stripped):
                continue
            # "<br>" separates lines inside a cell; the row stays one claim.
            cells = _cells(TABLE_LINE_BREAK_RE.sub(" ", stripped))
            if table_header is None:
                table_header = cells
                blocks.append(Block("table_header", " | ".join(cells)))
            else:
                text = "; ".join(f"{h}: {c}" if h else c for h, c in zip(table_header, cells) if c)
                blocks.append(Block("table_row", text, header=table_header))
            continue
        table_header = None

        if HORIZONTAL_RULE_RE.match(stripped):
            open_block = None
            continue
        heading = HEADING_RE.match(stripped)
        if heading or BOLD_HEADING_RE.match(stripped):
            blocks.append(Block("heading", heading.group(1) if heading else stripped))
            open_block = None
            continue
        item = LIST_ITEM_RE.match(line)
        if item:
            open_block = Block("list_item", item.group(1).strip())
            blocks.append(open_block)
            continue

        stripped = stripped.lstrip("> ").strip()  # blockquote
        if open_block is not None:
            # A Markdown line break inside a paragraph, or a line continuing a
            # list item: same block.
            open_block.text += " " + stripped
        else:
            open_block = Block("paragraph", stripped)
            blocks.append(open_block)

    # A "Sources" heading covers the list items right under it; the next prose
    # paragraph (e.g. closing advice) or heading ends it.
    in_sources_list = False
    for block in blocks:
        if block.type == "heading":
            in_sources_list = bool(SOURCE_HEADING_RE.match(_plain(block.text)))
            continue
        plain, has_markers = _plain(block.text), bool(cited_markers(block.text))
        is_source = (
            SOURCE_LINE_RE.match(plain)
            or CITATION_KEY_RE.match(_without_emphasis(block.text))
            or REFERENCE_ENTRY_RE.match(_without_emphasis(block.text))
            # markers alone on their own line: "...\n\n[1]"
            or (has_markers and not re.search(r"\w", plain))
            or (has_markers and ATTRIBUTION_RE.match(plain))
        )
        if block.type == "list_item" and in_sources_list:
            is_source = True
        elif block.type != "list_item":
            in_sources_list = False
        if is_source and block.type in ("paragraph", "list_item"):
            block.type = "source_line"
    return blocks


def split_sentences(text: str) -> list[str]:
    text = _MARKERS_AFTER_PUNCTUATION_RE.sub(lambda m: " " + m.group(2).strip() + m.group(1), text)
    sentences, start = [], 0
    for end in _SENTENCE_END_RE.finditer(text):
        sentence = text[start : end.end()].strip()
        last_word = sentence.split()[-1].lower().strip("*_")
        if last_word in ABBREVIATIONS or re.fullmatch(r"[a-z]\.", last_word):
            continue  # "e.g. The", "J. Smith": not a sentence end
        sentences.append(sentence)
        start = end.end()
    rest = text[start:].strip()
    if rest:
        sentences.append(rest)
    return sentences


def _has_content(sentence: str) -> bool:
    return bool(re.search(r"\w", CITATION_MARKER_RE.sub("", sentence)))


def exclusion_reason(sentence: str) -> str | None:
    """ "refusal", "lead_in", or None for a claim to judge. Neither kind may carry
    its own [N] marker: a cited sentence claims something about its passage."""
    text = sentence.translate(_TYPOGRAPHY).strip()
    if CITATION_MARKER_RE.search(text):
        return None
    if REFUSAL_RE.search(text):
        return "refusal"
    plain = _without_emphasis(text)
    if (
        plain.endswith(":")
        and len(plain[:-1].split()) <= LEAD_IN_MAX_WORDS
        and not DIGIT_RE.search(plain)
    ):
        return "lead_in"
    return None


def extract_claims(answer: str, passage_markers: set[int]) -> list[dict]:
    """Claims in `answer`, each with the markers it is checked against.

    `passage_markers` are the markers the tools actually returned; a claim
    whose markers are all outside them cites nothing real and is labelled
    unsupported here, without the judge.
    """
    claims: list[dict] = []
    lead_in: set[int] = set()  # nearest preceding cited block in this section
    source_markers: set[int] = set()

    for block in parse_blocks(answer):
        block_markers = cited_markers(block.text)
        if block.type == "heading":
            lead_in = block_markers
            continue
        if block.type == "table_header":
            lead_in = block_markers or lead_in
            continue
        if block.type == "source_line":
            source_markers |= block_markers
            continue

        sentences = [block.text] if block.type == "table_row" else split_sentences(block.text)
        for sentence in sentences:
            if not _has_content(sentence):
                continue
            own = cited_markers(sentence)
            if own:
                kind, markers = "own", own
            elif block_markers:
                kind, markers = "block", block_markers
            elif block.type in ("list_item", "table_row") and lead_in:
                kind, markers = "lead_in", lead_in
            else:
                kind, markers = "uncited", set()
            claims.append(
                {"text": sentence, "block_type": block.type, "kind": kind, "markers": markers}
            )
        if block_markers:
            lead_in = block_markers

    for claim in claims:
        if claim["kind"] == "uncited" and source_markers:
            claim["kind"], claim["markers"] = "source_line", source_markers
        markers = claim["markers"]
        claim["markers"] = sorted(markers)
        claim["invalid_markers"] = sorted(markers - passage_markers)
        claim["exclude"] = exclusion_reason(claim["text"])
        # An excluded sentence asserts nothing, so an invalid inherited marker
        # doesn't make it unsupported either.
        invalid_only = markers and not markers & passage_markers
        claim["auto_label"] = "unsupported" if invalid_only and not claim["exclude"] else None
    return claims


def split_run(run: int) -> list[dict]:
    answers_path = RESULTS_DIR / f"answers_run{run}.jsonl"
    with answers_path.open(encoding="utf-8") as f:
        answers = [json.loads(line) for line in f if line.strip()]
    duplicates = [i for i, n in Counter(a["id"] for a in answers).items() if n > 1]
    if duplicates:
        raise SystemExit(f"{answers_path.name} has duplicate ids (two runs at once?): {duplicates}")
    sets = {q["id"]: q["set"] for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))}

    all_claims = []
    for a in answers:
        if a["error"] or not a["answer"].strip():
            print(f"{a['id']:<28} no answer ({a['error'] or 'empty'}), no claims")
            continue
        passage_markers = {p["marker"] for p in a["passages"]}
        claims = extract_claims(a["answer"], passage_markers)
        for n, claim in enumerate(claims, start=1):
            all_claims.append(
                {
                    "claim_id": f"{a['id']}#{n}",
                    "id": a["id"],
                    "run": run,
                    "language": a["language"],
                    "set": sets[a["id"]],
                    **claim,
                }
            )
        kinds = Counter(c["kind"] for c in claims)
        print(f"{a['id']:<28} {len(claims):>2} claims  {dict(sorted(kinds.items()))}")

    out_path = RESULTS_DIR / f"claims_run{run}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for claim in all_claims:
            f.write(json.dumps(claim, ensure_ascii=False) + "\n")
    totals = Counter(c["kind"] for c in all_claims)
    auto = sum(1 for c in all_claims if c["auto_label"])
    excluded = Counter(c["exclude"] for c in all_claims if c["exclude"])
    print(f"\n{len(all_claims)} claims from {len(answers)} answers -> {out_path.name}")
    print(f"by kind: {dict(sorted(totals.items()))}; invalid citations (auto-unsupported): {auto}")
    print(f"excluded from scoring: {dict(sorted(excluded.items()))}")
    return all_claims


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=int, default=1)
    split_run(parser.parse_args().run)
