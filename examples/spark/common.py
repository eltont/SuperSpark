#!/usr/bin/env python3
"""Shared helpers for SuperSpark example Spark scenarios.

Programs must not import project accelerator code. These helpers cover CLI,
session setup, fixture IO, result serialization, and optional expected-file
self-checks only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = EXAMPLES_ROOT / "fixtures"
DEFAULT_EXPECTED = EXAMPLES_ROOT / "expected"
DEFAULT_OUTPUT = EXAMPLES_ROOT.parent / "artifacts" / "scenario-out"

SIZE_CHOICES = ("tiny", "small", "benchmark")

# Approximate row multipliers when synthesizing data for non-tiny sizes.
SIZE_SCALE = {
    "tiny": 1,
    "small": 50,
    "benchmark": 2000,
}


def scale_for(size: str) -> int:
    # Optional override for laptop benches: SUPERSPARK_SCALE_MULT=100 → 100× default scale
    base = SIZE_SCALE[size]
    mult = int(os.environ.get("SUPERSPARK_SCALE_MULT", "1"))
    return max(1, base * mult)


def build_arg_parser(
    description: str,
    *,
    default_input: Optional[str] = None,
    default_output: Optional[str] = None,
    extra: Optional[Callable] = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic RNG seed (default: 42)",
    )
    parser.add_argument(
        "--size",
        choices=SIZE_CHOICES,
        default="tiny",
        help="Workload size profile: tiny | small | benchmark",
    )
    parser.add_argument(
        "--profile",
        default=os.environ.get("SUPERSPARK_PROFILE", "local"),
        help="Execution profile label (local|k3d|...); informational for apps",
    )
    parser.add_argument(
        "--input",
        default=default_input,
        help="Input path (JSONL directory/file, or Parquet). Defaults vary by scenario.",
    )
    parser.add_argument(
        "--output",
        default=default_output or str(DEFAULT_OUTPUT),
        help="Output directory for materializing results",
    )
    parser.add_argument(
        "--expected",
        default=None,
        help="Optional expected JSON path for tiny self-check",
    )
    parser.add_argument(
        "--app-name",
        default=None,
        help="Spark application name override",
    )
    parser.add_argument(
        "--master",
        default=os.environ.get("SPARK_MASTER", "local[*]"),
        help="Spark master URL (default: local[*] or $SPARK_MASTER)",
    )
    parser.add_argument(
        "--check-expected",
        action="store_true",
        help="Compare collected result against --expected (or default tiny expected)",
    )
    if extra is not None:
        extra(parser)
    return parser


def create_spark(app_name: str, master: str, profile: str):
    """Create a SparkSession. Requires pyspark on PYTHONPATH / SPARK_HOME."""
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise SystemExit(
            "pyspark is not available. Set SPARK_HOME and ensure pyspark is importable."
        ) from exc

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", "4" if "local" in master else "8")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.superspark.profile", profile)
    )
    return builder.getOrCreate()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def fixture_path(size: str, name: str) -> Path:
    return DEFAULT_FIXTURES / size / name


def default_expected_path(scenario: str) -> Path:
    return DEFAULT_EXPECTED / f"{scenario}.json"


def read_jsonl_spark(spark, path: str | Path):
    """Read JSON / JSONL with spark.read.json."""
    return spark.read.json(str(path))


def write_parquet(df, path: str | Path, mode: str = "overwrite") -> None:
    ensure_dir(Path(path).parent if Path(path).suffix else path)
    df.write.mode(mode).parquet(str(path))


def write_jsonl_local(path: str | Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def rows_to_jsonable(rows: Sequence[Any]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        if hasattr(row, "asDict"):
            out.append(row.asDict(recursive=True))
        elif isinstance(row, dict):
            out.append(row)
        else:
            out.append(dict(row))
    return out


def stable_sort_rows(rows: list[dict], keys: Sequence[str]) -> list[dict]:
    def sort_key(r: dict):
        return tuple(_sortable(r.get(k)) for k in keys)

    return sorted(rows, key=sort_key)


def _sortable(v: Any):
    if v is None:
        return (0, "")
    if isinstance(v, float):
        return (1, f"{v:.10g}")
    return (1, v)


def checksum_rows(rows: Sequence[dict]) -> str:
    payload = json.dumps(list(rows), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_result_json(
    path: str | Path,
    *,
    scenario: str,
    seed: int,
    size: str,
    rows: Sequence[dict],
    extras: Optional[dict] = None,
) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    body = {
        "scenario": scenario,
        "seed": seed,
        "size": size,
        "row_count": len(rows),
        "checksum": checksum_rows(rows),
        "rows": list(rows),
    }
    if extras:
        body["extras"] = extras
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_expected(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def compare_with_expected(actual_rows: Sequence[dict], expected_path: str | Path) -> None:
    """Raise SystemExit(1) if actual rows diverge from expected file."""
    expected = load_expected(expected_path)
    exp_rows = expected.get("rows", expected if isinstance(expected, list) else [])
    act = json.loads(json.dumps(list(actual_rows), sort_keys=True, default=str))
    exp = json.loads(json.dumps(list(exp_rows), sort_keys=True, default=str))
    if act != exp:
        print(
            f"RESULT MISMATCH vs {expected_path}\n"
            f"  actual_count={len(act)} expected_count={len(exp)}\n"
            f"  actual_checksum={checksum_rows(act)}\n"
            f"  expected_checksum={checksum_rows(exp)}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(f"OK: matched expected {expected_path} ({len(act)} rows)")


def maybe_check_expected(
    args: argparse.Namespace,
    scenario: str,
    rows: Sequence[dict],
) -> None:
    if not getattr(args, "check_expected", False) and not args.expected:
        return
    path = args.expected or str(default_expected_path(scenario))
    if args.size != "tiny":
        print(
            f"Skipping expected check for size={args.size} (only tiny has gold files)",
            file=sys.stderr,
        )
        return
    if not Path(path).is_file():
        print(f"Expected file missing: {path}", file=sys.stderr)
        raise SystemExit(1)
    compare_with_expected(rows, path)


def collect_sorted(df, order_cols: Sequence[str]) -> list[dict]:
    """Materialize with an action and return stably ordered Python dicts."""
    ordered = df.orderBy(*order_cols)
    # Emit physical plan for native-coverage evidence (Gluten injects Native Plan strings).
    try:
        print("=== EXPLAIN extended ===")
        ordered.explain(extended=True)
    except Exception as exc:  # noqa: BLE001
        print(f"explain failed: {exc}", file=sys.stderr)
    # Force a materializing action beyond collect for timing/IO realism.
    _ = ordered.count()
    return rows_to_jsonable(ordered.collect())


def finish(
    args: argparse.Namespace,
    scenario: str,
    rows: Sequence[dict],
    *,
    extras: Optional[dict] = None,
    spark=None,
) -> int:
    out_dir = ensure_dir(Path(args.output) / scenario / args.size)
    result_path = out_dir / "result.json"
    write_result_json(
        result_path,
        scenario=scenario,
        seed=args.seed,
        size=args.size,
        rows=rows,
        extras=extras,
    )
    print(f"Wrote {len(rows)} rows -> {result_path}")
    maybe_check_expected(args, scenario, rows)
    if spark is not None:
        spark.stop()
    return 0


def resolve_input(args: argparse.Namespace, relative_name: str) -> str:
    """Resolve input path. If --input is a directory, append relative_name."""
    if args.input:
        p = Path(args.input)
        if p.is_dir():
            candidate = p / relative_name
            if candidate.exists():
                return str(candidate)
            # Also accept parquet directory named without extension
            stem = Path(relative_name).stem
            for alt in (p / stem, p / f"{stem}.parquet"):
                if alt.exists():
                    return str(alt)
            return str(candidate)
        return str(p)
    if args.size == "tiny":
        path = fixture_path("tiny", relative_name)
        if not path.exists():
            print(
                f"Missing fixture {path}. Run: python examples/fixtures/generate_tiny.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return str(path)
    return ""


def require_input_or_fixtures(args: argparse.Namespace, relative_name: str) -> str:
    """Resolve --input or fall back to examples/fixtures/<size>/<name> for tiny."""
    return resolve_input(args, relative_name)
