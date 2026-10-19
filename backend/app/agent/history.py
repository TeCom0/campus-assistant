"""Builds the message list the agent sees for one /chat request: prior turns
(optional) followed by the current question.

Citation markers like [3] are numbered per request, so a marker from an
earlier answer would point at the wrong source now. They are stripped from
prior assistant turns before the agent sees them.

Fallback answers (built in code when the model failed to answer, see
graph._fallback_answer) are left out, the way the UI leaves out interrupted
answers: they say nothing about the question, and with their markers stripped
only "I couldn't finish this answer..." would remain for the model to imitate.
The student's question stays.
"""

import re

from app.agent.citations import CITATION_MARKER_RE
from app.agent.graph import is_fallback_answer
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
    # Filtered before the cap, so the cap counts only turns the model will see.
    kept = [
        turn
        for turn in history or []
        if not (turn["role"] == "assistant" and is_fallback_answer(turn["content"]))
    ]
    prior = []
    for turn in kept[-MAX_HISTORY_MESSAGES:]:
        content = turn["content"]
        if turn["role"] == "assistant":
            content = strip_citation_markers(content)
        prior.append({"role": turn["role"], "content": content})
    return [*prior, {"role": "user", "content": question}]
