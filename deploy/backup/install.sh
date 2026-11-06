#!/usr/bin/env bash
# Installs the backup's tools, script and timer on the VM. Run with sudo from the
# repo copy's deploy/backup folder. Tools are pinned by exact version and sha256, and
# a mismatch stops here. It doesn't create or read any secret (deploy/DEPLOY.md).
set -euo pipefail
exec </dev/null

B2_VERSION=v5.0.2
B2_SHA256=8210f07b8d12363ef747847c4fcb04c60550909238177a1e5112abe4f204ca45
AGE_VERSION=v1.3.2
AGE_SHA256=cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10
TOOLS=/usr/local/lib/campus-backup

[ "$(id -u)" = "0" ] || { echo "INSTALL FAILED: run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
DOWNLOAD="$(mktemp -d)"
trap 'rm -rf "$DOWNLOAD"' EXIT

install -d -m 755 -o root -g root "$TOOLS"
install -d -m 700 -o root -g root /var/lib/campus-backup

curl -fsSL -m 300 -o "$DOWNLOAD/b2" \
  "https://github.com/Backblaze/B2_Command_Line_Tool/releases/download/$B2_VERSION/b2-linux"
echo "$B2_SHA256  $DOWNLOAD/b2" | sha256sum -c --quiet
install -m 755 -o root -g root "$DOWNLOAD/b2" "$TOOLS/b2"

AGE_TAR="age-$AGE_VERSION-linux-amd64.tar.gz"
curl -fsSL -m 300 -o "$DOWNLOAD/$AGE_TAR" \
  "https://github.com/FiloSottile/age/releases/download/$AGE_VERSION/$AGE_TAR"
echo "$AGE_SHA256  $DOWNLOAD/$AGE_TAR" | sha256sum -c --quiet
tar -xzf "$DOWNLOAD/$AGE_TAR" -C "$DOWNLOAD"
install -m 755 -o root -g root "$DOWNLOAD/age/age" "$TOOLS/age"

install -m 755 -o root -g root "$HERE/campus-backup.sh" /usr/local/sbin/campus-backup
install -m 755 -o root -g root "$HERE/b2_check.py" "$TOOLS/b2_check.py"
install -m 644 -o root -g root "$HERE/fingerprint.sql" "$TOOLS/fingerprint.sql"
install -m 644 -o root -g root "$HERE/campus-backup.service" /etc/systemd/system/campus-backup.service
install -m 644 -o root -g root "$HERE/campus-backup.timer" /etc/systemd/system/campus-backup.timer
systemctl daemon-reload

echo "--- proof ---"
echo "b2:    $(HOME="$DOWNLOAD" "$TOOLS/b2" version 2>/dev/null | head -n 1), sha256 $(sha256sum "$TOOLS/b2" | cut -c1-12)"
echo "age:   $("$TOOLS/age" --version)"
echo "script sha256: $(sha256sum /usr/local/sbin/campus-backup | cut -c1-12)"
echo "timer: installed, not enabled. Enable it after the first good backup:"
echo "       sudo systemctl enable --now campus-backup.timer"
echo "INSTALL OK"
