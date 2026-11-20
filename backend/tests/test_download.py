"""Downloading the registry's documents (A2.4 step 6; CLAUDE.md, "A2.4 rule", item 9).

Every URL, the registered one and each redirect, must be https on a host the registry's own
URLs use, and is checked before it is requested. Each request has a timeout and the whole
download a deadline; the size cap applies to the header and to what is read; what is kept
in data/raw is only ever a complete file with the registry's sha256.

No network: a stand-in `get` serves scripted responses and records what was asked for.
"""

import hashlib
from dataclasses import replace

import pytest
import requests
from test_ingest_gates import _fixture_registry

from app.ingestion import load
from app.ingestion.load import (
    MAX_REDIRECTS,
    TIMEOUT,
    DownloadRefused,
    allowed_hosts,
    check_url,
    download_edition,
    fetch,
)
from app.registry import load_registry, registry_of

HOSTS = frozenset({"aui.ma"})
BODY = b"%PDF-1.7 registered content"
URL = "https://aui.ma/hubfs/catalog.pdf"


class FakeResponse:
    def __init__(self, status=200, headers=None, blocks=(BODY,)):
        self.status_code = status
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._blocks = blocks
        self.closed = False

    def iter_content(self, chunk_size):
        for block in self._blocks:
            if isinstance(block, Exception):
                raise block
            yield block

    def close(self):
        self.closed = True


class FakeGet:
    """Serves responses by URL, and records every request with its arguments."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url not in self.responses:
            raise AssertionError(f"requested {url!r}, which the test didn't expect")
        return self.responses[url]

    @property
    def urls(self):
        return [url for url, _ in self.calls]


def _redirect(location, status=302):
    return FakeResponse(status, {"Location": location}, blocks=())


def _edition(body: bytes = BODY, **changes):
    edition = load_registry().course_tables_edition()
    return replace(edition, sha256=hashlib.sha256(body).hexdigest(), source_url=URL, **changes)


def _files(path):
    return sorted(p.name for p in path.iterdir())


# --- The allow-list ------------------------------------------------------------------------


def test_the_allowed_hosts_are_exactly_the_registrys():
    assert allowed_hosts(load_registry()) == {"aui.ma"}
    assert "fixtures.invalid" in allowed_hosts(_fixture_registry())


@pytest.mark.parametrize(
    "url",
    [
        "http://aui.ma/catalog.pdf",  # not https
        "https://elsewhere.example/catalog.pdf",
        "https://www.aui.ma/catalog.pdf",  # a subdomain isn't implied
        "https://aui.ma.elsewhere.example/catalog.pdf",
        "https://aui.ma@elsewhere.example/catalog.pdf",  # user info: the host is elsewhere
        "https://user:pw@aui.ma/catalog.pdf",
        "https://user@aui.ma/catalog.pdf",
        "https://:pw@aui.ma/catalog.pdf",
        "https://aui.ma:8443/catalog.pdf",
        "ftp://aui.ma/catalog.pdf",
    ],
)
def test_a_url_off_the_allowed_hosts_is_refused(url):
    with pytest.raises(DownloadRefused, match="allowed host"):
        check_url(url, HOSTS)


def test_an_allowed_url_passes():
    check_url(URL + "?hsLang=en", HOSTS)


# --- Redirects (rule item 9: off-host redirect) ----------------------------------------------


def test_an_off_host_redirect_is_refused_and_never_requested(tmp_path):
    get = FakeGet({URL: _redirect("https://elsewhere.example/catalog.pdf")})
    with pytest.raises(DownloadRefused, match="elsewhere.example"):
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert get.urls == [URL]
    assert _files(tmp_path) == []


def test_a_redirect_to_http_on_the_same_host_is_refused(tmp_path):
    get = FakeGet({URL: _redirect("http://aui.ma/hubfs/catalog.pdf", 301)})
    with pytest.raises(DownloadRefused, match="https"):
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert get.urls == [URL]


def test_an_on_host_redirect_is_followed_and_relative_locations_resolved(tmp_path):
    get = FakeGet(
        {
            URL: _redirect("/files/catalog-v2.pdf", 307),
            "https://aui.ma/files/catalog-v2.pdf": FakeResponse(),
        }
    )
    download_edition(_edition(), tmp_path, HOSTS, get)
    assert get.urls == [URL, "https://aui.ma/files/catalog-v2.pdf"]
    assert (tmp_path / _edition().filename).read_bytes() == BODY


def test_more_than_the_redirect_limit_is_refused(tmp_path):
    chain = {f"https://aui.ma/{n}": _redirect(f"/{n + 1}") for n in range(MAX_REDIRECTS + 1)}
    get = FakeGet(chain)
    with pytest.raises(DownloadRefused, match="redirects"):
        fetch("https://aui.ma/0", tmp_path / "x.part", hosts=HOSTS, max_bytes=100, get=get)
    assert len(get.urls) == MAX_REDIRECTS + 1


def test_a_redirect_without_a_location_is_refused(tmp_path):
    get = FakeGet({URL: FakeResponse(302, {}, blocks=())})
    with pytest.raises(DownloadRefused, match="no Location"):
        fetch(URL, tmp_path / "x.part", hosts=HOSTS, max_bytes=100, get=get)


def test_every_request_follows_no_redirect_itself_and_has_a_timeout(tmp_path):
    get = FakeGet({URL: _redirect("/b"), "https://aui.ma/b": FakeResponse()})
    download_edition(_edition(), tmp_path, HOSTS, get)
    assert [kwargs for _, kwargs in get.calls] == [
        {"allow_redirects": False, "timeout": TIMEOUT, "stream": True}
    ] * 2


# --- Size, time, status ------------------------------------------------------------------------


def test_a_content_length_over_the_cap_is_refused_before_reading(tmp_path):
    unread = FakeResponse(headers={"Content-Length": "101"}, blocks=(AssertionError("read"),))
    with pytest.raises(DownloadRefused, match="Content-Length 101"):
        fetch(URL, tmp_path / "x.part", hosts=HOSTS, max_bytes=100, get=FakeGet({URL: unread}))
    assert unread.closed and _files(tmp_path) == []


def test_a_malformed_content_length_is_refused(tmp_path):
    response = FakeResponse(headers={"Content-Length": "-5"})
    with pytest.raises(DownloadRefused, match="Content-Length"):
        fetch(URL, tmp_path / "x.part", hosts=HOSTS, max_bytes=100, get=FakeGet({URL: response}))


def test_a_body_over_the_cap_is_refused_while_reading_and_nothing_is_left(tmp_path):
    # No Content-Length, or a wrong one: the cap holds on what is actually read.
    response = FakeResponse(headers={"Content-Length": "10"}, blocks=(b"x" * 60, b"x" * 60))
    with pytest.raises(DownloadRefused, match="100-byte limit"):
        fetch(URL, tmp_path / "x.part", hosts=HOSTS, max_bytes=100, get=FakeGet({URL: response}))
    assert _files(tmp_path) == []


def test_the_size_cap_is_the_gates_limit_for_the_format(tmp_path, monkeypatch):
    monkeypatch.setitem(load.MAX_FILE_BYTES, "pdf", len(BODY) - 1)
    get = FakeGet({URL: FakeResponse()})
    with pytest.raises(DownloadRefused, match="limit"):
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert _files(tmp_path) == []


def test_a_download_past_the_deadline_is_refused_and_nothing_is_left(tmp_path):
    now = iter(range(0, 1000, 100))  # each reading of the clock is 100 s later
    response = FakeResponse(blocks=(b"a", b"b", b"c", b"d"))
    with pytest.raises(DownloadRefused, match="within 250 s"):
        fetch(
            URL,
            tmp_path / "x.part",
            hosts=HOSTS,
            max_bytes=100,
            get=FakeGet({URL: response}),
            clock=lambda: next(now),
            deadline=250,
        )
    assert _files(tmp_path) == []


def test_an_error_status_is_refused(tmp_path):
    get = FakeGet({URL: FakeResponse(404, blocks=())})
    with pytest.raises(DownloadRefused, match="HTTP 404"):
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert _files(tmp_path) == []


def test_a_connection_dropped_part_way_leaves_nothing(tmp_path):
    broken = FakeResponse(blocks=(b"part of it", requests.ConnectionError("reset")))
    with pytest.raises(requests.ConnectionError):
        download_edition(_edition(), tmp_path, HOSTS, FakeGet({URL: broken}))
    assert _files(tmp_path) == []


# --- The hash, and what is kept ----------------------------------------------------------------


def test_a_file_with_the_registrys_hash_is_saved_and_its_hash_reported(tmp_path):
    report = download_edition(_edition(), tmp_path, HOSTS, FakeGet({URL: FakeResponse()}))
    assert _files(tmp_path) == [_edition().filename]  # no .part left
    assert hashlib.sha256(BODY).hexdigest() in report and f"{len(BODY)} bytes" in report


def test_a_file_with_another_hash_is_not_kept_and_its_hash_is_printed(tmp_path):
    changed = b"%PDF-1.7 the publisher changed it"
    get = FakeGet({URL: FakeResponse(blocks=(changed,))})
    with pytest.raises(DownloadRefused) as refused:
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert hashlib.sha256(changed).hexdigest() in str(refused.value)
    assert "new edition" in str(refused.value)
    assert _files(tmp_path) == []


def test_a_file_already_there_with_the_registrys_hash_is_kept_without_a_request(tmp_path):
    (tmp_path / _edition().filename).write_bytes(BODY)
    get = FakeGet({})
    assert download_edition(_edition(), tmp_path, HOSTS, get).startswith("kept")
    assert get.urls == []


def test_a_file_already_there_with_another_hash_is_refused_and_not_overwritten(tmp_path):
    (tmp_path / _edition().filename).write_bytes(b"something else")
    get = FakeGet({})
    with pytest.raises(DownloadRefused, match="Not overwritten"):
        download_edition(_edition(), tmp_path, HOSTS, get)
    assert (tmp_path / _edition().filename).read_bytes() == b"something else"
    assert get.urls == []


# --- The command -------------------------------------------------------------------------------


def test_the_command_downloads_the_registry_and_exits_1_on_any_refusal(tmp_path, capsys):
    # Every registered URL is requested, in order. The stand-in serves bytes that aren't the
    # registered files, so each is refused, its hash printed, and nothing kept.
    editions = load_registry().editions
    get = FakeGet({e.source_url: FakeResponse(blocks=(e.id.encode(),)) for e in editions})
    assert load.main([], raw_dir=tmp_path, get=get) == 1
    assert get.urls == [e.source_url for e in editions]
    out = capsys.readouterr().out
    for edition in editions:
        assert hashlib.sha256(edition.id.encode()).hexdigest() in out
    assert f"0/{len(editions)} editions in place" in out
    assert _files(tmp_path) == []


def test_the_command_exits_0_when_every_file_is_in_place(tmp_path, capsys, monkeypatch):
    registry = load_registry()
    edition = registry.editions[0]
    (tmp_path / edition.filename).write_bytes(b"x")
    # The registry, with this edition's hash being the file's.
    in_place = replace(edition, sha256=hashlib.sha256(b"x").hexdigest())
    documents = tuple(
        replace(d, editions=tuple(in_place if e.id == edition.id else e for e in d.editions))
        for d in registry.documents
    )
    monkeypatch.setattr(load, "load_registry", lambda: registry_of(documents))
    assert load.main([edition.id], raw_dir=tmp_path, get=FakeGet({})) == 0
    assert "1/1 editions in place" in capsys.readouterr().out
