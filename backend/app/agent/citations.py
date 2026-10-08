"""Request-scoped citation numbering, shared across all tool calls within
one agent run, so a second (or third) tool call continues the [N]
numbering sequence instead of each tool restarting at [1].

Uses a ContextVar holding a MUTABLE counter object, not a plain int.
LangChain's tool-execution machinery runs each tool call via
contextvars.copy_context().run(...), and a plain ContextVar.set() made
inside that copied context does NOT propagate back out (verified directly
-- this is standard, correct contextvars isolation, by design, for
thread/task safety). A mutable object survives this: copying a context
copies the *binding* (a reference to the same object), not a deep copy, so
mutating the object's own attribute (not rebinding the ContextVar) is
visible across every tool call that shares the reference -- which they all
do, since none of them ever call reset_citation_counter() themselves.

A passage gets ONE number per request: several searches often return the
same chunk (3 searches for "What is MTH 1305?" gave 15 results but only 10
distinct chunks), and numbering each copy separately listed the same source
several times. The counter keeps a key -> number dict on the same mutable
object, so it crosses the copy_context() boundary the same way.
"""

import re
from collections.abc import Hashable
from contextvars import ContextVar


class _Counter:
    __slots__ = ("numbers", "value")

    def __init__(self) -> None:
        self.value = 0
        self.numbers: dict[Hashable, int] = {}


_counter_var: ContextVar[_Counter] = ContextVar("citation_counter")


def reset_citation_counter() -> None:
    """Call once at the start of handling a request, before the agent runs."""
    _counter_var.set(_Counter())


def citation_number_for(key: Hashable) -> tuple[int, bool]:
    """Return (number, is_new) for the passage identified by `key`.

    A key already numbered in this request gets its earlier number back
    (is_new=False); a new key gets the next number in the sequence.
    """
    counter = _counter_var.get()
    if key in counter.numbers:
        return counter.numbers[key], False
    counter.value += 1
    counter.numbers[key] = counter.value
    return counter.value, True


# "[3]", and also "[2, 4]" -- the prompt asks for one number per bracket, but
# a grouped citation still means both sources were used.
_CITED_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def cited_markers(answer: str) -> set[int]:
    """Every citation number the answer text uses."""
    return {int(number) for group in _CITED_RE.findall(answer) for number in group.split(",")}


def keep_cited(citations: list[dict], answer: str) -> list[dict]:
    """The citations the answer actually cites, once per marker, in marker order.

    Tools return a citation for every passage they hand the model, including
    ones it never uses, and a repeated passage comes back with its earlier
    marker; listing them all showed students sources the answer didn't use.
    """
    used = cited_markers(answer)
    by_marker = {c["marker"]: c for c in citations if c["marker"] in used}
    return [by_marker[marker] for marker in sorted(by_marker)]
