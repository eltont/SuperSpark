#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export KUBECONFIG="${ROOT}/artifacts/kubeconfig-superspark.yaml"
CLUSTER=superspark

echo "[local-down] deleting project cluster only; preserving artifacts/reports"
if k3d cluster list 2>/dev/null | grep -q "^${CLUSTER}"; then
  k3d cluster delete "$CLUSTER"
fi
echo "[local-down] done (data/reports retained)"
