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
"""

from contextvars import ContextVar


class _Counter:
    __slots__ = ("value",)

    def __init__(self) -> None:
        self.value = 0


_counter_var: ContextVar[_Counter] = ContextVar("citation_counter")


def reset_citation_counter() -> None:
    """Call once at the start of handling a request, before the agent runs."""
    _counter_var.set(_Counter())


def next_citation_numbers(count: int) -> list[int]:
    """Reserve and return the next `count` citation numbers (1-based),
    continuing from wherever the last call (in this request) left off.
    """
    counter = _counter_var.get()
    start = counter.value
    numbers = list(range(start + 1, start + 1 + count))
    counter.value = start + count
    return numbers
