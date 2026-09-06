#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
ARCH=arm64
while [[ $# -gt 0 ]]; do
  case "$1" in
    --arch) ARCH="$2"; shift 2;;
    *) echo "unknown arg $1"; exit 2;;
  esac
done

CACHE="$ROOT/artifacts/cache"
mkdir -p "$CACHE" "$ROOT/artifacts/logs"

PLATFORM="linux/arm64"
[[ "$ARCH" == "amd64" ]] && PLATFORM="linux/amd64"

echo "[build] platform=$PLATFORM"

# Ensure spark extracted
if [[ ! -d "$CACHE/spark-3.5.5-bin-hadoop3" ]]; then
  tar -xzf "$CACHE/spark-3.5.5-bin-hadoop3.tgz" -C "$CACHE"
fi

# Baseline image (plain docker build — buildx plugin optional)
docker build --platform "$PLATFORM" \
  -t "superspark/spark-baseline:3.5.5" \
  -f "$ROOT/runtime/docker/Dockerfile.baseline" \
  --build-arg SPARK_DIR=spark-3.5.5-bin-hadoop3 \
  "$CACHE" 2>&1 | tee "$ROOT/artifacts/logs/docker-baseline.log"

# Native image (copies Gluten jar)
GLUTEN_JAR_FILE="gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar"
if [[ "$ARCH" == "amd64" ]]; then
  if [[ ! -f "$CACHE/apache-gluten-1.6.0-bin-spark-3.5.tar.gz" ]]; then
    curl -fsSL -o "$CACHE/apache-gluten-1.6.0-bin-spark-3.5.tar.gz" \
      https://downloads.apache.org/gluten/1.6.0/apache-gluten-1.6.0-bin-spark-3.5.tar.gz
  fi
  mkdir -p "$CACHE/gluten-amd64"
  tar -xzf "$CACHE/apache-gluten-1.6.0-bin-spark-3.5.tar.gz" -C "$CACHE/gluten-amd64"
  src=$(find "$CACHE/gluten-amd64" -name 'gluten-velox-bundle*.jar' | head -1)
  GLUTEN_JAR_FILE=$(basename "$src")
  cp "$src" "$CACHE/$GLUTEN_JAR_FILE"
fi

test -f "$CACHE/$GLUTEN_JAR_FILE" || { echo "missing $CACHE/$GLUTEN_JAR_FILE"; exit 1; }

docker build --platform "$PLATFORM" \
  -t "superspark/spark-native:3.5.5-gluten1.6.0" \
  -f "$ROOT/runtime/docker/Dockerfile.native" \
  --build-arg SPARK_DIR=spark-3.5.5-bin-hadoop3 \
  --build-arg GLUTEN_JAR_FILE="$GLUTEN_JAR_FILE" \
  "$CACHE" 2>&1 | tee "$ROOT/artifacts/logs/docker-native.log"

docker images 'superspark/*' --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}'
echo "[build] done"
