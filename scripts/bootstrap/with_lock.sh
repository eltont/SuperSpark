#!/usr/bin/env bash
# Acquire exclusive resource lock for heavy jobs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOCK="$ROOT/artifacts/resource.lock"
PURPOSE="${1:?purpose required}"
mkdir -p "$ROOT/artifacts"
if [[ -f "$LOCK" ]]; then
  old_pid=$(awk -F= '/^pid=/{print $2}' "$LOCK" || true)
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Resource lock held by pid=$old_pid ($(cat "$LOCK"))" >&2
    exit 75
  fi
fi
cat >"$LOCK" <<EOF
pid=$$
purpose=$PURPOSE
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
trap 'rm -f "$LOCK"' EXIT
shift
exec "$@"
