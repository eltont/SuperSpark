#!/usr/bin/env bash
set -euo pipefail
CONFIG="${1:?CONFIG required}"
if [[ ! -f "$CONFIG" ]]; then
  echo "missing $CONFIG" >&2
  exit 2
fi
if grep -qE 'REPLACE_ME|REPLACE_REGISTRY' "$CONFIG"; then
  echo "Refusing: $CONFIG still contains REPLACE_ME / REPLACE_REGISTRY" >&2
  exit 2
fi
echo "[validate-k8s] OK preflight for $CONFIG"
echo "Live deploy requires: SUPERSPARK_ALLOW_REMOTE_DEPLOY=1 make deploy-k8s CONFIG=..."
