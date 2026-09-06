#!/usr/bin/env bash
set -euo pipefail
CONFIG="${1:?CONFIG required}"
if grep -q REPLACE_ME "$CONFIG"; then
  echo "CONFIG still has REPLACE_ME fields" >&2
  exit 2
fi
echo "[validate-yarn] preflight OK for $CONFIG"
echo "Live smoke: NOT RUN (requires authorized YARN cluster)"
