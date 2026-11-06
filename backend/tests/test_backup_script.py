"""The backup script, run for real with stubbed tools: it refuses a bad setup, a
failure anywhere means no BACKUP OK and no ping, and its proof comes from what B2
reports. The B2 replies below are the real b2 v5.0.2 binary's output, captured against a
local fake server, one with the right to read retention and one without.

Not on Windows: the script needs real file modes.
"""

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / "deploy" / "backup"
SCRIPT = BACKUP_DIR / "campus-backup.sh"
RECIPIENT = "age1" + "q" * 58
SECRET_KEY = "SECRETB2KEYMARKER"
PING_URL = "https://hc-ping.com/SECRETPINGMARKER"
OBJECT_SIZE = 2_000_000

BASH = shutil.which("bash")
posix_only = pytest.mark.skipif(
    sys.platform == "win32" or BASH is None, reason="needs bash and real file modes"
)


def b2_reply(mode="compliance", days=30, retain_ms="default", size=None, sha1=None):
    """The shape b2 file upload prints: two URL lines, then JSON."""
    until = int((datetime.now(UTC) + timedelta(days=days)).timestamp() * 1000)
    return {
        "mode": mode,
        "until": until if retain_ms == "default" else retain_ms,
        "size": size,
        "sha1": sha1,
    }


class Sandbox:
    """A config folder and stub tools. Each stub records that it ran."""

    def __init__(self, root: Path):
        self.root = root
        self.config = root / "etc"
        self.tools = root / "tools"
        self.work = root / "work"
        self.bin = root / "bin"
        self.calls = root / "calls"
        for folder in (self.config, self.tools, self.bin):
            folder.mkdir()
        self.calls.write_text("")
        (self.config / "age-recipient.txt").write_text(RECIPIENT + "\n")
        self._secret("b2.env", f"B2_APPLICATION_KEY_ID=KEYID\nB2_APPLICATION_KEY={SECRET_KEY}\n")
        self._secret("healthcheck-url", PING_URL + "\n")
        (self.tools / "fingerprint.sql").write_text("select 1;\n")
        self.docker(0)
        self.age(0)
        self.b2(0, b2_reply())
        self.curl(0, "OK")

    def _secret(self, name: str, text: str) -> None:
        path = self.config / name
        path.write_text(text)
        path.chmod(0o600)

    def _stub(self, path: Path, body: str) -> None:
        path.write_text(f"#!/usr/bin/env bash\necho {path.name} >> {self.calls}\n{body}\n")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def docker(self, code: int) -> None:
        self._stub(
            self.bin / "docker",
            f'case "$*" in *pg_dump*) head -c 1000 /dev/zero; exit {code};; '
            '*psql*) echo "document_chunks 1161 abc"; exit 0;; esac',
        )

    def age(self, code: int, size: int = OBJECT_SIZE, header: bool = True) -> None:
        first = "age-encryption.org/v1" if header else "not-an-age-file-here!"
        self._stub(
            self.tools / "age",
            'while [ $# -gt 0 ]; do [ "$1" = "-o" ] && out="$2"; shift; done\n'
            "cat > /dev/null\n"
            f'printf "{first}" > "$out"\n'
            f'head -c {size - len(first)} /dev/zero >> "$out"\n'
            f"exit {code}",
        )

    def b2(self, code: int, reply: dict) -> None:
        # The file's real size and SHA-1, unless a test wants them wrong.
        size = reply["size"] if reply["size"] is not None else '$(stat -c %s "$src")'
        sha1 = reply["sha1"] or '$(sha1sum "$src" | cut -d" " -f1)'
        until = "null" if reply["until"] is None else reply["until"]
        self._stub(
            self.tools / "b2",
            'src="${@: -2:1}"; name="${@: -1}"\n'
            f'[ "$B2_APPLICATION_KEY" = "{SECRET_KEY}" ] || exit 9\n'
            'echo "URL by file name: https://example/file/bucket/$name"\n'
            'echo "URL by fileId: https://example/b2_download_file_by_id?fileId=4_zid"\n'
            f"cat <<EOF\n"
            '{\n  "action": "upload",\n'
            f'  "contentSha1": "{sha1}",\n'
            '  "fileId": "4_zid",\n'
            '  "fileName": "$name",\n'
            f'  "fileRetention": {{"mode": "{reply["mode"]}", "retainUntilTimestamp": {until}}},\n'
            f'  "size": {size},\n'
            '  "uploadTimestamp": 1793934600000\n}\n'
            "EOF\n"
            f"exit {code}",
        )

    def curl(self, code: int, body: str) -> None:
        self._stub(
            self.bin / "curl", f'cat > {self.root}/curl.stdin\necho -n "{body}"\nexit {code}'
        )

    def called(self, tool: str) -> int:
        return self.calls.read_text().split().count(tool)

    def run(self, *args: str) -> subprocess.CompletedProcess:
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "CAMPUS_BACKUP_CONFIG_DIR": str(self.config),
            "CAMPUS_BACKUP_WORK_DIR": str(self.work),
            "CAMPUS_BACKUP_TOOLS_DIR": str(self.tools),
        }
        return subprocess.run(
            [BASH, str(SCRIPT), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
            check=False,
        )


@pytest.fixture
def box(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


def assert_no_secret(done: subprocess.CompletedProcess) -> None:
    output = done.stdout + done.stderr
    assert SECRET_KEY not in output
    assert "SECRETPINGMARKER" not in output


# --- A good run ---------------------------------------------------------------


@posix_only
def test_a_good_run_prints_the_proof_and_then_pings(box):
    done = box.run()

    assert done.returncode == 0, done.stderr
    assert f"encrypted: {OBJECT_SIZE} bytes" in done.stdout
    assert "sha256:" in done.stdout
    assert "object:    db/campus-" in done.stdout
    assert f"B2 size:   {OBJECT_SIZE} bytes" in done.stdout
    assert "retention: compliance until " in done.stdout
    assert "document_chunks 1161 abc" in done.stdout
    assert done.stdout.index("BACKUP OK") < done.stdout.index("PING OK")
    assert box.called("curl") == 1
    assert_no_secret(done)


@posix_only
def test_the_ping_url_reaches_curl_on_stdin_not_as_an_argument(box):
    box.run()
    assert PING_URL in (box.root / "curl.stdin").read_text()


@posix_only
def test_it_leaves_nothing_behind(box):
    assert box.run().returncode == 0
    assert list(box.work.iterdir()) == []


# --- Refusals -----------------------------------------------------------------


@posix_only
@pytest.mark.parametrize(
    ("break_it", "message"),
    [
        (lambda b: (b.config / "age-recipient.txt").unlink(), "age recipient file is missing"),
        (lambda b: (b.config / "age-recipient.txt").write_text("nonsense\n"), "age1 public key"),
        (lambda b: (b.config / "b2.env").unlink(), "B2 key file is missing"),
        (lambda b: (b.config / "b2.env").chmod(0o644), "must be mode 600"),
        (lambda b: b._secret("b2.env", "B2_APPLICATION_KEY_ID=KEYID\n"), "no B2_APPLICATION_KEY"),
        (lambda b: (b.tools / "age").unlink(), "age is not installed"),
        (lambda b: (b.tools / "b2").unlink(), "b2 is not installed"),
    ],
    ids=[
        "no_recipient",
        "bad_recipient",
        "no_key_file",
        "key_file_readable_by_others",
        "key_file_missing_a_value",
        "no_age",
        "no_b2",
    ],
)
@pytest.mark.parametrize("args", [(), ("--check",)], ids=["run", "check"])
def test_a_bad_setup_is_refused_before_any_dump(box, break_it, message, args):
    break_it(box)

    done = box.run(*args)

    assert done.returncode != 0
    assert message in done.stderr
    assert box.called("docker") == 0
    assert box.called("curl") == 0
    assert_no_secret(done)


@posix_only
def test_check_passes_on_a_good_setup_and_does_nothing(box):
    done = box.run("--check")
    assert done.returncode == 0
    assert "CHECK OK" in done.stdout
    assert box.called("docker") == box.called("b2") == box.called("curl") == 0


@posix_only
@pytest.mark.parametrize(
    "break_it",
    [
        lambda b: (b.config / "healthcheck-url").unlink(),
        lambda b: (b.config / "healthcheck-url").chmod(0o644),
        lambda b: b._secret("healthcheck-url", "http://example.com/x\n"),
    ],
    ids=["missing", "readable_by_others", "wrong_host"],
)
def test_a_bad_ping_url_fails_check_but_never_stops_a_backup(box, break_it):
    break_it(box)

    assert box.run("--check").returncode != 0

    done = box.run()
    assert done.returncode == 0
    assert "BACKUP OK" in done.stdout
    assert "PING SKIPPED" in done.stdout
    assert box.called("curl") == 0


# --- A failed backup means no BACKUP OK and no ping -----------------------------


@posix_only
@pytest.mark.parametrize(
    ("break_it", "message"),
    [
        (lambda b: b.docker(1), "dump or encryption failed"),
        (lambda b: b.age(1), "dump or encryption failed"),
        (lambda b: b.age(0, size=500), "minimum"),
        (lambda b: b.age(0, header=False), "not an age file"),
        (lambda b: b.b2(1, b2_reply()), "upload failed"),
        (lambda b: b.b2(0, b2_reply(mode="unknown", retain_ms=None)), "didn't confirm"),
        (lambda b: b.b2(0, b2_reply(mode="governance")), "didn't confirm"),
        (lambda b: b.b2(0, b2_reply(days=5)), "didn't confirm"),
        (lambda b: b.b2(0, b2_reply(size=123)), "didn't confirm"),
        (lambda b: b.b2(0, b2_reply(sha1="0" * 40)), "didn't confirm"),
    ],
    ids=[
        "pg_dump_failed",
        "age_failed",
        "dump_too_small",
        "not_an_age_file",
        "upload_failed",
        "key_cant_read_retention",
        "not_compliance_mode",
        "retention_too_short",
        "size_differs",
        "sha1_differs",
    ],
)
def test_a_failed_backup_never_pings(box, break_it, message):
    break_it(box)

    done = box.run()

    assert done.returncode != 0
    assert message in done.stderr
    assert "BACKUP OK" not in done.stdout
    assert box.called("curl") == 0
    assert_no_secret(done)


@posix_only
def test_a_failed_dump_is_never_uploaded(box):
    box.docker(1)
    box.run()
    assert box.called("b2") == 0


# --- A failed ping doesn't fail the backup ---------------------------------------


@posix_only
@pytest.mark.parametrize(
    ("code", "body"),
    [(6, ""), (22, ""), (0, "OK (not found)"), (0, "OK (rate limited)")],
    ids=["no_network", "http_error", "unknown_url", "rate_limited"],
)
def test_a_failed_ping_is_reported_and_doesnt_fail_the_backup(box, code, body):
    box.curl(code, body)

    done = box.run()

    assert done.returncode == 0
    assert "BACKUP OK" in done.stdout
    assert "PING FAILED" in done.stdout
    assert "PING OK" not in done.stdout
    assert_no_secret(done)


# --- The files themselves --------------------------------------------------------


def test_the_scripts_follow_the_rule_for_deploy_scripts():
    for name in ("campus-backup.sh", "install.sh", "restore-drill.sh"):
        source = (BACKUP_DIR / name).read_text(encoding="utf-8")
        assert "set -euo pipefail" in source, name
        assert "exec </dev/null" in source, name
        assert "set -x" not in source.replace("`set -x`", ""), name


def test_the_dump_excludes_question_log_rows():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "--exclude-table-data=question_log" in source
    assert "-Fc" in source


def test_the_timer_catches_up_and_the_service_closes_stdin():
    timer = (BACKUP_DIR / "campus-backup.timer").read_text(encoding="utf-8")
    assert "Persistent=true" in timer
    service = (BACKUP_DIR / "campus-backup.service").read_text(encoding="utf-8")
    assert "Type=oneshot" in service
    assert "StandardInput=null" in service
    assert "User=root" in service


def test_tools_are_pinned_by_exact_version_and_checksum():
    source = (BACKUP_DIR / "install.sh").read_text(encoding="utf-8")
    assert "B2_VERSION=v5.0.2" in source
    assert "B2_SHA256=8210f07b8d12363ef747847c4fcb04c60550909238177a1e5112abe4f204ca45" in source
    assert "AGE_VERSION=v1.3.2" in source
    assert "AGE_SHA256=cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10" in source
    assert "sha256sum -c" in source


def test_the_drill_uses_a_scratch_project_and_only_prints_its_cleanup():
    source = (BACKUP_DIR / "restore-drill.sh").read_text(encoding="utf-8")
    assert "PROJECT=a15drill" in source
    for line in source.splitlines():
        if "down -v" in line:
            assert line.strip().startswith("echo"), line


def test_the_backup_files_keep_lf_line_endings_on_their_way_to_the_vm():
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "deploy/backup/* text eol=lf" in attributes


# --- b2_check.py -------------------------------------------------------------------


def _b2_check():
    spec = importlib.util.spec_from_file_location("b2_check", BACKUP_DIR / "b2_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOOD_ALLOWED = {
    "capabilities": ["listBuckets", "writeFiles", "readFileRetentions", "readBucketRetentions"],
    "buckets": [{"id": "x", "name": "campus-assistant-backups-7"}],
    "namePrefix": None,
}


def test_a_key_with_exactly_the_needed_rights_passes():
    assert _b2_check().key_problems(GOOD_ALLOWED, None) == []


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"capabilities": ["listBuckets", "writeFiles"]}, "missing: readBucketRetentions"),
        (
            {"capabilities": [*GOOD_ALLOWED["capabilities"], "deleteFiles"]},
            "must not have: deleteFiles",
        ),
        ({"capabilities": [*GOOD_ALLOWED["capabilities"], "bypassGovernance"]}, "bypassGovernance"),
        (
            {"capabilities": [*GOOD_ALLOWED["capabilities"], "writeFileRetentions"]},
            "writeFileRetentions",
        ),
        ({"capabilities": [*GOOD_ALLOWED["capabilities"], "writeKeys"]}, "writeKeys"),
        ({"buckets": None}, "not restricted"),
        ({"buckets": [{"name": "another-bucket"}]}, "not restricted"),
        ({"namePrefix": "db/"}, "prefix"),
    ],
)
def test_a_key_outside_the_rule_is_reported(change, fragment):
    problems = _b2_check().key_problems({**GOOD_ALLOWED, **change}, None)
    assert any(fragment in problem for problem in problems)


def test_a_key_with_an_expiry_is_reported():
    assert any("expiry" in p for p in _b2_check().key_problems(GOOD_ALLOWED, 1793934600000))


def _lock(mode="compliance", duration=30, unit="days", enabled=True):
    return {
        "isClientAuthorizedToRead": True,
        "value": {
            "isFileLockEnabled": enabled,
            "defaultRetention": {"mode": mode, "period": {"duration": duration, "unit": unit}},
        },
    }


def test_compliance_for_30_days_passes():
    assert _b2_check().retention_problems(_lock()) == []


@pytest.mark.parametrize(
    "lock",
    [
        _lock(mode="governance"),
        _lock(duration=7),
        _lock(unit="years"),
        _lock(enabled=False),
        {"isClientAuthorizedToRead": False, "value": None},
    ],
    ids=["governance", "too_short", "wrong_unit", "lock_off", "cant_read"],
)
def test_any_other_retention_is_reported(lock):
    assert _b2_check().retention_problems(lock) != []


def test_the_check_prints_the_rights_but_never_the_secret(tmp_path, monkeypatch, capsys):
    module = _b2_check()
    key_file = tmp_path / "b2.env"
    key_file.write_text(f"B2_APPLICATION_KEY_ID=KEYID\nB2_APPLICATION_KEY={SECRET_KEY}\n")
    monkeypatch.setattr(module, "KEY_FILE", key_file)
    monkeypatch.setattr(module.read_key, "__defaults__", (key_file,))
    monkeypatch.setattr(
        module,
        "authorize",
        lambda key_id, key: {
            "accountId": "a",
            "authorizationToken": "SECRETTOKENMARKER",
            "applicationKeyExpirationTimestamp": None,
            "apiInfo": {"storageApi": {"apiUrl": "https://x", "allowed": GOOD_ALLOWED}},
        },
    )
    monkeypatch.setattr(
        module, "call", lambda *a: {"buckets": [{"fileLockConfiguration": _lock()}]}
    )

    assert module.main([]) == 0

    out = capsys.readouterr().out
    assert "KEY OK" in out
    assert "writeFiles" in out
    assert SECRET_KEY not in out
    assert "SECRETTOKENMARKER" not in out


def test_an_error_prints_only_its_type(monkeypatch, capsys):
    module = _b2_check()

    def failing():
        raise ValueError(f"something quoting {SECRET_KEY}")

    monkeypatch.setattr(module, "check", failing)
    assert module.main([]) == 1
    out = capsys.readouterr().out
    assert "ValueError" in out
    assert SECRET_KEY not in out


def test_delete_test_wont_run_with_a_key_that_can_delete(tmp_path, monkeypatch, capsys):
    module = _b2_check()
    key_file = tmp_path / "b2.env"
    key_file.write_text("B2_APPLICATION_KEY_ID=K\nB2_APPLICATION_KEY=S\n")
    monkeypatch.setattr(module.read_key, "__defaults__", (key_file,))
    allowed = {**GOOD_ALLOWED, "capabilities": ["deleteFiles"]}
    monkeypatch.setattr(
        module,
        "authorize",
        lambda *a: {
            "accountId": "a",
            "authorizationToken": "t",
            "apiInfo": {"storageApi": {"apiUrl": "https://x", "allowed": allowed}},
        },
    )
    monkeypatch.setattr(module, "call", lambda *a: pytest.fail("it must not try"))

    assert module.main(["delete-test", "id", "name"]) == 1
    assert "REFUSED TO TEST" in capsys.readouterr().out
