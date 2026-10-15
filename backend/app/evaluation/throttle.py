"""Keeps API calls under two limits at once: requests per second and tokens per
minute (input + output tokens of every call in the last 60 seconds).

Sliding window: the throttle remembers when each recent call started and how
many tokens it used. Before a call it waits until (a) the minimum gap since the
previous call has passed and (b) the window's tokens plus this call's estimate
fit under the per-minute limit -- old calls age out of the window as time
passes. The estimate is replaced by the real count once the call returns, so
estimation errors don't add up over a run.

The clock and sleep functions are parameters so tests can use a fake clock.
"""

import time
from collections.abc import Callable

WINDOW_SECONDS = 60


class Call:
    """One call in the window: when it started and its tokens (estimated until
    the reply says how many it really used)."""

    def __init__(self, started_at: float, tokens: int):
        self.started_at = started_at
        self.tokens = tokens


class Throttle:
    def __init__(
        self,
        requests_per_second: float,
        tokens_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_gap = 1 / requests_per_second
        self.tokens_per_minute = tokens_per_minute
        self.clock = clock
        self.sleep = sleep
        self.window: list[Call] = []  # oldest first

    def wait_for_slot(self, estimated_tokens: int) -> Call:
        """Sleep until a call of about estimated_tokens is allowed, then record it."""
        while True:
            now = self.clock()
            self.window = [c for c in self.window if now - c.started_at < WINDOW_SECONDS]
            wait = 0.0
            if self.window:
                wait = self.window[-1].started_at + self.min_gap - now
                used = sum(c.tokens for c in self.window)
                if used + estimated_tokens > self.tokens_per_minute:
                    # Until the oldest call leaves the window; then check again.
                    wait = max(wait, self.window[0].started_at + WINDOW_SECONDS - now)
            # An empty window always lets the call through, even one larger than
            # the limit on its own: waiting longer couldn't make it fit.
            if wait <= 0:
                break
            self.sleep(wait)
        call = Call(now, estimated_tokens)
        self.window.append(call)
        return call

    @staticmethod
    def record_actual(call: Call, tokens: int) -> None:
        call.tokens = tokens
