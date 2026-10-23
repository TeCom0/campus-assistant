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


def record_tool_step(tool: str, details: dict) -> None:
    """Record one tool call: its name and what it did. A no-op unless a trace was started."""
    trace = _trace_var.get()
    if trace is not None:
        trace.steps.append({"tool": tool, **details})


def trace_steps() -> list[dict] | None:
    """The steps recorded so far, in the order recorded; None if no trace was started."""
    trace = _trace_var.get()
    return None if trace is None else list(trace.steps)


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
