"""Tests for the requests-per-second + tokens-per-minute throttle
(app.evaluation.throttle), with a fake clock: no real waiting."""

from app.evaluation.throttle import Throttle


class FakeClock:
    """time.monotonic + time.sleep stand-ins: sleeping just moves the clock."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _throttle(rps: float, tpm: int) -> tuple[Throttle, FakeClock]:
    fake = FakeClock()
    return Throttle(rps, tpm, clock=fake.clock, sleep=fake.sleep), fake


def test_small_calls_are_spaced_by_the_requests_per_second_limit():
    throttle, fake = _throttle(rps=0.5, tpm=250_000)
    for _ in range(3):
        throttle.wait_for_slot(1_000)
    assert fake.sleeps == [2.0, 2.0]  # 0.5 requests/second = one every 2 s


def test_large_calls_wait_for_the_token_window():
    # 20k tokens/minute and 11k-token calls: two never fit in the same minute.
    throttle, _ = _throttle(rps=1, tpm=20_000)
    first = throttle.wait_for_slot(11_000)
    second = throttle.wait_for_slot(11_000)
    assert (first.started_at, second.started_at) == (0.0, 60.0)


def test_the_real_token_count_replaces_the_estimate():
    throttle, _ = _throttle(rps=1, tpm=20_000)
    call = throttle.wait_for_slot(15_000)  # estimated high...
    throttle.record_actual(call, 5_000)  # ...but the reply says 5k
    second = throttle.wait_for_slot(11_000)  # 5k + 11k fits: only the 1 s gap
    assert second.started_at == 1.0


def test_calls_leave_the_window_after_a_minute():
    throttle, _ = _throttle(rps=1, tpm=20_000)
    throttle.wait_for_slot(8_000)  # t=0
    throttle.wait_for_slot(8_000)  # t=1
    third = throttle.wait_for_slot(8_000)  # 24k > 20k: waits for the t=0 call to age out
    assert third.started_at == 60.0
    assert [c.started_at for c in throttle.window] == [1.0, 60.0]


def test_a_call_larger_than_the_limit_still_goes_through_on_an_empty_window():
    throttle, fake = _throttle(rps=1, tpm=20_000)
    throttle.wait_for_slot(25_000)
    assert fake.sleeps == []
