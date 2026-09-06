#!/usr/bin/env python3
"""Compare completed run manifests and emit Markdown + JSON reports."""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "artifacts" / "reports" / "runs"
OUT = ROOT / "artifacts" / "reports"


def load_runs():
    if not RUNS.exists():
        return []
    rows = []
    for p in sorted(RUNS.glob("*.json"), key=lambda x: x.stat().st_mtime):
        rows.append(json.loads(p.read_text()))
    return rows


def geomean(vals):
    vals = [v for v in vals if v and v > 0]
    if not vals:
        return None
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    by_key = defaultdict(list)
    for r in runs:
        key = (r.get("workload_id"), r.get("mode"), r.get("size"))
        by_key[key].append(r)

    lines = ["# SuperSpark report", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    lines.append("| Workload | Mode | Size | Status | App ms | Native evidence |")
    lines.append("|----------|------|------|--------|--------|-----------------|")
    for (wl, mode, size), items in sorted(by_key.items()):
        latest = items[-1]
        evid = latest.get("native_execution_evidence") or {}
        ne = evid.get("native_execution_asserted")
        lines.append(
            f"| {wl} | {mode} | {size} | {latest.get('correctness_status')} | {latest.get('application_ms')} | {ne} |"
        )

    # Speedups baseline vs native where both exist
    lines += ["", "## Speedups (latest per workload)", ""]
    speedups = []
    workloads = sorted({r.get("workload_id") for r in runs})
    for wl in workloads:
        b = [r for r in runs if r.get("workload_id") == wl and r.get("mode") == "baseline" and r.get("application_ms")]
        n = [r for r in runs if r.get("workload_id") == wl and r.get("mode") == "native" and r.get("application_ms")]
        if b and n:
            bm = statistics.median(r["application_ms"] for r in b)
            nm = statistics.median(r["application_ms"] for r in n)
            if nm > 0:
                sp = bm / nm
                speedups.append(sp)
                lines.append(f"- {wl}: baseline_med={bm:.0f}ms native_med={nm:.0f}ms speedup={sp:.2f}x")

    gm = geomean(speedups)
    lines += ["", f"Suite geometric-mean speedup: {gm if gm else 'n/a'}", ""]
    lines.append("Notes: tiny sizes are correctness-oriented; do not treat as production performance certification.")
    md = OUT / "latest-report.md"
    md.write_text("\n".join(lines) + "\n")
    (OUT / "latest-report.json").write_text(json.dumps({"runs": len(runs), "geomean_speedup": gm}, indent=2) + "\n")
    print(md.read_text())
    print(f"Wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
