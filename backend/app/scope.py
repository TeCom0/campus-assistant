"""What the assistant covers, in words, generated from the registry.

    python -m app.scope     # rewrite both JSON files, then commit them

Neither image can read data/registry.toml: the API's holds only backend/app, and the
frontend's build sees only frontend/. So the text is written to a committed JSON file
inside each one, and tests/test_scope.py fails if either stops matching the registry.

A case this module has no wording for stops with a ScopeError. A wrong sentence about what
the assistant covers would be worse than a failed build.
"""

import json
import sys
from pathlib import Path

from app.registry import Document, Registry, RegistryError, load_registry

BACKEND_SCOPE_PATH = Path(__file__).with_name("scope.json")
# backend/app/scope.py -> the repo root.
FRONTEND_SCOPE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "scope.json"

GENERATED_NOTE = "Generated from data/registry.toml by python -m app.scope. Don't edit by hand."

# The wording for each domain the registry uses. "prompt" and "topics" go to the model.
# "page" and "pages" name the documents other than the catalog, so the catalog's domain
# has none yet: a second academic document has to say how it should be described.
DOMAIN_WORDS = {
    "academic": {
        "prompt": "academic policies, course catalog descriptions",
        "tool": "academic catalog",
        "topics": [
            "academic policies",
            "course requirements",
            "grading",
            "registration",
            "admissions",
        ],
    },
    "scholarships": {
        "prompt": "scholarship information",
        "page": "scholarship page",
        "pages": "scholarship pages",
        "topics": ["scholarships/fellowships"],
    },
}


class ScopeError(Exception):
    """The registry holds something this module can't describe yet."""


def _words(document: Document, key: str) -> str | list[str]:
    try:
        return DOMAIN_WORDS[document.domain][key]
    except KeyError:
        raise ScopeError(
            f"no {key!r} wording for {document.id!r} in domain {document.domain!r}: "
            "add it to DOMAIN_WORDS"
        ) from None


def _check_one_edition_each(registry: Registry) -> None:
    # The file doesn't know which edition is in force: that's the database's status,
    # and A2.3 is what decides it. Naming one here would be a guess.
    for document in registry.documents:
        if len(document.editions) != 1:
            raise ScopeError(
                f"{document.id!r} has {len(document.editions)} editions: "
                "this text can only name a document with exactly one"
            )


def _check_all_in_english(registry: Registry) -> None:
    # The search tool's query_en argument tells the model "the documents are in English".
    for edition in registry.editions:
        if edition.language != "en":
            raise ScopeError(
                f"{edition.id!r} is in {edition.language!r}: the search tool's query_en "
                "argument says the documents are in English"
            )


def _other_documents(registry: Registry, catalog: Document) -> list[tuple[str, int]]:
    """The documents besides the catalog, as (name, how many), in registry order."""
    counts: dict[str, tuple[Document, int]] = {}
    for document in registry.documents:
        if document.id != catalog.id:
            _, count = counts.get(document.domain, (document, 0))
            counts[document.domain] = (document, count + 1)
    return [
        (_words(document, "page" if count == 1 else "pages"), count)
        for document, count in counts.values()
    ]


def _any_of(topics: list[str]) -> str:
    """["a", "b", "c"] -> "a, b, or c"."""
    if len(topics) == 1:
        return topics[0]
    return ", ".join(topics[:-1]) + ", or " + topics[-1]


def render_scope(registry: Registry) -> dict[str, str]:
    """Every sentence fragment that says what the assistant covers."""
    _check_one_edition_each(registry)
    _check_all_in_english(registry)

    edition = registry.course_tables_edition()
    catalog = registry.document_of(edition.id)
    # "2024-2025" in the registry, "2024–2025" wherever it's shown.
    label = edition.label.replace("-", "–")
    others = _other_documents(registry, catalog)
    names = [name for name, _ in others]

    # One entry per domain, in registry order.
    by_domain = list({document.domain: document for document in registry.documents}.values())
    tool_documents = " and ".join([_words(catalog, "tool"), *names])

    return {
        "_generated": GENERATED_NOTE,
        # For the model.
        "prompt_documents": ", ".join(_words(document, "prompt") for document in by_domain),
        "tool_documents": tool_documents,
        "tool_topics": _any_of(
            [topic for document in by_domain for topic in _words(document, "topics")]
        ),
        # For the interface.
        "catalog_label": label,
        "catalog_card_title": edition.card_title,
        "first_screen_documents": " and ".join(
            [f"public {label} {catalog.title_en}", *(f"AUI's {name}" for name in names)]
        ),
        "about_documents": " and ".join([f"{label} {catalog.title_en}", *names]),
        "meta_description": (
            "An unofficial student project: answers about Al Akhawayn University's public "
            f"{tool_documents}, in English or French, with their sources."
        ),
        "ingestion_documents": " + ".join(
            ["catalog PDF", *(f"{count} {name}" for name, count in others)]
        ),
    }


def load_scope() -> dict[str, str]:
    """The generated text, as the API reads it: the JSON file, never the registry file."""
    return json.loads(BACKEND_SCOPE_PATH.read_text(encoding="utf-8"))


def _write(path: Path, scope: dict[str, str]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(scope, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    try:
        scope = render_scope(load_registry())
    except (RegistryError, ScopeError) as e:
        print(f"SCOPE FAILED: {e}", file=sys.stderr)
        return 1
    for path in (BACKEND_SCOPE_PATH, FRONTEND_SCOPE_PATH):
        _write(path, scope)
        print(f"[scope] wrote {path}: {path.stat().st_size} bytes, {len(scope)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
