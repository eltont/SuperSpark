#!/usr/bin/env python3
"""Null / empty / NaN / division edge cases."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    create_spark,
    finish,
    resolve_input,
    rows_to_jsonable,
)


def load_edges(spark, args):
    from pyspark.sql import functions as F
    if args.size == "tiny":
        path = resolve_input(args, "edge_rows.jsonl")
        df = spark.read.json(path)
        # Restore NaN marker written by generate_tiny.py
        return df.withColumn(
            "a",
            F.when(F.col("a_was_nan") == True, F.lit(float("nan"))).otherwise(F.col("a")),  # noqa: E712
        )
    rows = [
        {"id": 1, "a": 1.0, "b": 2.0, "s": "ok", "n": 1},
        {"id": 2, "a": None, "b": 2.0, "s": None, "n": None},
        {"id": 3, "a": 0.0, "b": 0.0, "s": "", "n": 0},
        {"id": 4, "a": -1.5, "b": 3.0, "s": "  pad  ", "n": -3},
        {"id": 5, "a": 1e308, "b": 1e308, "s": "unicode-✓", "n": 42},
        {"id": 6, "a": float("nan"), "b": 1.0, "s": "nan-a", "n": 7},
        {"id": 7, "a": 4.0, "b": None, "s": "div0-guard", "n": 2},
        {"id": 8, "a": 2.5, "b": 5.0, "s": "Café", "n": 3},
    ]
    # Scale by repeating with shifted ids for non-tiny
    from common import scale_for

    out = []
    for copy in range(scale_for(args.size)):
        for r in rows:
            nr = dict(r)
            nr["id"] = r["id"] + copy * 100
            out.append(nr)
    return spark.createDataFrame(out)


def main() -> int:
    parser = build_arg_parser("Null/NaN/empty-string edge-case expressions")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "edge_cases", args.master, args.profile)

    try:
        edges = load_edges(spark, args)
        result = (
            edges.withColumn(
                "ratio",
                F.when(F.col("a").isNull() | F.col("b").isNull() | (F.col("b") == 0), F.lit(None))
                .otherwise(F.round(F.col("a") / F.col("b"), 6)),
            )
            .withColumn("trimmed", F.trim(F.col("s")))
            .withColumn("n_is_null", F.col("n").isNull())
            .withColumn("a_is_null", F.col("a").isNull())
            .select("id", "ratio", "trimmed", "n_is_null", "a_is_null")
        )
        ordered = result.orderBy("id")
        _ = ordered.count()
        rows = rows_to_jsonable(ordered.collect())
        # Normalize NaN for JSON / expected compare (Spark may yield float nan)
        for r in rows:
            v = r.get("ratio")
            if isinstance(v, float) and math.isnan(v):
                r["ratio"] = "NaN"
        return finish(args, "edge_cases", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
