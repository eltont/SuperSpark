#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ARCH=arm64
while [[ $# -gt 0 ]]; do
  case "$1" in
    --arch) ARCH="$2"; shift 2;;
    *) shift;;
  esac
done
OUT="$ROOT/artifacts/packages/superspark-runtime-${ARCH}"
mkdir -p "$OUT"
cp "$ROOT/versions.lock.yaml" "$OUT/"
cp "$ROOT/artifacts/cache/gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar" "$OUT/" 2>/dev/null || true
cp -R "$ROOT/configs" "$OUT/"
cp -R "$ROOT/deploy" "$OUT/"
tar -czf "${OUT}.tar.gz" -C "$(dirname "$OUT")" "$(basename "$OUT")"
echo "Wrote ${OUT}.tar.gz"
