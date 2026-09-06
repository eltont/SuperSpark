#!/usr/bin/env python3
"""Skewed join + aggregate (hot key dominates event volume)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    collect_sorted,
    create_spark,
    finish,
    resolve_input,
    scale_for,
)


def synthesize(spark, size: str):
    from pyspark.sql import functions as F
    scale = scale_for(size)
    # Hot key 1 gets 80% of events
    n = 100 * scale
    events = (
        spark.range(1, n + 1)
        .withColumnRenamed("id", "event_id")
        .withColumn(
            "key",
            F.when(F.col("event_id") <= int(n * 0.8), F.lit(1))
            .when(F.col("event_id") <= int(n * 0.9), F.lit(2))
            .otherwise(2 + ((F.col("event_id") % 6) + 1)),
        )
        .withColumn(
            "value",
            F.round((F.col("event_id") * 1.7 + F.col("key") * 0.3) % 100, 2),
        )
    )
    dims = spark.createDataFrame(
        [{"key": k, "label": f"bucket_{k}", "weight": k * 10} for k in range(1, 9)]
    )
    return events, dims


def main() -> int:
    parser = build_arg_parser("Skew-heavy join of events to dimension keys")
    parser.add_argument("--input-events", default=None)
    parser.add_argument("--input-dims", default=None)
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "skew", args.master, args.profile)

    try:
        if args.size == "tiny":
            events = spark.read.json(
                args.input_events or resolve_input(args, "skew_events.jsonl")
            )
            dims = spark.read.json(
                args.input_dims or resolve_input(args, "dim_keys.jsonl")
            )
        else:
            events, dims = synthesize(spark, args.size)

        joined = (
            events.join(dims, on="key", how="inner")
            .groupBy("key", "label", "weight")
            .agg(
                F.count("*").alias("event_count"),
                F.round(F.sum("value"), 2).alias("value_sum"),
            )
            .select("key", "label", "event_count", "value_sum", "weight")
        )
        rows = collect_sorted(joined, ["key"])
        return finish(args, "skew", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
