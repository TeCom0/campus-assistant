"""deploy/update.sh, run for real with stubbed tools: the order is right, and a failure
anywhere before `up` means the new containers never start and there is no UPDATE OK.

Not on Windows by default, like the backup script's tests: CI runs them. To run them
from Git Bash anyway, set CAMPUS_BASH_TESTS=1.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "deploy" / "update.sh"
DRILL = REPO_ROOT / "deploy" / "backup" / "restore-drill.sh"
BACKUP_DIR = REPO_ROOT / "deploy" / "backup"

BASH = shutil.which("bash")
posix_only = pytest.mark.skipif(
    BASH is None or (sys.platform == "win32" and "CAMPUS_BASH_TESTS" not in os.environ),
    reason="needs bash",
)

# Every outcome is chosen by the test through the environment.
FAKE_DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$CALLS"
case "$*" in
  *"run --rm -T migrate"*)
    [ "${FAIL:-}" != "migrate" ] || exit 1
    touch "$MIGRATED"
    ;;
  *"run --rm -T registry-sync"*)
    [ "${FAIL:-}" != "sync" ] || exit 1
    ;;
  *"app.db.verify_role"*)
    [ "${FAIL:-}" != "verify_exit" ] || exit 1
    [ "${FAIL:-}" = "verify_silent" ] || echo "[verify_role] ok: 9 allowed, 23 denied"
    ;;
  *"group by status"*) echo "active 3" ;;
  *"count(*) from documents"*) echo "${DOCUMENTS:-3}" ;;
  *"count(*) from document_editions"*) echo "${EDITIONS:-3}" ;;
  *"count(*) from document_chunks"*)
    if [ -f "$MIGRATED" ] && [ -n "${CHUNKS_AFTER:-}" ]; then echo "$CHUNKS_AFTER"; else echo 1161; fi
    ;;
  *"count(*) from courses"*) echo 660 ;;
  *"count(*) from course_prerequisites"*) echo 526 ;;
  *"select id from document_editions"*) echo "an_edition" ;;
  *"exec -T api python -c"*"/health"*)
    [ "${FAIL:-}" != "health" ] || exit 1
    ;;
  *"exec -T api python -c"*"/sources/"*) echo "${LINK:-302}" ;;
esac
exit 0
"""

FAKE_SUDO = """#!/usr/bin/env bash
echo "sudo $*" >> "$CALLS"
[ "${FAIL:-}" != "sudo" ] || exit 1
exit 0
"""


class Sandbox:
    def __init__(self, root: Path):
        self.root = root
        self.calls = root / "calls"
        self.calls.write_text("")
        self.docker = self._stub("docker", FAKE_DOCKER)
        self.sudo = self._stub("sudo", FAKE_SUDO)
        # The script checks these two exist, relative to where it runs.
        (root / "data").mkdir()
        (root / "data" / "registry.toml").write_text("")
        (root / "deploy" / "backup").mkdir(parents=True)
        (root / "deploy" / "backup" / "fingerprint.sql").write_text("select 1;\n")

    def _stub(self, name: str, body: str) -> Path:
        path = self.root / name
        path.write_text(body, newline="\n")
        path.chmod(0o755)
        return path

    def run(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [BASH, str(SCRIPT), *args],
            cwd=self.root,
            env={
                **os.environ,
                "DOCKER_BIN": self.docker.as_posix(),
                "SUDO_BIN": self.sudo.as_posix(),
                "FINGERPRINT_DEST": "/installed/fingerprint.sql",
                "CALLS": self.calls.as_posix(),
                "MIGRATED": (self.root / "migrated").as_posix(),
                "HEALTH_TRIES": "2",
                "HEALTH_WAIT_SECONDS": "0",
                **env,
            },
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def called(self) -> str:
        return self.calls.read_text()


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(tmp_path)


def _started_the_new_containers(sandbox: Sandbox) -> bool:
    return any(
        line.endswith("up -d") for line in sandbox.called().splitlines() if "up -d db" not in line
    )


@posix_only
def test_a_good_run_goes_in_order_and_prints_its_proof(sandbox):
    done = sandbox.run()
    assert done.returncode == 0, done.stderr
    calls = sandbox.called()
    order = [
        calls.index("build"),
        calls.index("run --rm -T migrate"),
        calls.index("run --rm -T registry-sync"),
        calls.index("app.db.verify_role"),
        calls.index("sudo -n install"),
        calls.index("docker-compose.prod.yml up -d\n"),
        calls.index("/health"),
        calls.index("/sources/"),
    ]
    assert order == sorted(order)
    assert done.stdout.rstrip().endswith("UPDATE OK")
    for line in (
        "documents:         3",
        "document_editions: 3",
        "active 3",
        "document_chunks 1161, courses 660, course_prerequisites 526",
        "an_edition answered 302",
    ):
        assert line in done.stdout


@posix_only
def test_plain_runs_plain_sync_and_initial_runs_initial(sandbox, tmp_path):
    sandbox.run()
    assert "registry-sync python -m app.registry sync\n" in sandbox.called()
    sandbox.calls.write_text("")
    sandbox.run("--initial")
    assert "registry-sync python -m app.registry sync --initial\n" in sandbox.called()


@posix_only
@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"DOCUMENTS": "0"}, "documents has 0 rows"),
        ({"EDITIONS": "0"}, "document_editions has 0 rows"),
        ({"DOCUMENTS": "nonsense"}, "not a count"),
        ({"FAIL": "migrate"}, "migrate failed"),
        ({"FAIL": "sync"}, "registry sync failed"),
        ({"FAIL": "verify_exit"}, "verify_role failed"),
        ({"FAIL": "verify_silent"}, "no ok line"),
        ({"FAIL": "sudo"}, "fingerprint"),
    ],
    ids=lambda value: str(value),
)
def test_a_failure_before_up_stops_with_the_old_api_still_serving(sandbox, env, message):
    done = sandbox.run(**env)
    assert done.returncode != 0
    assert message in done.stderr
    assert "UPDATE OK" not in done.stdout
    assert not _started_the_new_containers(sandbox)


@posix_only
def test_the_counts_are_printed_before_the_zero_row_gate_stops_it(sandbox):
    done = sandbox.run(DOCUMENTS="0", EDITIONS="0")
    assert "registry: documents 0, document_editions 0" in done.stdout


@posix_only
@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"FAIL": "health"}, "never answered"),
        ({"LINK": "404"}, "answered 404"),
        ({"CHUNKS_AFTER": "1000"}, "content counts changed"),
    ],
    ids=["health", "source link", "content changed"],
)
def test_a_failure_after_up_is_not_reported_as_success(sandbox, env, message):
    done = sandbox.run(**env)
    assert done.returncode != 0
    assert message in done.stderr
    assert "UPDATE OK" not in done.stdout


@posix_only
def test_an_unknown_argument_and_the_wrong_folder_stop_it(sandbox):
    done = sandbox.run("--typo")
    assert done.returncode != 0
    assert "unknown argument" in done.stderr
    assert sandbox.called() == ""

    (sandbox.root / "data" / "registry.toml").unlink()
    done = sandbox.run()
    assert done.returncode != 0
    assert "repo copy" in done.stderr
    assert sandbox.called() == ""


def test_the_script_follows_the_rules_for_deploy_scripts():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in source
    assert "exec </dev/null" in source
    for line in source.splitlines():
        if '"${COMPOSE[@]}"' in line and (" run " in line or " exec " in line):
            assert "</dev/null" in line, line
    assert "UPDATE OK" in source


def test_the_shell_scripts_keep_unix_line_endings_in_a_copy_made_on_windows():
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "deploy/*.sh text eol=lf" in attributes
    assert "deploy/backup/* text eol=lf" in attributes


# --- The fingerprint and the restore drill ----------------------------------------


def test_the_fingerprint_covers_the_registry_tables():
    source = (BACKUP_DIR / "fingerprint.sql").read_text(encoding="utf-8")
    for table in (
        "course_prerequisites",
        "courses",
        "document_chunks",
        "document_editions",
        "documents",
    ):
        assert f"FROM {table} t" in source


def test_the_old_fingerprint_stays_on_the_three_old_tables():
    source = (BACKUP_DIR / "fingerprint-pre-a2.1.sql").read_text(encoding="utf-8")
    assert "FROM document_chunks t" in source
    assert "FROM documents t" not in source
    assert "FROM document_editions t" not in source


def test_the_drill_requires_the_registry_tables_unless_told_otherwise():
    source = DRILL.read_text(encoding="utf-8")
    assert "--pre-a2-1) SQL=deploy/backup/fingerprint-pre-a2.1.sql ;;" in source
    assert '[ "$REGISTRY_TABLES" = "2" ] || die' in source
    assert '[ "$REGISTRY_TABLES" = "0" ] || die' in source
    assert "skipped, not in a dump from before A2.1: documents, document_editions" in source


def test_a_drill_with_the_old_fingerprint_runs_on_both_sides():
    # $SQL goes to the restored database and to production, so a pre-A2.1 run can't
    # compare three tables with five.
    source = DRILL.read_text(encoding="utf-8")
    assert source.count('<"$SQL"') == 2
