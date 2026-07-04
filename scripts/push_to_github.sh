#!/usr/bin/env bash
# Push dickey-sovereign-core to GitHub (requires SSH or HTTPS auth)
set -euo pipefail
cd "$(dirname "$0")/.."
REMOTE="${REMOTE:-git@github.com:keithdickey207/dickey-sovereign-core.git}"
if ! git remote get-url origin &>/dev/null; then
  git remote add origin "$REMOTE"
fi
git push -u origin main
echo "[+] Pushed to $REMOTE"