"""Tests for the demo protection (app.limits) and its use in /chat.

The limit tests need Postgres (skipped when it isn't reachable) and run inside
a transaction that is always rolled back, with the table emptied first and a
fixed clock, so real question_log rows are never touched or counted. The
/chat tests replace the limit check and the agent, so they make no LLM calls.
"""

from datetime import UTC, datetime, timedelta

import groq
import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main
from app.db.connection import database_reachable, get_connection, init_schema
from app.limits import Decision, check_and_record, client_ip, hash_ip

NOON = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=10)


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_is_the_tcp_peer_unless_proxy_headers_are_trusted():
    request = _request("10.0.0.2", forwarded="6.6.6.6, 203.0.113.7")
    assert client_ip(request, trust_proxy_headers=False) == "10.0.0.2"
    # Behind the proxy: its own appended entry (the last), not the client's claims.
    assert client_ip(request, trust_proxy_headers=True) == "203.0.113.7"
    assert client_ip(_request("10.0.0.2"), trust_proxy_headers=True) == "10.0.0.2"


def test_ips_are_stored_only_as_a_keyed_hash():
    assert hash_ip("203.0.113.7") == hash_ip("203.0.113.7")
    assert hash_ip("203.0.113.7") != hash_ip("203.0.113.8")
    assert "203.0.113.7" not in hash_ip("203.0.113.7")


needs_db = pytest.mark.skipif(not database_reachable(), reason="Postgres not reachable")


@pytest.fixture
def conn():
    connection = get_connection()
    with connection.transaction(force_rollback=True):
        init_schema(connection)
        connection.execute("DELETE FROM question_log")  # undone by the rollback
        yield connection
    connection.close()


def _ask(conn, ip: str, at: datetime, daily_cap: int = 30, per_ip_limit: int = 3) -> Decision:
    return check_and_record(conn, hash_ip(ip), at, daily_cap, per_ip_limit, WINDOW)


def _rows(conn) -> int:
    return conn.execute("SELECT count(*) FROM question_log").fetchone()[0]


@needs_db
def test_per_ip_limit_refuses_then_frees_up_after_the_window(conn):
    for minute in range(3):
        assert _ask(conn, "1.1.1.1", NOON + timedelta(minutes=minute)).allowed

    refused = _ask(conn, "1.1.1.1", NOON + timedelta(minutes=5))
    assert (refused.allowed, refused.kind) == (False, "per_ip")
    assert refused.retry_after_seconds == 5 * 60  # the 12:00 question leaves at 12:10
    assert _ask(conn, "2.2.2.2", NOON + timedelta(minutes=5)).allowed  # other visitors fine
    assert _ask(conn, "1.1.1.1", NOON + timedelta(minutes=10, seconds=1)).allowed


@needs_db
def test_a_zero_limit_refuses_everyone_without_crashing(conn):
    # Found in the browser check: no earlier question means min(asked_at) is NULL.
    refused = _ask(conn, "1.1.1.1", NOON, per_ip_limit=0)
    assert (refused.allowed, refused.kind, refused.retry_after_seconds) == (False, "per_ip", 600)


@needs_db
def test_refused_questions_are_not_recorded(conn):
    for minute in range(3):
        _ask(conn, "1.1.1.1", NOON + timedelta(minutes=minute))
    before = _rows(conn)
    for _ in range(5):
        _ask(conn, "1.1.1.1", NOON + timedelta(minutes=4))
    assert _rows(conn) == before


@needs_db
def test_daily_cap_counts_everyone_and_resets_at_utc_midnight(conn):
    for i in range(4):
        assert _ask(conn, f"10.0.0.{i}", NOON, daily_cap=4).allowed

    refused = _ask(conn, "10.0.0.99", NOON, daily_cap=4)
    assert (refused.allowed, refused.kind) == (False, "daily_cap")
    assert refused.retry_after_seconds == 12 * 3600  # until 00:00 UTC
    assert _ask(conn, "10.0.0.99", NOON + timedelta(hours=12), daily_cap=4).allowed


@needs_db
def test_rows_older_than_two_days_are_deleted(conn):
    _ask(conn, "1.1.1.1", NOON - timedelta(days=3))
    _ask(conn, "2.2.2.2", NOON)
    assert _rows(conn) == 1


# --- /chat ----------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    def no_agent(*args, **kwargs):
        raise AssertionError("the agent must not run")

    monkeypatch.setattr(main._compiled_graph, "astream", no_agent)
    return TestClient(main.app)  # not as a context manager: no startup, no DB


@pytest.mark.parametrize(
    ("kind", "question", "fragment"),
    [
        ("daily_cap", "How many credits can I transfer?", "try again tomorrow"),
        ("daily_cap", "Combien de crédits puis-je transférer ?", "Réessayez demain"),
        ("per_ip", "How many credits can I transfer?", "wait a few minutes"),
    ],
)
def test_a_refused_question_gets_a_429_and_never_reaches_the_agent(
    client, monkeypatch, kind, question, fragment
):
    monkeypatch.setattr(main, "admit_question", lambda request: Decision(False, kind, 600))
    response = client.post("/chat", json={"question": question})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "600"
    assert response.json()["kind"] == kind
    assert fragment in response.json()["message"]
    assert response.json()["title"]


@pytest.mark.parametrize(
    ("groq_message", "fragment"),
    [
        ("Rate limit reached ... tokens per minute (TPM): Limit 8000", "try again in a minute"),
        ("Rate limit reached ... tokens per day (TPD): Limit 200000", "try again tomorrow"),
    ],
)
def test_a_groq_rate_limit_mid_answer_ends_with_a_friendly_limit_event(
    client, monkeypatch, groq_message, fragment
):
    response_429 = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))

    async def rate_limited(*args, **kwargs):
        raise groq.RateLimitError(groq_message, response=response_429, body=None)
        yield  # an async generator, like the real astream

    monkeypatch.setattr(main, "admit_question", lambda request: Decision(True))
    monkeypatch.setattr(main._compiled_graph, "astream", rate_limited)
    body = client.post("/chat", json={"question": "How many credits can I transfer?"}).text

    assert "event: error" in body
    assert '"kind": "limit"' in body
    assert '"title":' in body
    assert fragment in body
