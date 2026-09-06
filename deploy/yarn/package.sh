#!/usr/bin/env bash
set -euo pipefail
CONFIG="${1:?CONFIG required}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/artifacts/packages/yarn"
mkdir -p "$OUT"
cp "$ROOT/versions.lock.yaml" "$OUT/"
cp "$ROOT/artifacts/cache/gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar" "$OUT/" 2>/dev/null || true
cp "$ROOT/deploy/yarn/submit-baseline.sh" "$ROOT/deploy/yarn/submit-native.sh" "$OUT/"
tar -czf "$OUT/../superspark-yarn-package.tar.gz" -C "$OUT" .
echo "Wrote $OUT/../superspark-yarn-package.tar.gz"
echo "Pilot on live YARN: NOT RUN without cluster access"
