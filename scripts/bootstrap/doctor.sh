#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export JAVA_HOME="${JAVA_HOME:-${HOME}/.local/opt/jdk-17}"

pass=0; warn=0; fail=0
check() {
  local status="$1"; shift
  case "$status" in
    PASS) echo "[PASS] $*"; pass=$((pass+1));;
    WARN) echo "[WARN] $*"; warn=$((warn+1));;
    FAIL) echo "[FAIL] $*"; fail=$((fail+1));;
  esac
}

echo "=== SuperSpark doctor (read-only) ==="
echo "host_arch=$(uname -m)"
echo "os=$(sw_vers -productName 2>/dev/null || uname -s) $(sw_vers -productVersion 2>/dev/null || true)"
mem_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
echo "memory_gib=$((mem_bytes/1024/1024/1024))"
df -h / | tail -1

[[ "$(uname -m)" == "arm64" ]] && check PASS "architecture arm64" || check WARN "architecture $(uname -m)"

if [[ -x "${JAVA_HOME}/bin/java" ]]; then
  check PASS "JAVA_HOME=$JAVA_HOME ($("${JAVA_HOME}/bin/java" -version 2>&1 | head -1))"
else
  check FAIL "JAVA_HOME missing at $JAVA_HOME"
fi

for t in docker kubectl k3d colima limactl; do
  if command -v "$t" >/dev/null 2>&1; then
    check PASS "$t -> $(command -v "$t")"
  else
    check FAIL "$t not on PATH"
  fi
done

if docker info >/dev/null 2>&1; then
  check PASS "docker daemon reachable ($(docker info --format '{{.Architecture}}' 2>/dev/null || echo unknown))"
else
  check WARN "docker daemon not reachable (start Colima via make bootstrap / local-up)"
fi

[[ -f "$ROOT/versions.lock.yaml" ]] && check PASS "versions.lock.yaml present" || check FAIL "versions.lock.yaml missing"
[[ -f "$ROOT/artifacts/cache/spark-3.5.5-bin-hadoop3.tgz" ]] && check PASS "spark distribution cached" || check WARN "spark tarball not cached"
[[ -f "$ROOT/artifacts/cache/gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar" ]] \
  && check PASS "gluten aarch64 interim jar cached" || check WARN "gluten aarch64 jar not cached"

if [[ -x /opt/homebrew/bin/brew ]]; then
  check WARN "system brew present but may be unusable by this user (permissions)"
fi
if [[ -x "${HOME}/.homebrew/bin/brew" ]]; then
  check PASS "user-local brew available"
fi

echo "=== summary pass=$pass warn=$warn fail=$fail ==="
[[ "$fail" -eq 0 ]]
