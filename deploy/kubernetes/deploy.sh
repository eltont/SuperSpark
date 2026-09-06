#!/usr/bin/env bash
set -euo pipefail
CONFIG="${1:?CONFIG required}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
"$ROOT/deploy/kubernetes/validate.sh" "$CONFIG"
# Require explicit confirmation env to avoid accidental remote apply
if [[ "${SUPERSPARK_ALLOW_REMOTE_DEPLOY:-}" != "1" ]]; then
  echo "Set SUPERSPARK_ALLOW_REMOTE_DEPLOY=1 to apply remote manifests" >&2
  exit 2
fi
echo "[deploy-k8s] applying is environment-specific; provide rendered manifests under deploy/kubernetes/overlays/"
echo "NOT RUN: no target cluster credentials validated in this environment"
exit 0
