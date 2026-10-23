"""Request-scoped trace of the tool calls behind one answer, for the UI's
"Under the hood" panel.

Tools record what they did (the phrasings searched, the passages ranked and
their scores, how long it took); /chat reads the trace after the run and
sends it to the browser. It is display data only: recording never changes
what a tool returns, so the model, the citations and the evaluation see
exactly what they saw before.

Nothing is recorded until start_trace() is called. /chat and the example
generator call it; the evaluation scripts don't, so in an evaluation run
every record_tool_step() is a no-op and the trace stays out of its results.

Same ContextVar pattern as app.agent.citations, for the same reason:
LangChain runs each tool via contextvars.copy_context().run(...), where a
ContextVar.set() made inside the tool doesn't reach the caller. Appending to
an object the caller created does: the copied context holds a reference to
that same object, not a copy of it.
"""

import time
from collections.abc import Callable
from contextvars import ContextVar


class _Trace:
    __slots__ = ("steps",)

    def __init__(self) -> None:
        self.steps: list[dict] = []


# None until start_trace(), so a run that never starts a trace records nothing.
_trace_var: ContextVar[_Trace | None] = ContextVar("trace", default=None)


def start_trace() -> None:
    """Start recording for this request. Call once, before the agent runs."""
    _trace_var.set(_Trace())


def record_tool_step(tool: str, details: dict, call_id: str | None = None) -> None:
    """Record one tool call: its name, the model's id for the call, and what it did.

    A no-op unless a trace was started.
    """
    trace = _trace_var.get()
    if trace is not None:
        trace.steps.append({"tool": tool, "call_id": call_id, **details})


def trace_steps() -> list[dict] | None:
    """The steps recorded so far, in the order recorded; None if no trace was started."""
    trace = _trace_var.get()
    return None if trace is None else list(trace.steps)


def in_call_order(steps: list[dict], call_ids: list[str]) -> list[dict]:
    """The steps in the order the model made the calls.

    ToolNode runs the calls of one round in parallel, so steps are recorded
    in the order the tools finish. `call_ids` is the model's order (its
    tool_calls, round after round). A step with an unknown id keeps its
    recorded place after the known ones.
    """
    position = {call_id: i for i, call_id in enumerate(call_ids)}
    return sorted(steps, key=lambda step: position.get(step["call_id"], len(call_ids)))


class RunTrace:
    """What /chat sees of one run, for its trace event: when each LLM call and
    tool round ended, the tokens each LLM call used, and the model's
    tool-call ids in order.

    The graph runs its nodes one after another, and the "updates" stream
    sends a chunk as each node finishes, so a segment of the timeline starts
    where the previous one ended. `clock` is a parameter so tests can use a
    fake one.
    """

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self._clock = clock
        self._started = clock()
        self._last_ms = 0
        self.timeline: list[dict] = []
        self.call_ids: list[str] = []
        self.first_token_ms: int | None = None

    def _now_ms(self) -> int:
        return round((self._clock() - self._started) * 1000)

    def _segment(self, kind: str, **details) -> None:
        now = self._now_ms()
        self.timeline.append({"kind": kind, "start_ms": self._last_ms, "end_ms": now, **details})
        self._last_ms = now

    def token(self) -> None:
        """A piece of answer text was streamed (only the first one is timed)."""
        if self.first_token_ms is None:
            self.first_token_ms = self._now_ms()

    def agent_message(self, message) -> None:
        """The agent node finished: one LLM call, or the answer built in code
        when the forced answer failed (graph._fallback_answer: no LLM, no tokens)."""
        self.call_ids.extend(call["id"] for call in message.tool_calls)
        if message.response_metadata.get("fallback"):
            self._segment("fallback")
            return
        usage = message.usage_metadata  # None if the provider didn't report it
        self._segment(
            "llm",
            tool_calls=[call["name"] for call in message.tool_calls],
            input_tokens=usage["input_tokens"] if usage else None,
            output_tokens=usage["output_tokens"] if usage else None,
            reasoning_tokens=(usage.get("output_token_details") or {}).get("reasoning")
            if usage
            else None,
        )

    def tools_done(self) -> None:
        """The tools node finished one round of tool calls."""
        self._segment("tools")

    def stopped(self) -> None:
        """The run ended in an error before the node in progress finished."""
        self._segment("stopped")

    @property
    def fell_back(self) -> bool:
        return any(segment["kind"] == "fallback" for segment in self.timeline)

    def event(self, status: str) -> dict:
        """The trace for the browser. `status`: "done", "fallback", "limit" or "error".

        Token totals add up only what the provider reported; `tokens_complete`
        says whether every LLM call reported, so a missing figure is never
        shown as a smaller one.
        """
        llm_calls = [s for s in self.timeline if s["kind"] == "llm"]

        def known_sum(key: str) -> int:
            return sum(s[key] for s in llm_calls if s[key] is not None)

        return {
            "status": status,
            "steps": in_call_order(trace_steps() or [], self.call_ids),
            "timeline": self.timeline,
            "totals": {
                "duration_ms": self._last_ms,
                "first_token_ms": self.first_token_ms,
                "llm_calls": len(llm_calls),
                "input_tokens": known_sum("input_tokens"),
                "output_tokens": known_sum("output_tokens"),
                "reasoning_tokens": known_sum("reasoning_tokens"),
                "tokens_complete": all(s["input_tokens"] is not None for s in llm_calls),
            },
        }


# The panel shows the start of each retrieved passage. ~200 characters for up
# to 15 passages (3 searches x top 5) is about 3 KB per answer.
SNIPPET_CHARS = 200


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    """The start of a passage for the panel: at most `limit` characters, cut at a
    word, with "…" when cut.

    A chunk's first line can be its "Section: ..." line (app.ingestion.chunk);
    the panel shows the section separately, so that line is skipped.
    """
    lines = text.split("\n")
    if lines and lines[0].startswith("Section: "):
        lines = lines[1:]
    flat = " ".join(" ".join(lines).split())  # newlines and runs of spaces to one space
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0] if " " in flat[:limit] else flat[:limit]
    return cut.rstrip(" ,;:.") + "…"
