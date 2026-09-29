"""RAG generation: answer questions using ONLY retrieved context, with
citations, saying "I don't know" when the context doesn't contain an answer.
"""

from dataclasses import dataclass

from app.llm import complete
from app.retrieval.hybrid_search import HybridResult, search_hybrid

TOP_K = 5

SYSTEM_PROMPT = """You are the Al Akhawayn University (AUI) assistant. Answer the student's \
question using ONLY the numbered context passages below. Do not use any outside knowledge, \
even if you believe you know the answer some other way -- the passages are the only source \
of truth you're allowed to draw on.

Rules:
- Cite every factual claim with its passage number in brackets, e.g. [1], right after the claim.
- If the passages don't contain enough information to answer, say plainly that you don't know \
based on the available documents. Do not guess or fill the gap with outside knowledge.
- LANGUAGE (strict): detect the language of the student's question and write your ENTIRE \
answer in that same language -- if the question is in English, answer only in English; if the \
question is in French, answer only in French. Never switch languages, even if the source \
passages are in a different language than the question.
- Be concise."""


@dataclass
class Citation:
    marker: str  # e.g. "[1]"
    source: str
    pages: list[int]


@dataclass
class Answer:
    text: str
    citations: list[Citation]


def _build_context(results: list[HybridResult]) -> str:
    parts = [f"[{i}] (source: {r.source}, pages: {r.pages})\n{r.text}" for i, r in enumerate(results, start=1)]
    return "\n\n".join(parts)


def answer_question(question: str, top_k: int = TOP_K) -> Answer:
    results = search_hybrid(question, top_k=top_k)
    context = _build_context(results)
    prompt = f"Context passages:\n{context}\n\nQuestion: {question}"

    text = complete(prompt, system=SYSTEM_PROMPT)

    citations = [
        Citation(marker=f"[{i}]", source=r.source, pages=r.pages)
        for i, r in enumerate(results, start=1)
    ]
    return Answer(text=text, citations=citations)


if __name__ == "__main__":
    import sys

    # Windows' console defaults to a codepage (e.g. cp1252) that can't
    # represent every Unicode character an LLM or a French source document
    # might produce (e.g. U+202F narrow no-break space), which would
    # otherwise crash print() outright rather than just look wrong.
    sys.stdout.reconfigure(encoding="utf-8")

    questions = [
        "How many credits can I transfer to AUI?",
        "Which fellowships are closing this month?",
    ]
    for q in questions:
        print(f"=== {q} ===")
        result = answer_question(q)
        print(result.text)
        print("\nSources:")
        for c in result.citations:
            print(f"  {c.marker} {c.source} (pages {c.pages})")
        print()
