#!/usr/bin/env bash
# The restore drill, on the laptop: decrypt a downloaded backup, restore it into a
# scratch project, and compare it with production. Pass = identical, by the rule in
# deploy/DEPLOY.md ("A1.5"). It leaves the scratch project up. Removing it is a
# separate, explicit step, printed at the end.
#
#   deploy/backup/restore-drill.sh <downloaded .dump.age file>
#
# Run from Git Bash at the repo root. The private key is read only by age.
set -euo pipefail
exec </dev/null
export MSYS_NO_PATHCONV=1

FILE="${1:?usage: restore-drill.sh <downloaded .dump.age file>}"
AGE_KEY="${AGE_KEY_FILE:-C:/dev/backup-keys/campus-backup.age-key}"
AGE="${AGE_BIN:-C:/dev/backup-tools/age/age.exe}"
VM="${DRILL_VM:-azureuser@campus-assistant.denmarkeast.cloudapp.azure.com}"
SSH_KEY="${DRILL_SSH_KEY:-$HOME/.ssh/campus_azure}"
PROJECT=a15drill
COMPOSE=(docker compose -p "$PROJECT" -f deploy/backup/drill-compose.yml)
SQL=deploy/backup/fingerprint.sql

die() {
  echo "DRILL FAILED: $1" >&2
  exit 1
}

[ -f "$FILE" ] || die "no such file"
[ -f "$AGE_KEY" ] || die "the private key isn't at $AGE_KEY"
[ -f "$SQL" ] || die "run this from the repo root"
START=$(date +%s)

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "file:   $(wc -c <"$FILE") bytes, sha256 $(sha256sum "$FILE" | cut -d' ' -f1)"

"${COMPOSE[@]}" up -d db </dev/null >/dev/null 2>&1 || die "scratch database didn't start"
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T db psql -U drill -d drill -Atc 'select 1' </dev/null >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done
[ "${READY:-}" = "1" ] || die "scratch database never answered"
EXISTING="$("${COMPOSE[@]}" exec -T db psql -U drill -d drill -Atc "select count(*) from information_schema.tables where table_schema = 'public'" </dev/null | tr -d '\r')"
[ "$EXISTING" = "0" ] || die "the scratch database isn't empty: remove it first"

# Decrypted straight into pg_restore, so no plain dump lands on the laptop's disk.
# --no-privileges: dumps hold grants to campus_api, which doesn't exist here.
"$AGE" -d -i "$AGE_KEY" "$FILE" 2>"$WORK/age.err" \
  | "${COMPOSE[@]}" exec -T db pg_restore -U drill -d drill --no-owner --no-privileges 2>"$WORK/restore.err" \
  || die "decrypt or restore failed"

"${COMPOSE[@]}" exec -T db psql -U drill -d drill -At -F " " <"$SQL" 2>/dev/null | tr -d '\r' >"$WORK/restored.txt"
QUESTION_ROWS="$("${COMPOSE[@]}" exec -T db psql -U drill -d drill -Atc 'select count(*) from question_log' </dev/null | tr -d '\r')"

# shellcheck disable=SC2016  # $POSTGRES_* are the container's own variables
ssh -i "$SSH_KEY" -o BatchMode=yes "$VM" \
  "docker exec -i campus-db-1 sh -c 'psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -At -F \" \"'" \
  <"$SQL" | tr -d '\r' >"$WORK/production.txt"

[ -s "$WORK/restored.txt" ] || die "no fingerprint from the restored database"
[ -s "$WORK/production.txt" ] || die "no fingerprint from production"

echo "--- proof ---"
echo "production:"
sed 's/^/  /' "$WORK/production.txt"
echo "restored:"
sed 's/^/  /' "$WORK/restored.txt"
echo "question_log rows restored: $QUESTION_ROWS"
echo "took $(( $(date +%s) - START )) s"
echo "scratch project left up. To remove it:"
echo "  docker compose -p $PROJECT -f deploy/backup/drill-compose.yml down -v"

diff "$WORK/production.txt" "$WORK/restored.txt" >/dev/null || die "the content differs from production"
[ "$QUESTION_ROWS" = "0" ] || die "question_log isn't empty"
echo "DRILL PASSED"
