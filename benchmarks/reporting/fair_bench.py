#!/usr/bin/env python3
"""Fair small-size bench: baseline + native both in Linux containers.

Warm-up + N measured reps, alternating modes. Tiny is excluded by design.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("SUPERSPARK_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / "runner" / "python"))

from superspark_runner import (  # noqa: E402
    REPORTS,
    ensure_dirs,
    extract_native_evidence,
    mode_conf,
    run_captured,
    write_manifest,
)


def run_docker(mode: str, name: str, size: str, trial: int, warmup: bool) -> dict:
    """Force both baseline and native through Docker for fair timing."""
    image = (
        "superspark/spark-native:3.5.5-gluten1.6.0"
        if mode != "baseline"
        else "superspark/spark-baseline:3.5.5"
    )
    out_dir = ROOT / "artifacts" / "data" / "bench" / f"{name}-{mode}-{size}-t{trial}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "artifacts" / "logs" / f"bench-{name}-{mode}-{size}-t{trial}.log"

    conf_args: list[str] = []
    for c in mode_conf(mode):
        c = c.replace(str(ROOT / "artifacts" / "cache" / "gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar"), "/opt/gluten/gluten-velox-bundle.jar")
        c = c.replace(str(ROOT / "artifacts" / "logs" / "events"), "/work/artifacts/logs/events")
        conf_args += ["--conf", c]

    app = f"/work/examples/spark/{name}.py"
    # For non-tiny sizes, omit --input so programs synthesize scaled data.
    app_args = [
        "--size",
        size,
        "--seed",
        "42",
        "--output",
        f"/work/artifacts/data/bench/{name}-{mode}-{size}-t{trial}",
    ]
    if size == "tiny":
        app_args += ["--input", "/work/examples/fixtures/tiny"]

    cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/arm64",
        "-v",
        f"{ROOT}:/work",
        "-w",
        "/work",
        "-e",
        f"SUPERSPARK_SCALE_MULT={os.environ.get('SUPERSPARK_SCALE_MULT', '1')}",
        image,
        "/opt/spark/bin/spark-submit",
        "--master",
        "local[4]",
        *conf_args,
        app,
        *app_args,
    ]

    t0 = time.perf_counter()
    rc, out = run_captured(cmd, log_path)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    evidence = extract_native_evidence(out)
    status = "PASS" if rc == 0 else "FAIL"
    if mode == "native" and rc == 0 and not evidence.get("native_execution_asserted"):
        status = "FAIL"
        rc = 2

    manifest = {
        "run_id": f"bench-{name}-{mode}-{size}-t{trial}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "workload_id": name,
        "size": size,
        "trial_index": trial,
        "warmup_status": "warmup" if warmup else "measured",
        "application_ms": elapsed_ms,
        "action_ms": elapsed_ms,
        "correctness_status": status,
        "native_execution_evidence": evidence,
        "exit_status": rc,
        "evidence_paths": {"log": str(log_path), "output": str(out_dir)},
        "fairness": "both_modes_in_linux_arm64_docker",
    }
    write_manifest(REPORTS / "runs" / f"{manifest['run_id']}.json", manifest)
    return manifest


def summarize(results: list[dict]) -> dict:
    by = {}
    for r in results:
        if r["warmup_status"] != "measured":
            continue
        key = (r["workload_id"], r["mode"])
        by.setdefault(key, []).append(r["application_ms"])

    summary = {"workloads": {}, "generated": datetime.now(timezone.utc).isoformat()}
    for (wl, mode), times in sorted(by.items()):
        summary["workloads"].setdefault(wl, {})[mode] = {
            "n": len(times),
            "times_ms": times,
            "median_ms": statistics.median(times),
            "mean_ms": statistics.mean(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
            "min_ms": min(times),
            "max_ms": max(times),
        }

    for wl, modes in summary["workloads"].items():
        if "baseline" in modes and "native" in modes:
            b = modes["baseline"]["median_ms"]
            n = modes["native"]["median_ms"]
            modes["speedup_median"] = (b / n) if n else None
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workloads", default="aggregate,joins", help="comma-separated")
    parser.add_argument("--size", default="small", choices=["small", "benchmark"])
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--reps", type=int, default=5)
    args = parser.parse_args()

    ensure_dirs()
    workloads = [w.strip() for w in args.workloads.split(",") if w.strip()]
    results: list[dict] = []

    print(f"=== Fair Docker bench size={args.size} warmup={args.warmup} reps={args.reps} ===")
    print(f"workloads={workloads}")
    print("Both baseline and native run in linux/arm64 containers.\n")

    for name in workloads:
        # Warm-ups (baseline then native once each per warmup count)
        for w in range(args.warmup):
            for mode in ("baseline", "native"):
                print(f"[warmup {w}] {name} {mode} ...", flush=True)
                m = run_docker(mode, name, args.size, trial=-(w + 1), warmup=True)
                results.append(m)
                print(f"  -> {m['application_ms']}ms status={m['correctness_status']}", flush=True)
                if m["exit_status"] != 0:
                    print("Warm-up failed; aborting", file=sys.stderr)
                    return 1

        # Measured reps: alternate baseline/native each trial
        for t in range(args.reps):
            order = ("baseline", "native") if t % 2 == 0 else ("native", "baseline")
            for mode in order:
                print(f"[trial {t}] {name} {mode} ...", flush=True)
                m = run_docker(mode, name, args.size, trial=t, warmup=False)
                results.append(m)
                print(f"  -> {m['application_ms']}ms status={m['correctness_status']}", flush=True)
                if m["exit_status"] != 0:
                    print("Measured trial failed; continuing", file=sys.stderr)

    summary = summarize(results)
    out = REPORTS / f"bench-small-fair-{int(time.time())}.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=2) + "\n")
    md = REPORTS / "bench-small-fair-latest.md"
    lines = [
        "# Fair small-size bench (both modes in Docker)",
        "",
        f"Generated: {summary['generated']}",
        f"Size: {args.size}; warmup={args.warmup}; reps={args.reps}",
        "",
        "| Workload | Baseline median ms | Native median ms | Speedup |",
        "|----------|-------------------:|-----------------:|--------:|",
    ]
    for wl, modes in sorted(summary["workloads"].items()):
        b = modes.get("baseline", {}).get("median_ms")
        n = modes.get("native", {}).get("median_ms")
        sp = modes.get("speedup_median")
        lines.append(f"| {wl} | {b:.0f} | {n:.0f} | {sp:.2f}x |" if sp else f"| {wl} | {b} | {n} | n/a |")
        for mode in ("baseline", "native"):
            if mode in modes:
                d = modes[mode]
                lines.append(
                    f"  - {mode}: n={d['n']} median={d['median_ms']:.0f} "
                    f"mean={d['mean_ms']:.0f}±{d['stdev_ms']:.0f} "
                    f"min={d['min_ms']} max={d['max_ms']} times={d['times_ms']}"
                )
    lines += [
        "",
        "Notes:",
        "- Fair comparison: both modes use linux/arm64 Docker images.",
        "- Application elapsed includes container + Spark startup + job.",
        "- `small` is still modest data; not production certification.",
        f"- Raw JSON: `{out}`",
        "",
    ]
    md.write_text("\n".join(lines) + "\n")
    print("\n" + md.read_text())
    print(f"Wrote {md} and {out}")
    fails = [r for r in results if r["warmup_status"] == "measured" and r["exit_status"] != 0]
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
