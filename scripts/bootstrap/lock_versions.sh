#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[lock-versions] versions already resolved in versions.lock.yaml"
echo "Evidence under artifacts/version-evidence/"
ls -la "$ROOT/artifacts/version-evidence/" || true
cat "$ROOT/versions.lock.yaml" | head -40
