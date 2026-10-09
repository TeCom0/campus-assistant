"""Builds the message list the agent sees for one /chat request: prior turns
(optional) followed by the current question.

Citation markers like [3] are numbered per request, so a marker from an
earlier answer would point at the wrong source now. They are stripped from
prior assistant turns before the agent sees them.
"""

import re

from app.agent.citations import CITATION_MARKER_RE
from app.config import MAX_HISTORY_MESSAGES

# The same marker pattern citations.py uses ("[3]" and "[2, 4]"), plus the
# whitespace before it, so "68 credits [2]." becomes "68 credits.".
_MARKER_WITH_SPACE = re.compile(r"\s*" + CITATION_MARKER_RE.pattern)


def strip_citation_markers(text: str) -> str:
    return _MARKER_WITH_SPACE.sub("", text)


def build_input_messages(
    question: str,
    history: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    prior = []
    for turn in (history or [])[-MAX_HISTORY_MESSAGES:]:
        content = turn["content"]
        if turn["role"] == "assistant":
            content = strip_citation_markers(content)
        prior.append({"role": turn["role"], "content": content})
    return [*prior, {"role": "user", "content": question}]
