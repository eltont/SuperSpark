#!/usr/bin/env bash
set -euo pipefail
echo "=== check-updates (no mutation) ==="
echo "Pinned Gluten: 1.6.0"
curl -fsSL https://downloads.apache.org/gluten/ 2>/dev/null | grep -oE 'gluten/[0-9]+\.[0-9]+\.[0-9]+' | sort -u | tail -5 || true
echo "Pinned Spark: 3.5.5"
curl -fsSL https://downloads.apache.org/spark/ 2>/dev/null | grep -oE 'spark-[0-9]+\.[0-9]+\.[0-9]+' | sort -u | tail -10 || true
echo "Pinned k3d: v5.8.3; latest:"
curl -fsSL https://api.github.com/repos/k3d-io/k3d/releases/latest 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["tag_name"])' || true
echo "Done. No lockfile changes made."
