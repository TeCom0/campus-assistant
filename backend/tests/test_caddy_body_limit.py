"""The body limit and timeouts in deploy/Caddyfile, proven on real Caddy.

Reading the Caddyfile can't show that a body really gets a 413: that depends on
how Caddy handles the directive, and it needs an upstream reading the body. So
this runs the image production pins, with the repo's Caddyfile, in front of a
small stub standing in for the API and the UI.

Needs Docker. Without it the test skips on a laptop, but fails in CI: a skipped
test would otherwise leave the limit unproven on a green run.
"""

import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

from app.config import MAX_BODY_BYTES

REPO_ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = REPO_ROOT / "deploy" / "Caddyfile"
MARKER = "SECRETMARKER123"

# Reads the whole body, the way the API does, and answers with its size. The
# request_body limit only fires when the upstream side reads past it.
STUB_UPSTREAM = """
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        size = 0
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            while True:
                chunk = int(self.rfile.readline().strip() or b"0", 16)
                if chunk == 0:
                    self.rfile.readline()
                    break
                size += len(self.rfile.read(chunk))
                self.rfile.readline()
        else:
            size = len(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        if "/stream/" in self.path:
            # Like /chat: a POST answered as a stream, with a pause between its parts.
            pause = float(self.path.rsplit("/", 1)[1])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for part in (b"first", b"second", b"third"):
                self.wfile.write(b"%x\\r\\n%s\\r\\n" % (len(part), part))
                self.wfile.flush()
                time.sleep(pause)
            self.wfile.write(b"0\\r\\n\\r\\n")
            self.wfile.flush()
            return
        reply = str(size).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
"""


def _docker(*args: str) -> str:
    done = subprocess.run(["docker", *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


def _production_caddy_image() -> str:
    text = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    return re.search(r"image:\s*(caddy:\S+)", text).group(1)


@pytest.fixture(scope="module")
def caddy():
    """The URL of Caddy in front of the stub, and a function reading Caddy's log."""
    if not _docker_available():
        if os.environ.get("CI"):
            pytest.fail("Docker is required in CI: the Caddy body limit must not go unproven")
        pytest.skip("Docker is not available")

    suffix = uuid.uuid4().hex[:8]
    network, upstream, proxy = (f"caddy-limit-{name}-{suffix}" for name in ("net", "up", "caddy"))
    _docker("network", "create", network)
    try:
        _docker(
            "run",
            "-d",
            "--rm",
            "--name",
            upstream,
            "--network",
            network,
            "--network-alias",
            "api",
            "--network-alias",
            "frontend",
            "python:3.12-alpine",
            "python",
            "-c",
            STUB_UPSTREAM,
        )
        _docker(
            "run",
            "-d",
            "--rm",
            "--name",
            proxy,
            "--network",
            network,
            "-p",
            "127.0.0.1::80",
            "-e",
            "DOMAIN=:80",
            "-v",
            f"{CADDYFILE}:/etc/caddy/Caddyfile:ro",
            _production_caddy_image(),
        )
        port = _docker("port", proxy, "80/tcp").rsplit(":", 1)[1]
        url = f"http://127.0.0.1:{port}"

        deadline = time.monotonic() + 30
        while True:
            try:
                if httpx.post(f"{url}/api/chat", content=b"x", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                pytest.fail("Caddy and the stub did not start in 30 s")
            time.sleep(0.5)

        yield (
            url,
            lambda: (
                subprocess.run(
                    ["docker", "logs", proxy], capture_output=True, text=True, check=False
                ).stderr
            ),
        )
    finally:
        for container in (proxy, upstream):
            subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
        subprocess.run(["docker", "network", "rm", network], capture_output=True, check=False)


def _body(size: int) -> bytes:
    return (MARKER.encode() + b"x" * size)[:size]


def _chunked(body: bytes):
    """A generator makes httpx send it chunked, with no Content-Length."""
    for start in range(0, len(body), 8192):
        yield body[start : start + 8192]


@pytest.mark.parametrize(
    ("size", "status"),
    [
        (MAX_BODY_BYTES, 200),
        (MAX_BODY_BYTES + 1, 413),
        (65 * 1024, 413),
        (200_000, 413),
    ],
    ids=["at_limit", "one_byte_over", "65_KiB", "far_over"],
)
@pytest.mark.parametrize("framing", ["content_length", "chunked"])
def test_caddy_refuses_a_body_over_the_limit(caddy, size, status, framing):
    url, _ = caddy
    body = _body(size)
    content = body if framing == "content_length" else _chunked(body)

    response = httpx.post(f"{url}/api/chat", content=content, timeout=20)

    assert response.status_code == status
    if status == 200:
        assert response.text == str(size)  # the whole body reached the upstream


def test_a_refused_body_leaves_no_text_in_caddys_log(caddy):
    url, read_log = caddy
    httpx.post(f"{url}/api/chat", content=_body(MAX_BODY_BYTES + 1), timeout=20)
    assert MARKER not in read_log()


def _stream(url: str, pause: float, encoding: str) -> list[tuple[bytes, float]]:
    """Each part of a streamed answer, decoded, with the seconds since the request began.
    Browsers ask for compression, and Caddy's encode directive then applies to the stream."""
    start = time.monotonic()
    parts = []
    with httpx.stream(
        "POST",
        f"{url}/api/stream/{pause}",
        content=b"{}",
        headers={"Accept-Encoding": encoding},
        timeout=pause + 30,
    ) as reply:
        assert reply.status_code == 200
        assert reply.headers.get("content-encoding", "identity") == encoding
        for chunk in reply.iter_bytes():
            if chunk:
                parts.append((chunk, time.monotonic() - start))
    return parts


@pytest.mark.parametrize("encoding", ["identity", "gzip"])
def test_a_streamed_answer_arrives_piece_by_piece(caddy, encoding):
    url, _ = caddy
    parts = _stream(url, 1.5, encoding)
    assert b"".join(chunk for chunk, _ in parts) == b"firstsecondthird"
    # The first part got through long before the last: nothing buffered the stream.
    assert parts[-1][1] - parts[0][1] >= 2.5


@pytest.mark.skipif(
    not os.environ.get("CADDY_LONG_STREAM"),
    reason="takes over 3 minutes: run by hand on an upgrade",
)
def test_a_stream_that_pauses_past_the_default_timeouts_survives(caddy):
    # 2.11.6 cut off POSTed streams after 60 s, and reset quiet ones. 2.11.7 fixed both.
    url, _ = caddy
    parts = _stream(url, 70, "gzip")
    assert b"".join(chunk for chunk, _ in parts) == b"firstsecondthird"
    assert parts[-1][1] - parts[0][1] >= 130


def test_a_client_that_never_finishes_its_headers_is_dropped(caddy):
    url, _ = caddy
    port = int(url.rsplit(":", 1)[1])
    start = time.monotonic()
    with socket.create_connection(("127.0.0.1", port), timeout=20) as client:
        client.sendall(b"POST /api/chat HTTP/1.1\r\nHost: x\r\nX-Slow: ")
        received = b""
        while True:  # until Caddy gives up on it and closes the connection
            chunk = client.recv(1024)
            if not chunk:
                break
            received += chunk
    elapsed = time.monotonic() - start
    assert 8 <= elapsed <= 16, elapsed  # read_header 10s, not Caddy's default 1m


def test_the_image_is_pinned_by_digest_and_the_timeouts_are_set():
    assert "@sha256:" in _production_caddy_image()
    caddyfile = CADDYFILE.read_text(encoding="utf-8")
    for line in ("read_header 10s", "read_body 30s", "read_body_idle 10s", "idle 2m"):
        assert line in caddyfile
    # A hard limit on writes would cut a long streamed answer off.
    assert not re.search(r"^\s*write(_idle)?\s", caddyfile, re.MULTILINE)


def test_the_caddy_limit_is_the_same_as_the_apps():
    # 64KB would be 64,000 bytes to Caddy: the unit matters, not only the digits.
    match = re.search(r"max_size (\d+)KiB", CADDYFILE.read_text(encoding="utf-8"))
    assert match, "the limit must be written in KiB"
    assert int(match.group(1)) * 1024 == MAX_BODY_BYTES
