#!/usr/bin/env bash
# Update the running stack on the VM. Run from the repo copy, as a file: never piped
# through `ssh ... bash -s`, where a `docker compose run` once swallowed the rest of the
# script and it still exited 0.
#
#   bash deploy/update.sh             # every deploy
#   bash deploy/update.sh --initial   # once, when the registry tables are empty
#
# Everything up to `up` happens with the old API still serving, so a failure before it
# leaves the site as it was. A deploy doesn't change content, so the content tables'
# counts must match before and after.
set -euo pipefail
exec </dev/null

DOCKER="${DOCKER_BIN:-docker}"
SUDO="${SUDO_BIN:-sudo}"
FINGERPRINT_DEST="${FINGERPRINT_DEST:-/usr/local/lib/campus-backup/fingerprint.sql}"
COMPOSE=("$DOCKER" compose -f docker-compose.yml -f docker-compose.prod.yml)
HEALTH_TRIES="${HEALTH_TRIES:-60}"
HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-2}"

die() {
  echo "UPDATE FAILED: $1" >&2
  exit 1
}

case "${1:-}" in
  "") SYNC=(python -m app.registry sync) ;;
  --initial) SYNC=(python -m app.registry sync --initial) ;;
  *) die "unknown argument" ;;
esac

[ -f data/registry.toml ] || die "run this from the repo copy: no data/registry.toml here"
[ -f deploy/backup/fingerprint.sql ] || die "no deploy/backup/fingerprint.sql here"

query() {
  # shellcheck disable=SC2016  # $POSTGRES_* are the container's own variables
  "${COMPOSE[@]}" exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$0"' "$1" </dev/null | tr -d '\r'
}

count() {
  local rows
  rows="$(query "select count(*) from $1")" || die "couldn't count $1"
  [[ "$rows" =~ ^[0-9]+$ ]] || die "not a count for $1"
  echo "$rows"
}

content_counts() {
  echo "document_chunks $(count document_chunks), courses $(count courses), course_prerequisites $(count course_prerequisites)"
}

"${COMPOSE[@]}" up -d db </dev/null || die "the database didn't start"
BEFORE="$(content_counts)"
echo "content before: $BEFORE"

"${COMPOSE[@]}" build </dev/null || die "build failed"
"${COMPOSE[@]}" run --rm -T migrate </dev/null || die "migrate failed"
"${COMPOSE[@]}" run --rm -T registry-sync "${SYNC[@]}" </dev/null || die "registry sync failed"

# Fail closed: the API can't name a source from empty tables.
DOCUMENTS="$(count documents)"
EDITIONS="$(count document_editions)"
echo "registry: documents $DOCUMENTS, document_editions $EDITIONS"
[ "$DOCUMENTS" -gt 0 ] || die "documents has 0 rows"
[ "$EDITIONS" -gt 0 ] || die "document_editions has 0 rows"

GATE="$("${COMPOSE[@]}" run --rm --no-deps -T api python -m app.db.verify_role </dev/null)" \
  || { echo "$GATE"; die "verify_role failed"; }
echo "$GATE"
# The line, not only the exit code: a clean exit alone has proved nothing here before.
grep -q '^\[verify_role\] ok:' <<<"$GATE" || die "verify_role printed no ok line"

# After migrate, because the backup would fail on tables that don't exist yet. The
# restore drill sends its own copy; this one is for the nightly backup's proof.
"$SUDO" -n install -m 644 -o root -g root deploy/backup/fingerprint.sql "$FINGERPRINT_DEST" </dev/null \
  || die "couldn't install the fingerprint"

"${COMPOSE[@]}" up -d </dev/null || die "up failed"

for try in $(seq 1 "$HEALTH_TRIES"); do
  if "${COMPOSE[@]}" exec -T api python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=5)" </dev/null >/dev/null 2>&1; then
    HEALTHY=1
    break
  fi
  [ "$try" = "$HEALTH_TRIES" ] || sleep "$HEALTH_WAIT_SECONDS"
done
[ "${HEALTHY:-}" = "1" ] || die "the API never answered /health"

# A source link, through the API's own read of the synced tables.
EDITION="$(query "select id from document_editions where status = 'active' order by id limit 1")"
[ -n "$EDITION" ] || die "no active edition"
LINK="$("${COMPOSE[@]}" exec -T api python -c "import http.client as h; c = h.HTTPConnection('127.0.0.1', 8000, timeout=20); c.request('GET', '/sources/$EDITION'); print(c.getresponse().status)" </dev/null | tr -d '\r')"
[ "$LINK" = "302" ] || die "a source link answered $LINK, not 302"

AFTER="$(content_counts)"
[ "$AFTER" = "$BEFORE" ] || die "the content counts changed: before $BEFORE, after $AFTER"

echo "--- proof ---"
echo "documents:         $(count documents)"
echo "document_editions: $(count document_editions)"
echo "edition status:    $(query "select status || ' ' || count(*) from document_editions group by status order by status" | tr '\n' ',')"
echo "content after:     $AFTER"
echo "source link:       $EDITION answered $LINK"
echo "fingerprint:       $(sha256sum deploy/backup/fingerprint.sql | cut -c1-12), installed at $FINGERPRINT_DEST"
echo "UPDATE OK"
