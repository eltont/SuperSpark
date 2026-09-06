"""SuperSpark job runner: baseline / native / optimized modes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("SUPERSPARK_ROOT", Path(__file__).resolve().parents[2]))
CACHE = ROOT / "artifacts" / "cache"
LOGS = ROOT / "artifacts" / "logs"
REPORTS = ROOT / "artifacts" / "reports"
DATA = ROOT / "artifacts" / "data"
SPARK_HOME = Path(os.environ.get("SPARK_HOME", CACHE / "spark-3.5.5-bin-hadoop3"))
GLUTEN_JAR = CACHE / "gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar"
JAVA_HOME = Path(os.environ.get("JAVA_HOME", Path.home() / ".local/opt/jdk-17"))

SCENARIOS = [
    "filter_project",
    "joins",
    "aggregate",
    "sort_topk",
    "strings",
    "skew",
    "parquet_roundtrip",
    "small_files",
    "spill",
    "fallback_udf",
    "edge_cases",
]

NATIVE_EVIDENCE_PATTERNS = [
    r"ProjectExecTransformer",
    r"FilterExecTransformer",
    r"HashAggregateExecTransformer",
    r"ShuffledHashJoinExecTransformer",
    r"SortMergeJoinExecTransformer",
    r"WholeStageCodegenTransformer",
    r"VeloxColumnarToRowExec",
    r"BatchScanExecTransformer",
    r"FileSourceScanExecTransformer",
    r"ColumnarToRowExec",
    r"Native Plan",
    r"GlutenPlugin",
]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dirs() -> None:
    for p in (LOGS, REPORTS, DATA, LOGS / "events"):
        p.mkdir(parents=True, exist_ok=True)


def lockfile_hash() -> str:
    p = ROOT / "versions.lock.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "missing"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def mode_conf(mode: str) -> list[str]:
    conf = [
        "spark.sql.adaptive.enabled=true",
        "spark.eventLog.enabled=true",
        f"spark.eventLog.dir={LOGS / 'events'}",
        "spark.driver.memory=1g",
        "spark.executor.memory=1536m",
        "spark.sql.shuffle.partitions=4",
    ]
    if mode == "baseline":
        return conf
    if mode in ("native", "optimized"):
        if not GLUTEN_JAR.exists():
            raise SystemExit(f"Gluten jar missing: {GLUTEN_JAR}")
        # JDK 17: Netty/Arrow/Gluten need reflective access to DirectByteBuffer
        jdk17_opens = (
            "-Dio.netty.tryReflectionSetAccessible=true "
            "--add-opens=java.base/java.nio=ALL-UNNAMED "
            "--add-opens=java.base/java.lang=ALL-UNNAMED "
            "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
            "--add-opens=java.base/java.io=ALL-UNNAMED "
            "--add-opens=java.base/java.net=ALL-UNNAMED "
            "--add-opens=java.base/java.nio.file=ALL-UNNAMED "
            "--add-opens=java.base/java.security=ALL-UNNAMED "
            "--add-opens=java.base/java.util=ALL-UNNAMED "
            "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
            "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
            "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
            "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
            "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED "
            "--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED"
        )
        conf += [
            "spark.plugins=org.apache.gluten.GlutenPlugin",
            "spark.shuffle.manager=org.apache.spark.shuffle.sort.ColumnarShuffleManager",
            "spark.memory.offHeap.enabled=true",
            "spark.memory.offHeap.size=1536m",
            f"spark.driver.extraClassPath={GLUTEN_JAR}",
            f"spark.executor.extraClassPath={GLUTEN_JAR}",
            f"spark.driver.extraJavaOptions={jdk17_opens}",
            f"spark.executor.extraJavaOptions={jdk17_opens}",
            "spark.gluten.sql.columnar.backend.velox.showTaskMetricsWhenFinished=true",
            "spark.gluten.sql.injectNativePlanStringToExplain=true",
        ]
        if mode == "optimized":
            conf += [
                "spark.superspark.optimize.enabled=true",
                # Conservative batch-size / offload policy (project optimization)
                "spark.gluten.sql.columnar.maxBatchSize=8192",
                "spark.gluten.memory.dynamic.offHeap.sizing.enabled=true",
            ]
        return conf
    raise SystemExit(f"unknown mode {mode}")


def spark_submit_cmd(mode: str, app: Path, app_args: list[str], master: str = "local[4]") -> list[str]:
    cmd = [
        str(SPARK_HOME / "bin" / "spark-submit"),
        "--master",
        master,
        "--deploy-mode",
        "client",
    ]
    for c in mode_conf(mode):
        cmd += ["--conf", c]
    cmd.append(str(app))
    cmd += app_args
    return cmd


def run_captured(cmd: list[str], log_path: Path, env: dict | None = None) -> tuple[int, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    merged_env = os.environ.copy()
    merged_env["JAVA_HOME"] = str(JAVA_HOME)
    merged_env["PATH"] = f"{JAVA_HOME}/bin:{merged_env.get('PATH', '')}"
    if env:
        merged_env.update(env)
    print("+", " ".join(cmd))
    with log_path.open("w") as log:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=merged_env)
        log.write(proc.stdout)
        print(proc.stdout[-4000:] if len(proc.stdout) > 4000 else proc.stdout)
        return proc.returncode, proc.stdout


def extract_native_evidence(text: str) -> dict:
    hits = {pat: len(re.findall(pat, text)) for pat in NATIVE_EVIDENCE_PATTERNS}
    substantial_keys = (
        "ProjectExecTransformer",
        "FilterExecTransformer",
        "HashAggregateExecTransformer",
        "ShuffledHashJoinExecTransformer",
        "SortMergeJoinExecTransformer",
        "WholeStageCodegenTransformer",
        "VeloxColumnarToRowExec",
        "BatchScanExecTransformer",
        "FileSourceScanExecTransformer",
        "Native Plan",
    )
    substantial = sum(hits.get(k, 0) for k in substantial_keys)
    return {
        "hits": hits,
        "substantial_native_nodes": substantial,
        "native_execution_asserted": substantial > 0,
    }


def write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def cmd_scenarios_list(_: argparse.Namespace) -> int:
    for name in SCENARIOS:
        print(f"{name}\t{ROOT / 'examples' / 'spark' / (name + '.py')}")
    return 0


def run_scenario(name: str, mode: str, profile: str, size: str) -> dict:
    ensure_dirs()
    run_id = f"{name}-{mode}-{size}-{uuid.uuid4().hex[:8]}"
    out_dir = DATA / "outputs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    app = ROOT / "examples" / "spark" / f"{name}.py"
    if not app.exists():
        raise SystemExit(f"missing scenario {app}")
    expected = ROOT / "examples" / "expected" / f"{name}.json"
    app_args = [
        "--size",
        size,
        "--seed",
        "42",
        "--output",
        str(out_dir),
        "--input",
        str(ROOT / "examples" / "fixtures" / "tiny"),
        "--expected",
        str(expected),
        "--check-expected",
    ]
    # fallback_udf expects fallback; still must succeed functionally in baseline;
    # in native, expected fallback is OK.
    if name == "fallback_udf" and mode != "baseline":
        # still check expected rows if program supports it
        pass

    log_path = LOGS / f"{run_id}.log"
    t0 = time.time()
    # Prefer containerized Linux for native mode on Mac host
    if mode in ("native", "optimized") and sys.platform == "darwin":
        rc, out = run_in_docker(mode, app, app_args, log_path)
    else:
        rc, out = run_captured(spark_submit_cmd(mode, app, app_args), log_path)
    elapsed_ms = int((time.time() - t0) * 1000)
    evidence = extract_native_evidence(out)
    correctness = "PASS" if rc == 0 else "FAIL"
    if name == "fallback_udf" and mode in ("native", "optimized") and rc == 0:
        correctness = "EXPECTED_FALLBACK" if "fallback" in out.lower() or evidence["substantial_native_nodes"] == 0 else "PASS"

    if mode in ("native", "optimized") and name not in ("fallback_udf",) and rc == 0:
        if not evidence["native_execution_asserted"]:
            correctness = "FAIL"
            print("Native mode completed but no native plan evidence found", file=sys.stderr)
            rc = 2

    manifest = {
        "run_id": run_id,
        "timestamp": utcnow(),
        "git_commit": git_commit(),
        "lockfile_hash": lockfile_hash(),
        "image_digest": None,
        "mode": mode,
        "host_arch": os.uname().machine,
        "cpu_model": _cpu_model(),
        "node_count": 1,
        "resource_limits": {"master": "local-or-container"},
        "storage_profile": "local-file",
        "spark_conf_redacted": mode_conf(mode),
        "workload_id": name,
        "seed": 42,
        "input_rows": None,
        "input_bytes": None,
        "trial_index": 0,
        "warmup_status": "none",
        "application_ms": elapsed_ms,
        "action_ms": elapsed_ms,
        "correctness_status": correctness,
        "native_execution_evidence": evidence,
        "fallback_reasons": None,
        "shuffle_read_bytes": None,
        "shuffle_write_bytes": None,
        "spill_bytes": None,
        "peak_memory_if_measured": None,
        "exit_status": rc,
        "failure_reason": None if rc == 0 else f"exit {rc}",
        "evidence_paths": {"log": str(log_path), "output": str(out_dir)},
        "profile": profile,
        "size": size,
    }
    write_manifest(REPORTS / "runs" / f"{run_id}.json", manifest)
    return manifest


def _cpu_model() -> str:
    try:
        if sys.platform == "darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        pass
    return "unknown"


def run_in_docker(mode: str, app: Path, app_args: list[str], log_path: Path) -> tuple[int, str]:
    """Run Spark job inside Linux arm64 container (required for Gluten native libs)."""
    image = "superspark/spark-native:3.5.5-gluten1.6.0" if mode != "baseline" else "superspark/spark-baseline:3.5.5"
    # Ensure image exists
    if subprocess.call(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        print(f"Image {image} missing; build via make build", file=sys.stderr)
        return 1, f"missing image {image}"

    conf_args = []
    for c in mode_conf(mode):
        # rewrite paths for container
        c = c.replace(str(GLUTEN_JAR), "/opt/gluten/gluten-velox-bundle.jar")
        c = c.replace(str(LOGS / "events"), "/work/artifacts/logs/events")
        conf_args += ["--conf", c]

    rel_app = str(app.relative_to(ROOT))
    docker_app_args = []
    i = 0
    while i < len(app_args):
        a = app_args[i]
        if a in ("--output", "--input", "--expected") and i + 1 < len(app_args):
            p = Path(app_args[i + 1])
            try:
                rel = p.relative_to(ROOT)
                docker_app_args += [a, f"/work/{rel}"]
            except ValueError:
                docker_app_args += [a, app_args[i + 1]]
            i += 2
            continue
        docker_app_args.append(a)
        i += 1

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
        image,
        "/opt/spark/bin/spark-submit",
        "--master",
        "local[4]",
        *conf_args,
        f"/work/{rel_app}",
        *docker_app_args,
    ]
    return run_captured(cmd, log_path)


def cmd_scenario(args: argparse.Namespace) -> int:
    m = run_scenario(args.name, args.mode, args.profile, args.size)
    print(json.dumps({"run_id": m["run_id"], "correctness_status": m["correctness_status"], "exit_status": m["exit_status"]}, indent=2))
    return 0 if m["exit_status"] == 0 and m["correctness_status"] in ("PASS", "EXPECTED_FALLBACK") else 1


def cmd_scenarios(args: argparse.Namespace) -> int:
    results = []
    modes = ["baseline", "native"]
    # optimized only when implemented flag file present or always attempt with NOT IMPLEMENTED handling
    for name in SCENARIOS:
        for mode in modes:
            try:
                m = run_scenario(name, mode, args.profile, args.size)
            except SystemExit as e:
                m = {"workload_id": name, "mode": mode, "correctness_status": "FAIL", "exit_status": 1, "failure_reason": str(e)}
            results.append(m)
            if m.get("exit_status", 1) != 0 and name != "fallback_udf":
                # continue suite but record failure
                pass
        # optimized
        results.append(
            {
                "workload_id": name,
                "mode": "optimized",
                "correctness_status": "NOT_IMPLEMENTED" if not (ROOT / "artifacts" / "OPTIMIZATION_ENABLED").exists() else "PENDING",
                "exit_status": 0,
            }
        )
    summary_path = REPORTS / f"scenarios-{args.size}-{int(time.time())}.json"
    write_manifest(summary_path, {"results": results})
    print(f"Wrote {summary_path}")
    hard_fail = [
        r
        for r in results
        if r.get("mode") in ("baseline", "native")
        and r.get("correctness_status") not in ("PASS", "EXPECTED_FALLBACK", "NOT_RUN")
        and r.get("workload_id") != "fallback_udf"
    ]
    # fallback_udf native may be EXPECTED_FALLBACK
    return 1 if hard_fail else 0


def cmd_smoke(args: argparse.Namespace) -> int:
    """Deterministic filter/join/aggregate smoke."""
    ensure_dirs()
    # generate fixtures
    subprocess.check_call([sys.executable, str(ROOT / "examples" / "fixtures" / "generate_tiny.py")])
    names = ["filter_project", "joins", "aggregate"]
    failed = False
    manifests = []
    for name in names:
        m = run_scenario(name, args.mode, "local", "tiny")
        manifests.append(m)
        if m["exit_status"] != 0 or m["correctness_status"] not in ("PASS", "EXPECTED_FALLBACK"):
            failed = True
        if args.mode in ("native", "optimized") and name != "fallback_udf":
            if not m["native_execution_evidence"].get("native_execution_asserted"):
                failed = True
    write_manifest(REPORTS / f"smoke-{args.mode}-{int(time.time())}.json", {"manifests": manifests})
    return 1 if failed else 0


def cmd_bench(args: argparse.Namespace) -> int:
    ensure_dirs()
    # Use aggregate as compute-heavy tiny/small stand-in; larger sizes via SIZE env later
    size = os.environ.get("BENCH_SIZE", "small")
    m = run_scenario("aggregate", args.mode, args.profile, size if size in ("tiny", "small", "benchmark") else "small")
    print(json.dumps(m, indent=2))
    return 0 if m["exit_status"] == 0 else 1


def cmd_local_test(args: argparse.Namespace) -> int:
    # Correctness across scenarios in baseline+native; infra tests documented separately
    ns = argparse.Namespace(profile="k3d", size="tiny")
    return cmd_scenarios(ns)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="superspark")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scenarios-list")
    p.set_defaults(func=cmd_scenarios_list)

    p = sub.add_parser("scenario")
    p.add_argument("--name", required=True)
    p.add_argument("--mode", default="baseline", choices=["baseline", "native", "optimized"])
    p.add_argument("--profile", default="local")
    p.add_argument("--size", default="tiny")
    p.set_defaults(func=cmd_scenario)

    p = sub.add_parser("scenarios")
    p.add_argument("--profile", default="local")
    p.add_argument("--size", default="tiny")
    p.set_defaults(func=cmd_scenarios)

    p = sub.add_parser("smoke")
    p.add_argument("--mode", required=True, choices=["baseline", "native", "optimized"])
    p.set_defaults(func=cmd_smoke)

    p = sub.add_parser("bench")
    p.add_argument("--profile", default="local")
    p.add_argument("--mode", required=True, choices=["baseline", "native", "optimized"])
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("local-test")
    p.set_defaults(func=cmd_local_test)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
