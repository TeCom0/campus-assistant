"""Human-readable, localized labels for tool_call SSE events.

Only distinguishes English vs. French (this project's actual scope, not
arbitrary language support). The language comes from
app.agent.language.detect_language; when that's unsure (None), labels are
in English.

A student reads these lines while the answer is held, and the gate doesn't check them, so
they hold no text the model wrote: a jailbreak could otherwise write into the search query.
A course code is shown only if it has a course code's shape.
"""

import re

_TEMPLATES = {
    "search_documents": {
        "en": "Searching the documents...",
        "fr": "Recherche dans les documents...",
    },
    "query_courses": {
        "en": "Looking up course {code}",
        "fr": "Recherche du cours {code}",
    },
    "query_courses_chain": {
        "en": "Looking up course {code} and its prerequisite chain",
        "fr": "Recherche du cours {code} et de sa chaîne de prérequis",
    },
    "query_courses_no_code": {
        "en": "Looking up a course",
        "fr": "Recherche d'un cours",
    },
}
_FALLBACK = {
    "en": "Using tool {tool}",
    "fr": "Utilisation de l'outil {tool}",
}

# "ACC 2302", "MTH1305", "CSC 3326L": letters, an optional space, digits.
_COURSE_CODE_RE = re.compile(r"[A-Z]{2,4} ?\d{3,4}[A-Z]?")


def build_tool_call_label(tool: str, args: dict, language: str | None) -> str:
    """Build a human-readable label for a tool_call event, in `language` ('en'/'fr'/None)."""
    lang = language if language == "fr" else "en"

    if tool == "search_documents":
        return _TEMPLATES["search_documents"][lang]

    if tool == "query_courses":
        code = str(args.get("code", "")).strip().upper()
        if not _COURSE_CODE_RE.fullmatch(code):
            return _TEMPLATES["query_courses_no_code"][lang]
        key = "query_courses_chain" if args.get("follow_prerequisites") else "query_courses"
        return _TEMPLATES[key][lang].format(code=code)

    return _FALLBACK[lang].format(tool=tool)
