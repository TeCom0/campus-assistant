"""The answer-level gate: the only uncited text a student reads is text written here.

A finished answer goes out only if a tool ran this turn and every marker in it is one a
tool returned. Anything else is replaced by a template. See docs/architecture.md, 2.4.

It's structural on purpose: it reads no meaning, so it costs no tokens and no wording can
talk it round. That has two limits. It can prove an answer has valid citations, never that
they support the claims, which stays the job of the evaluation. And it can't tell a good
answer that forgot its markers from a bad one, so it replaces both.
"""

from dataclasses import dataclass

from app.agent.citations import cited_markers, normalize_brackets
from app.scope import load_scope

_SCOPE = load_scope()

# Why an answer was replaced. Short and fixed, so they're safe to log: they hold nothing
# the student wrote or the model said.
NO_TOOL = "no_tool"
NO_CITATION = "no_citation"
INVENTED_MARKER = "invented_marker"

# No tool ran: a greeting, an off-topic question or a jailbreak.
SCOPE_TEMPLATE = {
    "en": (
        f"I answer questions about {_SCOPE['covers_en']}, and I cite where each answer comes "
        "from. Please ask me about those."
    ),
    "fr": (
        f"Je réponds aux questions sur {_SCOPE['covers_fr']}, en citant mes sources. "
        "Posez-moi une question à ce sujet."
    ),
}

# Tools ran, and the answer can't show what it rests on.
NOT_FOUND_TEMPLATE = {
    "en": (
        "I couldn't find this in the documents I have. Please try rephrasing your question, "
        "or ask the university office concerned."
    ),
    "fr": (
        "Je n'ai pas trouvé cette information dans mes documents. Essayez de reformuler votre "
        "question, ou adressez-vous au service concerné de l'université."
    ),
}


@dataclass(frozen=True)
class GateResult:
    answer: str
    # None when the answer passed. Otherwise why it was replaced.
    reason: str | None


def gate_answer(
    answer: str,
    *,
    tool_ran: bool,
    known_markers: set[int],
    language: str | None,
    fallback: bool = False,
) -> GateResult:
    """What the student reads, given the finished answer and what this turn's tools returned.

    fallback: the code-built answer for when the model failed twice. It's written in code
    already, and its markers are the passages found, so it goes out as it is.
    """
    if fallback:
        return GateResult(answer, None)

    # Same default as the fallback answer: detection can be unsure, as on "GPA?".
    text_language = "fr" if language == "fr" else "en"
    if not tool_ran:
        return GateResult(SCOPE_TEMPLATE[text_language], NO_TOOL)

    markers = cited_markers(normalize_brackets(answer))
    if not markers:
        return GateResult(NOT_FOUND_TEMPLATE[text_language], NO_CITATION)
    # One invented number is enough: the answer's sources can't be trusted as a whole.
    if not markers <= known_markers:
        return GateResult(NOT_FOUND_TEMPLATE[text_language], INVENTED_MARKER)
    return GateResult(answer, None)
