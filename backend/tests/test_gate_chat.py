"""The gate through the real /chat stream: the compiled graph with a fake model and a fake
tool, so no LLM calls and no database. What's tested is what a browser receives."""

import asyncio
import json

import groq
import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.tools import tool

from app import main
from app.agent import graph
from app.agent.gate import INVENTED_MARKER, NO_CITATION, NO_TOOL, NOT_FOUND_TEMPLATE, SCOPE_TEMPLATE
from app.limits import Decision
from app.registry import SourceRow
from app.sources import sources_from_rows

QUESTION = "How many credits can I transfer from another university?"
# In every rejected answer, so a leak anywhere in the response is easy to find.
REJECTED = "REJECTED-MODEL-TEXT"
SOURCE = "academic_catalog_2024_2025"
SOURCES = sources_from_rows(
    [
        SourceRow(
            edition_id=SOURCE,
            card_title="Academic Catalog 2024–2025",
            source_url="https://aui.ma/catalog.pdf",
            fallback_url=None,
            format="pdf",
            status="active",
        )
    ]
)


@tool("search_documents", response_format="content_and_artifact")
def _fake_search(query: str) -> tuple[str, list[dict]]:
    """Stands in for the real search: always one passage, marker 1."""
    return "[1] a passage", [{"marker": 1, "source": SOURCE, "pages": [118], "text": "a passage"}]


def _search_turn() -> AIMessage:
    return AIMessage(
        "", tool_calls=[{"id": "c1", "name": "search_documents", "args": {"query": "credits"}}]
    )


class _ScriptedModel:
    def __init__(self, *replies: AIMessage) -> None:
        self.replies = list(replies)

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        return self.replies.pop(0)


def _post(monkeypatch, question: str = QUESTION) -> str:
    monkeypatch.setattr(main, "admit_question", lambda request: Decision(True))
    monkeypatch.setattr(main, "load_sources", lambda: SOURCES)
    return TestClient(main.app).post("/chat", json={"question": question}).text


def _chat(monkeypatch, *replies: AIMessage, question: str = QUESTION) -> tuple[str, list]:
    """The raw response and its events, from the real graph."""
    monkeypatch.setattr(graph, "TOOLS", [_fake_search])
    model = _ScriptedModel(*replies)
    monkeypatch.setattr(graph, "get_agent_model", lambda: model)
    monkeypatch.setattr(main, "_compiled_graph", graph.build_graph())
    body = _post(monkeypatch, question)
    return body, _events(body)


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for frame in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def _text(events) -> str:
    return "".join(data["text"] for name, data in events if name == "token")


def _trace(events) -> dict:
    [trace] = [data for name, data in events if name == "trace"]
    return trace


def _citations(events) -> list:
    [citations] = [data["citations"] for name, data in events if name == "citations"]
    return citations


# --- A rejected answer never reaches the browser ------------------------------------


@pytest.mark.parametrize(
    ("replies", "template", "reason"),
    [
        ([AIMessage(f"{REJECTED}: 1 + 1 = 2.")], SCOPE_TEMPLATE["en"], NO_TOOL),
        (
            [_search_turn(), AIMessage(f"{REJECTED}: 68 credits.")],
            NOT_FOUND_TEMPLATE["en"],
            NO_CITATION,
        ),
        (
            [_search_turn(), AIMessage(f"{REJECTED}: 68 [7].")],
            NOT_FOUND_TEMPLATE["en"],
            INVENTED_MARKER,
        ),
    ],
    ids=["no_tool", "no_citation", "invented_marker"],
)
def test_a_rejected_answers_text_appears_nowhere_in_the_response(
    monkeypatch, replies, template, reason
):
    body, events = _chat(monkeypatch, *replies)

    assert REJECTED not in body  # in no event at all, the trace included
    assert _text(events) == template
    assert _citations(events) == []
    assert _trace(events)["gate"] == reason
    assert [name for name, _ in events][-3:] == ["citations", "trace", "done"]


def test_a_template_follows_the_questions_language(monkeypatch):
    _, events = _chat(
        monkeypatch,
        AIMessage(f"{REJECTED}: bonjour"),
        question="Quelle est la capitale de la France et combien de crédits puis-je transférer ?",
    )
    assert _text(events) == SCOPE_TEMPLATE["fr"]


# --- A good answer ------------------------------------------------------------------


def test_a_cited_answer_is_sent_whole_after_the_tools_and_before_the_citations(monkeypatch):
    _, events = _chat(monkeypatch, _search_turn(), AIMessage("Up to 68 credits [1]."))

    names = [name for name, _ in events]
    assert names == ["tool_call", "token", "citations", "trace", "done"]
    assert _text(events) == "Up to 68 credits [1]."
    assert [c["marker"] for c in _citations(events)] == [1]
    assert _citations(events)[0]["title"] == "Academic Catalog 2024–2025"
    assert "gate" not in _trace(events)


def test_the_first_word_is_timed_when_the_student_gets_it(monkeypatch):
    async def stream(*args, **kwargs):
        yield "messages", (AIMessageChunk("Up to 68 credits [1]."), {"langgraph_node": "agent"})
        await asyncio.sleep(0.05)  # the model has written a word, and isn't finished
        yield "updates", {"agent": {"messages": [AIMessage("Up to 68 credits [1].")]}}

    monkeypatch.setattr(main._compiled_graph, "astream", stream)
    totals = _trace(_events(_post(monkeypatch)))["totals"]
    # Held until the model finished, so not before the run's last step ended.
    assert totals["first_token_ms"] >= totals["duration_ms"]


# --- A run that fails partway -------------------------------------------------------


def _partial_then(error: Exception):
    async def stream(*args, **kwargs):
        yield "messages", (AIMessageChunk(f"{REJECTED} half an"), {"langgraph_node": "agent"})
        raise error

    return stream


def _rate_limit() -> groq.RateLimitError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return groq.RateLimitError("tokens per day", response=response, body={})


@pytest.mark.parametrize(
    "error", [RuntimeError("Groq is down"), _rate_limit()], ids=["error", "limit"]
)
def test_text_held_when_the_run_fails_is_never_sent(monkeypatch, error):
    monkeypatch.setattr(main._compiled_graph, "astream", _partial_then(error))
    body = _post(monkeypatch)

    assert REJECTED not in body
    names = [name for name, _ in _events(body)]
    assert "token" not in names
    assert names[-1] == "error"
