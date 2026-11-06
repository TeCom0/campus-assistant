"""The logs must never hold a student's question or a visitor's IP address.

A question can contain personal details, and container logs live outside the
database's 2-day retention. So: run a search and each failure path with a
recognisable question, and check nothing the process writes contains it.

capfd captures file descriptors 1 and 2, which is what `docker logs` reads, so
it sees print() and any logging handler. caplog sees records that a handler
might otherwise filter out. No LLM calls, no database (the searches are stubs).

The second half checks the deployment files that keep IPs out of the Caddy and
nginx logs and bound the size of every container's log.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import groq
import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app import main
from app.agent.citations import reset_citation_counter
from app.agent.tools import search_documents
from app.limits import Decision
from app.retrieval import hybrid_search

REPO_ROOT = Path(__file__).resolve().parents[2]

# The marker is what's searched for; the rest makes it look like a real question.
QUESTION = "My student ID is SECRETMARKER123 and my grade is D, can I keep my scholarship?"
MARKER = "SECRETMARKER123"


@pytest.fixture
def written(capfd, caplog):
    """A function returning everything written to stdout, stderr and the log so far."""
    caplog.set_level(logging.DEBUG)

    def read() -> str:
        out, err = capfd.readouterr()
        return out + err + caplog.text

    return read


@dataclass
class _Hit:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    section: str | None = None
    level: str = "general"
    sections: tuple = ()


def test_a_search_logs_no_question_or_query_text(monkeypatch, written):
    searched = []

    def search_vector(query, top_k):
        searched.append(query)
        return [_Hit("catalog", 1, [1], "passage")]

    monkeypatch.setattr(hybrid_search, "search_vector", search_vector)
    monkeypatch.setattr(hybrid_search, "search_keyword", lambda query, top_k: [])

    tool_graph = StateGraph(MessagesState)
    tool_graph.add_node("tools", ToolNode([search_documents]))
    tool_graph.add_edge(START, "tools")
    args = {"query": f"scholarship {MARKER}", "query_en": f"keep scholarship {MARKER}"}
    call = AIMessage("", tool_calls=[{"id": "1", "name": "search_documents", "args": args}])
    reset_citation_counter()
    tool_graph.compile().invoke({"messages": [HumanMessage(QUESTION), call]})

    assert QUESTION in searched  # the search really ran, on the question itself
    assert MARKER not in written()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "admit_question", lambda request: Decision(True))
    monkeypatch.setattr(main, "load_sources", dict)
    return TestClient(main.app)  # not as a context manager: no startup, no DB


def _graph_raising(error: Exception):
    async def raising(*args, **kwargs):
        raise error
        yield  # an async generator, like the real astream

    return raising


_RESPONSE_429 = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))


@pytest.mark.parametrize(
    ("error", "expected_in_log"),
    [
        # Provider errors can quote the request or the model's output.
        (ValueError(f"failed_generation: {QUESTION}"), "ValueError"),
        (
            groq.RateLimitError(f"tokens per day: {QUESTION}", response=_RESPONSE_429, body=None),
            "RateLimitError",
        ),
    ],
    ids=["other_error", "groq_rate_limit"],
)
def test_an_exception_logs_only_its_type(client, monkeypatch, written, error, expected_in_log):
    monkeypatch.setattr(main._compiled_graph, "astream", _graph_raising(error))

    body = client.post("/chat", json={"question": QUESTION}).text

    assert "event: error" in body  # the failure path really ran
    log = written()
    assert expected_in_log in log  # still useful for debugging
    assert MARKER not in log


def test_a_failed_trace_logs_only_its_type(client, monkeypatch, written):
    def failing_trace(run, status, sources):
        raise KeyError(QUESTION)

    monkeypatch.setattr(main._compiled_graph, "astream", _graph_raising(ValueError("x")))
    monkeypatch.setattr(main, "display_trace", failing_trace)

    client.post("/chat", json={"question": QUESTION})

    log = written()
    assert "KeyError" in log
    assert MARKER not in log


# --- Rejected requests --------------------------------------------------------
# Refused before any answer exists, so no other test above reaches these paths.

_LONG_WITH_MARKER = QUESTION + " " + "x" * 2000
_REJECTED_BODIES = {
    "question_too_long": {"question": _LONG_WITH_MARKER},
    "control_character": {"question": QUESTION + "\x00"},
    "wrong_type": {"question": [QUESTION]},
    "extra_field": {"question": "hi", MARKER: QUESTION},
    "too_many_messages": {
        "question": "hi",
        "messages": [{"role": "user", "content": QUESTION} for _ in range(21)],
    },
    "user_content_too_long": {
        "question": "hi",
        "messages": [{"role": "user", "content": _LONG_WITH_MARKER}],
    },
    "unknown_role": {"question": "hi", "messages": [{"role": MARKER, "content": QUESTION}]},
}


@pytest.fixture
def rejecting_client(monkeypatch):
    def must_not_run(request):
        raise AssertionError("a rejected request reached the limit check")

    monkeypatch.setattr(main, "admit_question", must_not_run)
    return TestClient(main.app)


@pytest.mark.parametrize("body", _REJECTED_BODIES.values(), ids=_REJECTED_BODIES.keys())
def test_a_rejected_request_logs_no_body_text_and_echoes_none(rejecting_client, written, body):
    response = rejecting_client.post("/chat", json=body)

    assert response.status_code == 422  # the rejection path really ran
    assert MARKER not in response.text
    assert MARKER not in written()


@pytest.mark.parametrize(
    ("content", "status"),
    [
        (f'{{"question": "{QUESTION}"', 422),  # invalid JSON
        (f"{QUESTION} ".encode() + b"x" * 70000, 413),
        (f'{{"question": "{QUESTION}\xff"}}'.encode("latin-1"), 400),  # invalid UTF-8
    ],
    ids=["invalid_json", "oversized", "invalid_utf8"],
)
def test_an_unreadable_body_logs_no_body_text_and_echoes_none(
    rejecting_client, written, content, status
):
    response = rejecting_client.post(
        "/chat", content=content, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == status
    assert MARKER not in response.text
    assert MARKER not in written()


# --- Deployment files ---------------------------------------------------------


class _ComposeLoader(yaml.SafeLoader):
    """Compose's !reset tag ("drop the inherited value") isn't standard YAML."""


_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def _services(filename: str) -> dict:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    return yaml.load(text, Loader=_ComposeLoader)["services"]


@pytest.mark.parametrize(
    ("filename", "service"),
    [
        ("docker-compose.yml", "db"),
        ("docker-compose.yml", "migrate"),
        ("docker-compose.yml", "api"),
        ("docker-compose.yml", "frontend"),
        ("docker-compose.prod.yml", "caddy"),
    ],
)
def test_every_container_rotates_its_log(filename, service):
    logging_config = _services(filename)[service]["logging"]
    assert logging_config["driver"] == "json-file"
    assert logging_config["options"]["max-size"]
    assert logging_config["options"]["max-file"]


def test_compose_files_define_no_other_container():
    services = set(_services("docker-compose.yml")) | set(_services("docker-compose.prod.yml"))
    assert services == {"db", "migrate", "registry-sync", "api", "frontend", "caddy"}


@pytest.mark.parametrize(
    "field",
    [
        "remote",
        "request>remote_ip",
        "request>remote_port",
        "request>client_ip",
        # A client's own X-Forwarded-For, X-Real-IP or Referer would be logged as sent.
        "request>headers",
    ],
)
def test_caddy_deletes_client_addresses_from_its_logs(field):
    caddyfile = (REPO_ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    assert f"{field} delete" in caddyfile


def test_nginx_writes_no_access_log():
    # Its default format records X-Forwarded-For: the visitor's real address.
    config = (REPO_ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "access_log off;" in config
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "nginx.conf /etc/nginx/conf.d/default.conf" in dockerfile
