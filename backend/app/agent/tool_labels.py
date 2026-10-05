"""Human-readable, localized labels for tool_call SSE events.

Only distinguishes English vs. French (this project's actual scope, not
arbitrary language support), and defaults to English unless the question is
confidently detected as French -- langdetect is unreliable on short/
ambiguous text (e.g. "Hello" -> misdetected as Finnish, a bare course code
-> misdetected as Tagalog, tested directly), so treating "anything but a
confident fr" as English is the safe choice, not a real detection bug.
"""

from langdetect import DetectorFactory, LangDetectException, detect

# langdetect is non-deterministic by default (probabilistic sampling
# internally) -- without a fixed seed, the same input text could return
# different results across runs/requests.
DetectorFactory.seed = 0

_TEMPLATES = {
    "search_documents": {
        "en": 'Searching documents for "{query}"',
        "fr": "Recherche dans les documents pour « {query} »",
    },
    "query_courses": {
        "en": "Looking up course {code}",
        "fr": "Recherche du cours {code}",
    },
    "query_courses_chain": {
        "en": "Looking up course {code} and its prerequisite chain",
        "fr": "Recherche du cours {code} et de sa chaîne de prérequis",
    },
}
_FALLBACK = {
    "en": "Using tool {tool}",
    "fr": "Utilisation de l'outil {tool}",
}


def detect_language(text: str) -> str:
    """Return 'fr' only if confidently detected as French, else 'en'."""
    try:
        return "fr" if detect(text) == "fr" else "en"
    except LangDetectException:
        return "en"


def build_tool_call_label(tool: str, args: dict, language: str) -> str:
    """Build a human-readable label for a tool_call event, in `language` ('en'/'fr')."""
    lang = language if language == "fr" else "en"

    if tool == "search_documents":
        return _TEMPLATES["search_documents"][lang].format(query=args.get("query", ""))

    if tool == "query_courses":
        key = "query_courses_chain" if args.get("follow_prerequisites") else "query_courses"
        return _TEMPLATES[key][lang].format(code=args.get("code", ""))

    return _FALLBACK[lang].format(tool=tool)
