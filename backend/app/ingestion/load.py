"""Download the registry's documents (data/registry.toml) into data/raw/ (A2.4 step 6).

    python -m app.ingestion.load                      # every edition
    python -m app.ingestion.load <edition id> [...]

What is downloaded is checked before it is kept:

1. every URL, the registered one and each redirect, is https on a host the registry's own
   URLs use (allowed_hosts). Redirects are followed by hand, at most MAX_REDIRECTS, and a
   URL is checked before it is requested, so an off-host one is never contacted;
2. each request has a connect and a read timeout, and the whole download a deadline: a
   server sending a byte every few seconds never trips the read timeout;
3. the size cap of gates.py for the edition's format, from Content-Length before reading,
   and again while reading, since the header can be missing or wrong;
4. the sha256 of what was received is the registry's.

The body goes to a .part file next to the destination and is renamed into place only when
every check passed, so data/raw never holds a partial or unregistered file. A file already
there is kept if its sha256 is the registry's, and refused otherwise: never overwritten.
Every file's sha256 is printed, a refused one's too: a changed file becomes a new edition,
registered with that hash. The exit code is 0 only if every edition is in place.
"""

import argparse
import hashlib
import os
import sys
import time
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from app.ingestion.gates import MAX_FILE_BYTES
from app.registry import Edition, Registry, load_registry

# data/raw/ lives at the repo root, three levels up from this file
# (ingestion -> app -> backend -> repo root).
DATA_RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

MAX_REDIRECTS = 5
TIMEOUT = (10, 30)  # seconds: to connect, and between two reads
DEADLINE_SECONDS = 300  # the whole download; the catalog (2.8 MB) takes a few seconds
BLOCK_BYTES = 64 * 1024
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class DownloadRefused(Exception):
    """A download that wasn't kept; data/raw is as it was."""


def allowed_hosts(registry: Registry) -> frozenset[str]:
    """The hosts the registry's URLs name, exactly: no subdomain is implied."""
    urls = [e.source_url for e in registry.editions]
    urls += [e.fallback_url for e in registry.editions if e.fallback_url]
    return frozenset(urlsplit(url).hostname for url in urls)


def check_url(url: str, hosts: frozenset[str]) -> None:
    """Refuse a URL that isn't https on an allowed host, with nothing that could disguise
    one: user info (https://allowed.host@elsewhere/, whose host is elsewhere) or a port."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in hosts
        or "@" in parts.netloc  # user info, with or without a password
        or parts.port is not None
    ):
        raise DownloadRefused(
            f"{url!r} isn't https on an allowed host ({', '.join(sorted(hosts))})"
        )


Get = Callable[..., requests.Response]


def fetch(
    url: str,
    part: Path,
    *,
    hosts: frozenset[str],
    max_bytes: int,
    get: Get = requests.get,
    clock: Callable[[], float] = time.monotonic,
    deadline: float = DEADLINE_SECONDS,
) -> tuple[int, str]:
    """Download `url` into `part`; returns its size and sha256. On any refusal or error,
    `part` is removed and the exception raised."""
    started = clock()

    def in_time() -> None:
        if clock() - started > deadline:
            raise DownloadRefused(f"{url!r}: not finished within {deadline:g} s")

    redirects = 0
    while True:
        check_url(url, hosts)
        in_time()
        response = get(url, allow_redirects=False, timeout=TIMEOUT, stream=True)
        if response.status_code not in REDIRECT_STATUSES:
            break
        location = response.headers.get("location")
        response.close()
        redirects += 1
        if redirects > MAX_REDIRECTS:
            raise DownloadRefused(f"{url!r}: more than {MAX_REDIRECTS} redirects")
        if not location:
            raise DownloadRefused(f"{url!r}: a redirect with no Location")
        url = urljoin(url, location)

    with closing(response):
        if response.status_code != 200:
            raise DownloadRefused(f"{url!r}: HTTP {response.status_code}")
        length = response.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > max_bytes):
            raise DownloadRefused(f"{url!r}: Content-Length {length}, limit {max_bytes} bytes")
        digest, size = hashlib.sha256(), 0
        try:
            with open(part, "wb") as f:
                for block in response.iter_content(chunk_size=BLOCK_BYTES):
                    size += len(block)
                    if size > max_bytes:
                        raise DownloadRefused(f"{url!r}: over the {max_bytes}-byte limit")
                    in_time()
                    digest.update(block)
                    f.write(block)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
    return size, digest.hexdigest()


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_edition(
    edition: Edition, raw_dir: Path, hosts: frozenset[str], get: Get = requests.get, **fetch_args
) -> str:
    """Put one edition's registered file in raw_dir; returns what was done, for the report.
    Raises DownloadRefused (or a requests error), leaving raw_dir as it was."""
    dest = raw_dir / edition.filename
    if dest.exists():
        digest = _sha256_of(dest)
        if digest != edition.sha256:
            raise DownloadRefused(
                f"{dest.name} is already there with sha256 {digest}, not the registry's "
                f"{edition.sha256}. Not overwritten."
            )
        return f"kept {dest.name}: already there, sha256 {digest} (the registry's)"

    part = dest.with_name(dest.name + ".part")
    size, digest = fetch(
        edition.source_url,
        part,
        hosts=hosts,
        max_bytes=MAX_FILE_BYTES[edition.format],
        get=get,
        **fetch_args,
    )
    if digest != edition.sha256:
        part.unlink()
        raise DownloadRefused(
            f"{edition.source_url!r}: received {size} bytes with sha256 {digest}, the registry "
            f"says {edition.sha256}. Not kept: a changed file is a new edition, registered "
            "with this sha256."
        )
    os.replace(part, dest)
    return f"saved {dest.name}: {size} bytes, sha256 {digest} (the registry's)"


def main(argv: list[str] | None = None, raw_dir: Path = DATA_RAW_DIR, get: Get = requests.get):
    parser = argparse.ArgumentParser(description="Download the registry's documents.")
    parser.add_argument("editions", nargs="*", help="edition ids (default: every edition)")
    args = parser.parse_args(argv)
    registry = load_registry()
    editions = [registry.edition(e) for e in args.editions] or list(registry.editions)
    hosts = allowed_hosts(registry)

    raw_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for edition in editions:
        try:
            print(f"{edition.id}: {download_edition(edition, raw_dir, hosts, get)}")
        except (DownloadRefused, requests.RequestException) as e:
            failed += 1
            print(f"{edition.id}: REFUSED: {type(e).__name__}: {e}")
    print(f"{len(editions) - failed}/{len(editions)} editions in place in {raw_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
