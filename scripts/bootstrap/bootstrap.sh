#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export JAVA_HOME="${JAVA_HOME:-${HOME}/.local/opt/jdk-17}"
LOG_DIR="$ROOT/artifacts/logs"
STATE="$ROOT/artifacts/setup-state.json"
mkdir -p "$LOG_DIR" "$ROOT/artifacts/cache" "$ROOT/artifacts/data" "$ROOT/artifacts/reports"

echo "[bootstrap] running doctor first..."
"$ROOT/scripts/bootstrap/doctor.sh" || true

echo "[bootstrap] ensuring Colima (Docker) runtime..."
if ! docker info >/dev/null 2>&1; then
  # 12GiB / 4 CPU for ~24GiB host
  colima start --arch aarch64 --cpu 4 --memory 12 --disk 60 --runtime docker --network-address 2>&1 | tee "$LOG_DIR/colima-start.log" \
    || colima start 2>&1 | tee -a "$LOG_DIR/colima-start.log"
fi
docker info >/dev/null

echo "[bootstrap] building runtime images..."
"$ROOT/scripts/bootstrap/build_images.sh" --arch arm64

echo "[bootstrap] bringing up project k3d cluster..."
"$ROOT/scripts/bootstrap/local_up.sh"

echo "[bootstrap] generating tiny fixtures if needed..."
python3 "$ROOT/examples/fixtures/generate_tiny.py"

echo "[bootstrap] smoke baseline..."
"$ROOT/runner/bin/superspark" smoke --mode baseline
echo "[bootstrap] smoke native..."
"$ROOT/runner/bin/superspark" smoke --mode native

python3 - <<'PY'
import json, os, platform, datetime
root = os.environ.get("SUPERSPARK_ROOT", "/Users/neo/Software/SuperSpark")
state = {
  "project": "superspark",
  "updated": datetime.datetime.utcnow().isoformat() + "Z",
  "host_arch": platform.machine(),
  "java_home": os.environ.get("JAVA_HOME"),
  "cluster": "k3d-superspark",
  "namespace": "superspark",
  "runtime": "colima",
  "images": ["superspark/spark-baseline:3.5.5", "superspark/spark-native:3.5.5-gluten1.6.0"],
  "readiness": {"docker": True, "smoke_baseline": True, "smoke_native": True},
}
path = os.path.join(root, "artifacts", "setup-state.json")
with open(path, "w") as f:
    json.dump(state, f, indent=2)
print("wrote", path)
PY

echo "[bootstrap] complete"
