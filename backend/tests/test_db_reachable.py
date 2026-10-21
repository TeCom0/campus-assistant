"""database_reachable() must answer within seconds when Postgres is down.

Regression test for the pytest hang (found 2026-10-15): the DB tests' skip
check runs at collection time, and with no connect timeout an unreachable
database stalled the whole run instead of skipping those tests. No Postgres
needed: both cases use a local socket that isn't a Postgres server.
"""

import socket
import threading
import time

from app.db.connection import database_reachable

# The check is given 1 s per address; well past that means it hangs.
DEADLINE_SECONDS = 15


def _check_in_thread(conninfo: str) -> tuple[list[bool], float]:
    # A daemon thread, so a hanging check fails this test instead of hanging
    # the whole suite (the bug being tested).
    result: list[bool] = []
    start = time.monotonic()
    thread = threading.Thread(
        target=lambda: result.append(database_reachable(conninfo, timeout_seconds=1)),
        daemon=True,
    )
    thread.start()
    thread.join(DEADLINE_SECONDS)
    assert not thread.is_alive(), f"database_reachable still waiting after {DEADLINE_SECONDS} s"
    return result, time.monotonic() - start


def _conninfo(port: int) -> str:
    return f"postgresql://user:password@127.0.0.1:{port}/db"


def test_nothing_listening_on_the_port():
    # Bind to get a free port, then close it: connecting is refused. On
    # Windows this is the case that hung (psycopg never saw the refusal).
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    result, elapsed = _check_in_thread(_conninfo(port))
    assert result == [False]
    assert elapsed < DEADLINE_SECONDS


def test_server_that_accepts_but_never_answers():
    # listen() without accept(): the OS completes the TCP handshake, then
    # nothing ever replies to Postgres's startup message.
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        result, elapsed = _check_in_thread(_conninfo(server.getsockname()[1]))
    assert result == [False]
    assert elapsed < DEADLINE_SECONDS
