"""Detects whether a student's question is in English or French.

langdetect (used before) is built for paragraphs and failed on chat-length
questions, with full confidence: "ACC 2302 prerequisites" -> French (1.0),
"graduation requirements for computer science" -> French, "date limite
inscription" -> English. Neither a confidence threshold nor a minimum word
count fixed it.

This project only needs English vs. French, so instead we count each
language's common function words ("the", "what", "for" vs. "le", "quels",
"pour"), plus an accented letter as one French signal. Whichever side has
more wins; a tie (often zero vs. zero, e.g. "GPA?" or "ACC 2302
prerequisites") returns None -- unsure -- and callers fall back to letting
the model judge the language, rather than ordering a wrong one.

Words used in both languages ("a", "on", "me", "date") are left out on
purpose: they'd count as evidence for one side when they're evidence for
neither.
"""

import re

_ENGLISH_WORDS = {
    "the", "an", "is", "are", "was", "what", "how", "when", "where", "which", "who", "why",
    "do", "does", "did", "can", "could", "i", "my", "for", "of", "to", "in", "and", "or",
    "with", "from", "about", "please", "need", "be", "it", "this", "there", "any", "if",
    "should", "will", "much", "many", "have", "get", "your", "after", "before", "thanks",
    "hi", "hello",
}  # fmt: skip

_FRENCH_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "est", "sont", "quel", "quelle",
    "quels", "quelles", "comment", "quand", "où", "pourquoi", "je", "mon", "ma", "mes",
    "pour", "et", "ou", "avec", "dans", "sur", "au", "aux", "puis", "peux", "faut", "il",
    "elle", "ce", "cette", "combien", "qui", "que", "qu", "merci", "bonjour", "avant",
    "après",
}  # fmt: skip

_FRENCH_ACCENT_RE = re.compile(r"[àâçéèêëîïôûùüÿœ]", re.IGNORECASE)

# Runs of letters only: drops digits, so "ACC 2302" gives just "acc", and
# splits "l'université" or "puis-je" into separate words.
_WORD_RE = re.compile(r"[^\W\d_]+")


def detect_language(text: str) -> str | None:
    """Return "en" or "fr", or None when the text gives no clear signal either way."""
    words = _WORD_RE.findall(text.lower())
    english = sum(word in _ENGLISH_WORDS for word in words)
    french = sum(word in _FRENCH_WORDS for word in words)
    if _FRENCH_ACCENT_RE.search(text):
        french += 1

    if english > french:
        return "en"
    if french > english:
        return "fr"
    return None
