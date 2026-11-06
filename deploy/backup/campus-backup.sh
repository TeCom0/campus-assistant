#!/usr/bin/env bash
# Daily off-VM backup: dump the content tables, encrypt, push to Backblaze B2, and
# print proof. The runbook is in deploy/DEPLOY.md ("A1.5").
#
#   campus-backup          run a backup
#   campus-backup --check  check the configuration, and stop there
#
# Secrets stay out of the log: tool output is kept in files that are parsed and never
# printed, errors say only what failed and its exit code, and `set -x` is never used.
# The key reaches `b2` as an environment variable, which it keeps in memory.
set -euo pipefail
exec </dev/null
umask 077

CONFIG_DIR="${CAMPUS_BACKUP_CONFIG_DIR:-/etc/campus-backup}"
WORK_ROOT="${CAMPUS_BACKUP_WORK_DIR:-/var/lib/campus-backup}"
TOOLS_DIR="${CAMPUS_BACKUP_TOOLS_DIR:-/usr/local/lib/campus-backup}"
DB_CONTAINER="${CAMPUS_BACKUP_DB_CONTAINER:-campus-db-1}"
BUCKET=campus-assistant-backups-7
MIN_BYTES="${CAMPUS_BACKUP_MIN_BYTES:-1000000}"
MIN_RETENTION_DAYS=29

RECIPIENT_FILE="$CONFIG_DIR/age-recipient.txt"
KEY_FILE="$CONFIG_DIR/b2.env"
PING_FILE="$CONFIG_DIR/healthcheck-url"
FINGERPRINT_SQL="$TOOLS_DIR/fingerprint.sql"
AGE="$TOOLS_DIR/age"
B2="$TOOLS_DIR/b2"

die() {
  echo "BACKUP FAILED: $1" >&2
  exit 1
}

value_of() {
  sed -n "s/^$1=//p" "$KEY_FILE" | head -n 1 | tr -d '\r'
}

# Root-only here means owned by whoever runs this, with mode 600. The service runs
# as root, so on the VM that is root.
is_private() {
  [ "$(stat -c '%a %U' "$1")" = "600 $(id -un)" ]
}

check_config() {
  [ -f "$RECIPIENT_FILE" ] || die "age recipient file is missing"
  grep -Eq '^age1[0-9a-z]{58}$' "$RECIPIENT_FILE" || die "age recipient is not a single age1 public key"
  [ -f "$KEY_FILE" ] || die "B2 key file is missing"
  is_private "$KEY_FILE" || die "B2 key file must be mode 600 and owned by this user"
  [ -n "$(value_of B2_APPLICATION_KEY_ID)" ] || die "B2 key file has no B2_APPLICATION_KEY_ID"
  [ -n "$(value_of B2_APPLICATION_KEY)" ] || die "B2 key file has no B2_APPLICATION_KEY"
  [ -x "$AGE" ] || die "age is not installed"
  [ -x "$B2" ] || die "b2 is not installed"
  [ -f "$FINGERPRINT_SQL" ] || die "fingerprint.sql is not installed"
}

# The ping is optional at run time: a missing or bad URL must never stop a backup.
ping_url_problem() {
  [ -f "$PING_FILE" ] || { echo "ping URL file is missing"; return 0; }
  is_private "$PING_FILE" || { echo "ping URL file must be mode 600 and owned by this user"; return 0; }
  grep -Eq '^https://hc-ping\.com/[A-Za-z0-9/_-]+$' "$PING_FILE" || { echo "ping URL is not a single hc-ping.com URL"; return 0; }
  return 1
}

# Tells Healthchecks.io, with $1 appended to the URL. True only if it answered exactly
# "OK": an unknown URL also answers 200, with "OK (not found)". The URL goes through a
# config on stdin, to stay out of the process list, and curl's own errors are dropped
# because they can quote it.
ping_check() {
  local body
  body="$(curl -fs -m 10 --retry 5 -K - 2>/dev/null <<<"url = \"$(cat "$PING_FILE")$1\"")" && [ "$body" = "OK" ]
}

# Runs however the script ends, so a failure nobody wrote a `die` for is covered too.
# The /fail ping makes the alert immediate instead of 26 hours later. It's best effort:
# the exit code is saved first and restored last, so it can't mask the real result.
WORK=""
FAILURE_ALERTS=0
on_exit() {
  local code=$?
  trap - EXIT
  set +e
  [ -n "$WORK" ] && rm -rf "$WORK"
  if [ "$code" -ne 0 ] && [ "$FAILURE_ALERTS" = "1" ]; then
    if problem="$(ping_url_problem)"; then
      echo "FAIL PING SKIPPED: $problem"
    elif ping_check /fail; then
      echo "FAIL PING OK"
    else
      echo "FAIL PING FAILED: the check wasn't told, so it alerts only when the backup is overdue"
    fi
  fi
  exit "$code"
}
trap on_exit EXIT
# Without these, being stopped would skip the EXIT trap above.
trap 'exit 143' TERM
trap 'exit 130' INT
trap 'exit 129' HUP

if [ "${1:-}" = "--check" ]; then
  check_config
  if problem="$(ping_url_problem)"; then
    die "$problem"
  fi
  echo "CHECK OK: recipient, B2 key file, ping URL and tools are in place"
  exit 0
fi
[ "$#" -eq 0 ] || die "unknown argument"

# A real run from here on, so a failure alerts. Checking the setup or a mistyped
# argument isn't a failed backup.
FAILURE_ALERTS=1
check_config

mkdir -p "$WORK_ROOT"
WORK="$(mktemp -d "$WORK_ROOT/run.XXXXXX")"
export HOME="$WORK"

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
ENCRYPTED="$WORK/backup.dump.age"
UPLOAD_OUT="$WORK/upload.out"

# Straight from pg_dump into age, so no unencrypted dump ever touches this disk.
# pipefail makes a failed pg_dump fail this line, even though age would succeed.
# shellcheck disable=SC2016  # $POSTGRES_* are the container's own variables
docker exec "$DB_CONTAINER" sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --exclude-table-data=question_log' \
  </dev/null 2>"$WORK/dump.err" \
  | "$AGE" -R "$RECIPIENT_FILE" -o "$ENCRYPTED" 2>"$WORK/age.err" \
  || die "dump or encryption failed"

SIZE="$(stat -c %s "$ENCRYPTED")"
[ "$SIZE" -ge "$MIN_BYTES" ] || die "the encrypted dump is only $SIZE bytes, under the $MIN_BYTES minimum"
[ "$(head -c 21 "$ENCRYPTED")" = "age-encryption.org/v1" ] || die "the output is not an age file"
SHA256="$(sha256sum "$ENCRYPTED" | cut -d' ' -f1)"
SHA1="$(sha1sum "$ENCRYPTED" | cut -d' ' -f1)"

# Unique by time and content. This key can't list files, so nothing could notice a
# name already taken, and an overwrite would only add a version anyway.
OBJECT="db/campus-$STAMP-${SHA256:0:12}.dump.age"

KEY_ID="$(value_of B2_APPLICATION_KEY_ID)"
KEY="$(value_of B2_APPLICATION_KEY)"
if ! B2_APPLICATION_KEY_ID="$KEY_ID" B2_APPLICATION_KEY="$KEY" \
  "$B2" file upload --no-progress "$BUCKET" "$ENCRYPTED" "$OBJECT" >"$UPLOAD_OUT" 2>"$WORK/upload.err"; then
  die "upload failed"
fi
unset KEY KEY_ID

# What B2 reports, not what was sent. It prints two URL lines, then JSON. A failure
# here means the upload's result can't be trusted, so no BACKUP OK and no ping.
python3 -I - "$UPLOAD_OUT" "$OBJECT" "$SIZE" "$SHA1" "$MIN_RETENTION_DAYS" <<'PY' >"$WORK/proof" || die "B2's reply didn't confirm the upload"
import json
import sys
from datetime import UTC, datetime, timedelta

path, expected_name, expected_size, expected_sha1, min_days = sys.argv[1:6]
try:
    text = open(path, encoding="utf-8").read()
    reply = json.loads(text[text.index("{"):])
    name, size, sha1 = reply["fileName"], reply["size"], reply["contentSha1"]
    file_id = reply["fileId"]
    retention = reply["fileRetention"]
    mode, until_ms = retention["mode"], retention["retainUntilTimestamp"]
except Exception as e:  # only its type: the reply isn't for the log
    print(f"unreadable reply: {type(e).__name__}", file=sys.stderr)
    sys.exit(1)

problems = []
if name != expected_name:
    problems.append("name differs")
if size != int(expected_size):
    problems.append("size differs")
if sha1 != expected_sha1:
    problems.append("SHA-1 differs")
if mode != "compliance":
    problems.append(f"retention mode is {mode}")
if until_ms is None:
    problems.append("no retention date")
else:
    until = datetime.fromtimestamp(until_ms / 1000, UTC)
    if until < datetime.now(UTC) + timedelta(days=int(min_days)):
        problems.append(f"retention ends too soon, {until:%Y-%m-%d}")
if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)

print(f"object:    {name}")
print(f"file id:   {file_id}")
print(f"B2 size:   {size} bytes")
print(f"retention: {mode} until {until:%Y-%m-%dT%H:%M:%SZ}")
PY

echo "--- proof ---"
echo "encrypted: $SIZE bytes"
echo "sha256:    $SHA256"
cat "$WORK/proof"
echo "content at dump time (table, rows, md5):"
docker exec -i "$DB_CONTAINER" sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F " "' \
  <"$FINGERPRINT_SQL" 2>/dev/null | sed 's/^/  /' || die "content fingerprint failed"
echo "BACKUP OK"
FAILURE_ALERTS=0

# The dead man's switch: Healthchecks.io alerts if these stop. A failed ping is
# reported, but the backup above is already safe, so it doesn't fail the run.
if problem="$(ping_url_problem)"; then
  echo "PING SKIPPED: $problem"
elif ping_check ""; then
  echo "PING OK"
else
  echo "PING FAILED: the backup is fine, but the check wasn't told"
fi
exit 0
