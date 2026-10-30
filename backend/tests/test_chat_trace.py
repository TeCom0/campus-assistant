"""Tests for the "Under the hood" trace: RunTrace's timeline and token
totals, the trace event /chat sends however the run ends (done, fallback,
Groq rate limit, other error), and that the evaluation never collects one.

The /chat tests replace the limit check and the agent with a stub stream
that records a tool step the way the real tools do, so they make no LLM
calls and need no database.
"""

import contextvars
import json

import groq
import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app import main
from app.agent import trace as trace_module
from app.agent.trace import RunTrace, record_tool_step, trace_steps
from app.evaluation import generate_faithfulness_answers
from app.limits import Decision

# --- RunTrace ---------------------------------------------------------------


class _Clock:
    """A fake perf_counter: each test moves it on by hand."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _usage(input_tokens: int, output_tokens: int, reasoning: int) -> dict:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "output_token_details": {"reasoning": reasoning},
    }


def _tool_call(call_id: str, name: str = "search_documents") -> dict:
    return {"id": call_id, "name": name, "args": {}}


def test_timeline_segments_follow_each_other_and_carry_tokens():
    clock = _Clock()
    run = RunTrace(clock)
    clock.now += 1.85
    run.agent_message(
        AIMessage("", tool_calls=[_tool_call("a")], usage_metadata=_usage(888, 49, 16))
    )
    clock.now += 0.28
    run.tools_done()
    clock.now += 0.10
    run.token()
    clock.now += 0.79
    run.token()  # only the first token is timed
    run.agent_message(AIMessage("The answer [1]", usage_metadata=_usage(1148, 398, 122)))

    assert run.timeline == [
        {
            "kind": "llm",
            "start_ms": 0,
            "end_ms": 1850,
            "tool_calls": ["search_documents"],
            "input_tokens": 888,
            "output_tokens": 49,
            "reasoning_tokens": 16,
        },
        {"kind": "tools", "start_ms": 1850, "end_ms": 2130},
        {
            "kind": "llm",
            "start_ms": 2130,
            "end_ms": 3020,
            "tool_calls": [],
            "input_tokens": 1148,
            "output_tokens": 398,
            "reasoning_tokens": 122,
        },
    ]
    totals = run.event("done")["totals"]
    assert totals == {
        "duration_ms": 3020,
        "first_token_ms": 2230,
        "llm_calls": 2,
        "input_tokens": 2036,
        "output_tokens": 447,
        "reasoning_tokens": 138,
        "tokens_complete": True,
    }


def test_missing_usage_is_never_counted_as_zero_tokens():
    run = RunTrace(_Clock())
    run.agent_message(AIMessage("", tool_calls=[_tool_call("a")], usage_metadata=_usage(10, 2, 0)))
    run.agent_message(AIMessage("answer"))  # provider reported nothing

    assert run.timeline[1]["input_tokens"] is None
    totals = run.event("done")["totals"]
    assert totals["input_tokens"] == 10
    assert totals["tokens_complete"] is False


def test_event_lists_the_recorded_steps_in_the_models_order():
    def run_in_request():
        main.start_trace()
        run = RunTrace(_Clock())
        run.agent_message(AIMessage("", tool_calls=[_tool_call("first"), _tool_call("second")]))
        record_tool_step("search_documents", {"n": 2}, call_id="second")  # finished first
        record_tool_step("search_documents", {"n": 1}, call_id="first")
        return run.event("done")["steps"]

    steps = contextvars.Context().run(run_in_request)
    assert [step["n"] for step in steps] == [1, 2]


# --- /chat ------------------------------------------------------------------

QUESTION = "How many credits can I transfer?"
RESULT = {
    "rank": 1,
    "marker": 1,
    "new": True,
    "source": "academic_catalog_2024_2025",
    "pages": [118],
    "level": "undergraduate",
    "section": "Transfer Credits",
    "sections": ["Transfer Credits"],
    "snippet": "A maximum of",
    "rrf_score": 0.0328,
    "vector_rank": 1,
    "keyword_rank": 1,
}
CITATION = {"marker": 1, "source": "academic_catalog_2024_2025", "pages": [118], "text": "..."}


def _search_round():
    """What the stream shows for one search: the agent's call, the tool's
    recorded step (as search_documents records it), the tools update."""
    call = AIMessage("", tool_calls=[_tool_call("call_1")], usage_metadata=_usage(900, 50, 10))
    yield "updates", {"agent": {"messages": [call]}}
    record_tool_step("search_documents", {"results": [RESULT]}, call_id="call_1")
    tool_message = ToolMessage("[1] passage", tool_call_id="call_1", artifact=[CITATION])
    yield "updates", {"tools": {"messages": [tool_message]}}


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for frame in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def _chat(monkeypatch, stream) -> list[tuple[str, dict]]:
    monkeypatch.setattr(main, "admit_question", lambda request: Decision(True))
    monkeypatch.setattr(main._compiled_graph, "astream", stream)
    return _events(TestClient(main.app).post("/chat", json={"question": QUESTION}).text)


def _trace(events) -> dict:
    [trace] = [data for name, data in events if name == "trace"]
    return trace


def test_answered_question_sends_the_trace_between_citations_and_done(monkeypatch):
    async def answered(*args, **kwargs):
        for update in _search_round():
            yield update
        yield "messages", (AIMessageChunk("Up to 30 credits [1]."), {"langgraph_node": "agent"})
        answer = AIMessage("Up to 30 credits [1].", usage_metadata=_usage(1200, 300, 80))
        yield "updates", {"agent": {"messages": [answer]}}

    events = _chat(monkeypatch, answered)

    assert [name for name, _ in events][-3:] == ["citations", "trace", "done"]
    trace = _trace(events)
    assert trace["status"] == "done"
    assert trace["model"]["name"] == trace_module.MODEL
    assert [s["kind"] for s in trace["timeline"]] == ["llm", "tools", "llm"]
    assert trace["totals"]["input_tokens"] == 2100
    [step] = trace["steps"]
    assert step["call_id"] == "call_1"
    # Passages get the same display info as source cards.
    assert step["results"][0]["title"] == "Academic Catalog 2024–2025"


def test_fallback_answer_still_sends_the_trace_with_the_steps_before_it(monkeypatch):
    async def fell_back(*args, **kwargs):
        for update in _search_round():
            yield update
        # graph._fallback_answer: built in code when the forced answer fails twice.
        fallback = AIMessage(
            "I couldn't finish this answer. These passages found while searching may help: [1]",
            response_metadata={"fallback": True},
        )
        yield "updates", {"agent": {"messages": [fallback]}}

    events = _chat(monkeypatch, fell_back)

    assert [name for name, _ in events][-2:] == ["trace", "done"]
    trace = _trace(events)
    assert trace["status"] == "fallback"
    assert [s["kind"] for s in trace["timeline"]] == ["llm", "tools", "fallback"]
    assert trace["totals"]["llm_calls"] == 1  # the fallback used no LLM call
    assert [step["call_id"] for step in trace["steps"]] == ["call_1"]


def _rate_limit_error() -> groq.RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    return groq.RateLimitError(
        "Rate limit reached ... tokens per day (TPD): Limit 200000", response=response, body=None
    )


@pytest.mark.parametrize(
    ("error", "status"),
    [(_rate_limit_error(), "limit"), (RuntimeError("database password is hunter2"), "error")],
)
def test_run_stopped_by_an_error_still_sends_the_trace_before_the_error(monkeypatch, error, status):
    async def stopped(*args, **kwargs):
        for update in _search_round():
            yield update
        raise error  # the answer's LLM call fails

    events = _chat(monkeypatch, stopped)
    names = [name for name, _ in events]

    assert names[-2:] == ["trace", "error"]
    trace = _trace(events)
    assert trace["status"] == status
    assert [s["kind"] for s in trace["timeline"]] == ["llm", "tools", "stopped"]
    assert [step["call_id"] for step in trace["steps"]] == ["call_1"]
    # Exception text stays in the server log, as for the error event.
    assert "hunter2" not in json.dumps(trace)


def test_a_trace_that_cant_be_built_doesnt_cost_the_answer(monkeypatch):
    async def answered(*args, **kwargs):
        yield "updates", {"agent": {"messages": [AIMessage("Hello.")]}}

    def broken(self, status):
        raise KeyError("results")

    monkeypatch.setattr(RunTrace, "event", broken)
    names = [name for name, _ in _chat(monkeypatch, answered)]

    assert "trace" not in names
    assert names[-1] == "done"


def test_a_refused_question_gets_its_429_and_no_trace(monkeypatch):
    monkeypatch.setattr(main, "admit_question", lambda request: Decision(False, "daily_cap", 600))
    response = TestClient(main.app).post("/chat", json={"question": QUESTION})

    assert response.status_code == 429
    assert "trace" not in response.text


# --- the evaluation ---------------------------------------------------------

# Every key of a faithfulness answer record, as in runs 1-3: the trace must
# not add one.
EVAL_RECORD_KEYS = {
    "id", "run", "question", "language", "detected_language", "provider", "model",
    "answer", "cited_markers", "passages", "tool_calls", "searches", "usage",
    "seconds", "error", "fallback", "generated_at",
}  # fmt: skip


class _FakeGraph:
    """Answers like the agent, and records a tool step as search_documents would."""

    def invoke(self, state, config):
        record_tool_step("search_documents", {"results": [RESULT]}, call_id="call_1")
        return {"messages": [HumanMessage(QUESTION), AIMessage("Up to 30 credits.")]}


def test_the_evaluation_collects_no_trace_and_keeps_its_record_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(generate_faithfulness_answers, "build_graph", _FakeGraph)
    question = {"id": "transfer_credits_en", "question": QUESTION, "language": "en"}

    def evaluation_run():  # a fresh context, as in a new eval process
        records = generate_faithfulness_answers.generate([question], tmp_path / "a.jsonl", run=9)
        return records, trace_steps()

    [record], steps = contextvars.Context().run(evaluation_run)

    assert steps is None  # no trace was started, so nothing was recorded
    assert set(record) == EVAL_RECORD_KEYS
