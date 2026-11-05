"""What /chat refuses, and that refusing costs nothing: the body-size middleware
counts the bytes that really arrive, the field limits hold at N and N+1, a
rejected request never reaches the demo limits, and a valid answer still streams
token by token through the middleware.

No LLM calls and no database: the limit check and the agent are stubs.
"""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk

from app import main
from app.config import (
    MAX_ASSISTANT_CONTENT_CHARS,
    MAX_BODY_BYTES,
    MAX_QUESTION_CHARS,
    MAX_REQUEST_MESSAGES,
    MAX_USER_CONTENT_CHARS,
)
from app.limits import Decision
from app.request_limits import BodySizeLimitMiddleware

# --- The middleware, driven through ASGI directly -----------------------------
# A client like TestClient hands over one whole body. Here each chunk is its own
# message, as uvicorn delivers a chunked request, with no Content-Length.


def _http_scope(headers=()) -> dict:
    return {"type": "http", "method": "POST", "path": "/", "headers": list(headers)}


def _receiver(chunks: list[bytes]):
    """An ASGI receive that delivers the chunks, then says the client left."""
    pending = [
        {"type": "http.request", "body": chunk, "more_body": i < len(chunks) - 1}
        for i, chunk in enumerate(chunks)
    ]
    calls = []

    async def receive():
        calls.append(1)
        return pending.pop(0) if pending else {"type": "http.disconnect"}

    receive.calls = calls
    return receive


class _RecordingApp:
    """Reads the whole body and answers 200, recording what it was given."""

    def __init__(self):
        self.called = False
        self.body = b""
        self.next_message = None

    async def __call__(self, scope, receive, send):
        self.called = True
        while True:
            message = await receive()
            self.body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        self.next_message = await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def _through_middleware(chunks, headers=(), limit=100):
    inner = _RecordingApp()
    sent = []

    async def send(message):
        sent.append(message)

    middleware = BodySizeLimitMiddleware(inner, max_bytes=limit)
    receive = _receiver(chunks)
    asyncio.run(middleware(_http_scope(headers), receive, send))
    return inner, sent[0]["status"], receive


def test_a_chunked_body_at_the_limit_passes_whole():
    inner, status, _ = _through_middleware([b"a" * 40, b"b" * 40, b"c" * 20])
    assert status == 200
    assert inner.body == b"a" * 40 + b"b" * 40 + b"c" * 20


def test_a_chunked_body_over_the_limit_is_refused_without_a_content_length():
    inner, status, _ = _through_middleware([b"a" * 40, b"b" * 40, b"c" * 21])
    assert status == 413
    assert not inner.called


def test_reading_stops_as_soon_as_the_limit_is_passed():
    _, status, receive = _through_middleware([b"a" * 101, b"never read"])
    assert status == 413
    assert len(receive.calls) == 1


def test_a_large_declared_size_is_refused_without_reading_the_body():
    inner, status, receive = _through_middleware([b"small"], [(b"content-length", b"101")])
    assert status == 413
    assert not inner.called
    assert not receive.calls


def test_a_false_small_content_length_does_not_get_around_the_count():
    inner, status, _ = _through_middleware([b"a" * 101], [(b"content-length", b"5")])
    assert status == 413
    assert not inner.called


def test_the_app_still_hears_a_disconnect_after_the_body():
    inner, status, _ = _through_middleware([b"body"])
    assert status == 200
    assert inner.next_message == {"type": "http.disconnect"}


def test_a_client_gone_before_the_body_ended_reaches_the_app():
    seen = []

    async def app(scope, receive, send):
        seen.append(await receive())
        seen.append(await receive())

    pending = [
        {"type": "http.request", "body": b"part", "more_body": True},
        {"type": "http.disconnect"},
    ]

    async def receive():
        return pending.pop(0)

    asyncio.run(BodySizeLimitMiddleware(app, max_bytes=100)(_http_scope(), receive, None))
    assert [message["type"] for message in seen] == ["http.request", "http.disconnect"]


def test_other_scopes_pass_untouched():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(BodySizeLimitMiddleware(app, max_bytes=1)({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]


# --- /chat --------------------------------------------------------------------


@pytest.fixture
def admitted(monkeypatch) -> list:
    """Stubs the agent, and records each request that reached the limit check."""
    calls = []

    def admit(request):
        calls.append(request)
        return Decision(True)

    async def one_token(*args, **kwargs):
        yield "messages", (AIMessageChunk(content="Hello"), {"langgraph_node": "agent"})

    monkeypatch.setattr(main, "admit_question", admit)
    monkeypatch.setattr(main._compiled_graph, "astream", one_token)
    return calls


@pytest.fixture
def client(admitted) -> TestClient:
    return TestClient(main.app)  # not as a context manager: no startup, no DB


def _history(count: int) -> list[dict]:
    return [{"role": "user", "content": "hi"} for _ in range(count)]


@pytest.mark.parametrize(
    "body",
    [
        {"question": "x" * MAX_QUESTION_CHARS},
        {"question": "  " + "x" * MAX_QUESTION_CHARS + "\n"},  # counted after trimming
        {"question": "line one\nline two\twith a tab"},
        {"question": "é" * MAX_QUESTION_CHARS},  # characters, not bytes
        {"question": "hi", "messages": None},
        {"question": "hi", "messages": []},
        {"question": "hi", "messages": _history(MAX_REQUEST_MESSAGES)},
        {"question": "hi", "messages": [{"role": "user", "content": "x" * MAX_USER_CONTENT_CHARS}]},
        {
            "question": "hi",
            "messages": [{"role": "assistant", "content": "x" * MAX_ASSISTANT_CONTENT_CHARS}],
        },
    ],
    ids=[
        "question_at_limit",
        "question_at_limit_after_trim",
        "newline_and_tab",
        "accents_counted_as_characters",
        "messages_null",
        "messages_empty",
        "messages_at_limit",
        "user_content_at_limit",
        "assistant_content_at_limit",
    ],
)
def test_a_request_within_the_limits_is_answered(client, admitted, body):
    response = client.post("/chat", json=body)
    assert response.status_code == 200
    assert "event: token" in response.text
    assert len(admitted) == 1


REJECTED = {
    "question_over_limit": {"question": "x" * (MAX_QUESTION_CHARS + 1)},
    "question_empty": {"question": ""},
    "question_only_whitespace": {"question": " \n\t "},
    "question_null_character": {"question": "hi\x00there"},
    "question_escape_character": {"question": "hi\x1b[31mthere"},
    "question_carriage_return": {"question": "hi\r\nthere"},
    "question_c1_control": {"question": "hi\x85there"},
    "question_missing": {"messages": []},
    "question_wrong_type": {"question": ["hi"]},
    "messages_over_limit": {"question": "hi", "messages": _history(MAX_REQUEST_MESSAGES + 1)},
    "user_content_over_limit": {
        "question": "hi",
        "messages": [{"role": "user", "content": "x" * (MAX_USER_CONTENT_CHARS + 1)}],
    },
    "assistant_content_over_limit": {
        "question": "hi",
        "messages": [{"role": "assistant", "content": "x" * (MAX_ASSISTANT_CONTENT_CHARS + 1)}],
    },
    "unknown_role": {"question": "hi", "messages": [{"role": "system", "content": "x"}]},
    "extra_field": {"question": "hi", "model": "something-else"},
    "extra_field_in_a_message": {
        "question": "hi",
        "messages": [{"role": "user", "content": "x", "name": "y"}],
    },
}


@pytest.mark.parametrize("body", REJECTED.values(), ids=REJECTED.keys())
def test_a_request_over_a_limit_gets_a_422_and_is_not_counted(client, admitted, body):
    response = client.post("/chat", json=body)
    assert response.status_code == 422
    assert response.json() == {"kind": "invalid_request", "message": "The request is not valid."}
    assert admitted == []


@pytest.mark.parametrize(
    ("content", "headers"),
    [
        ("{not json", {"Content-Type": "application/json"}),
        ('{"question": "hi"}', {"Content-Type": "text/plain"}),
        ('{"question": "hi"}', {}),
    ],
    ids=["invalid_json", "text_plain", "no_content_type"],
)
def test_only_json_is_accepted(client, admitted, content, headers):
    response = client.post("/chat", content=content, headers=headers)
    assert response.status_code == 422
    assert admitted == []


def test_an_oversized_body_gets_a_413_and_is_not_counted(client, admitted):
    response = client.post("/chat", content=b"x" * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.json()["kind"] == "too_large"
    assert admitted == []


def test_a_body_exactly_at_the_limit_gets_past_the_size_check(client, admitted):
    # It then fails validation: 422, not 413, shows which check refused it.
    response = client.post("/chat", content=b"x" * MAX_BODY_BYTES)
    assert response.status_code == 422
    assert admitted == []


def test_the_question_reaches_the_agent_trimmed(monkeypatch, client):
    seen = {}

    async def recording(payload, **kwargs):
        seen["last"] = payload["messages"][-1]["content"]
        yield "messages", (AIMessageChunk(content="Hello"), {"langgraph_node": "agent"})

    monkeypatch.setattr(main._compiled_graph, "astream", recording)
    client.post("/chat", json={"question": "  How many credits?\n"})
    assert seen["last"] == "How many credits?"


def test_a_refused_request_can_still_be_read_across_origins(client):
    origin = main.CORS_ORIGINS[0]
    response = client.post("/chat", content=b"x" * (MAX_BODY_BYTES + 1), headers={"Origin": origin})
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MAX_BODY_BYTES", MAX_BODY_BYTES),
        ("MAX_QUESTION_CHARS", MAX_QUESTION_CHARS),
        ("MAX_REQUEST_MESSAGES", MAX_REQUEST_MESSAGES),
        ("MAX_USER_CONTENT_CHARS", MAX_USER_CONTENT_CHARS),
        ("MAX_ASSISTANT_CONTENT_CHARS", MAX_ASSISTANT_CONTENT_CHARS),
    ],
)
def test_the_frontend_holds_the_same_limits(name, value):
    source = Path(__file__).resolve().parents[2] / "frontend" / "src" / "requestLimits.ts"
    assert f"export const {name} = {value};" in source.read_text(encoding="utf-8")


# --- Streaming through the middleware -----------------------------------------


def test_a_valid_answer_streams_token_by_token(monkeypatch, admitted):
    """The order of events proves it: each token reaches `send` before the agent
    is asked for the next. A middleware that buffered the response would show all
    the tokens produced first, and only then sent. Driven through ASGI directly,
    because TestClient collects the whole response before returning it."""
    tokens = ["The ", "limit ", "is ", "68."]
    order = []

    async def stub_agent(*args, **kwargs):
        for token in tokens:
            order.append(f"produced {token}")
            yield "messages", (AIMessageChunk(content=token), {"langgraph_node": "agent"})

    monkeypatch.setattr(main._compiled_graph, "astream", stub_agent)

    body = json.dumps({"question": "How many credits?"}).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/chat",
        "raw_path": b"/chat",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    async def run():
        delivered = []

        async def receive():
            if not delivered:
                delivered.append(1)
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()  # the client stays connected

        async def send(message):
            if message["type"] == "http.response.start":
                order.append(f"status {message['status']}")
            elif message["type"] == "http.response.body":
                text = message.get("body", b"").decode()
                if text.startswith("event: token"):
                    order.append(f"sent {json.loads(text.split('data: ', 1)[1])['text']}")

        await main.app(scope, receive, send)

    asyncio.run(run())

    assert order == [
        "status 200",
        "produced The ",
        "sent The ",
        "produced limit ",
        "sent limit ",
        "produced is ",
        "sent is ",
        "produced 68.",
        "sent 68.",
    ]
