#!/usr/bin/env python3
"""Aggregate non-cancelled orders by region."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    collect_sorted,
    create_spark,
    finish,
    require_input_or_fixtures,
    scale_for,
)


def synthesize(spark, size: str):
    from pyspark.sql import functions as F
    n = 40 * scale_for(size)
    return (
        spark.range(1, n + 1)
        .withColumnRenamed("id", "order_id")
        .withColumn(
            "amount",
            F.round(F.col("order_id") * 10.0 + (F.col("order_id") % 7) * 3.5, 2),
        )
        .withColumn(
            "status",
            F.element_at(
                F.array(F.lit("complete"), F.lit("pending"), F.lit("cancelled")),
                ((((F.col("order_id") - 1) % 3) + 1).cast("int")),
            ),
        )
        .withColumn(
            "region",
            F.element_at(
                F.array(F.lit("west"), F.lit("east"), F.lit("central"), F.lit("south")),
                ((((F.col("order_id") - 1) % 4) + 1).cast("int")),
            ),
        )
    )


def main() -> int:
    parser = build_arg_parser("Group-by region aggregates on non-cancelled orders")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "aggregate", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        agg = (
            orders.filter(F.col("status") != "cancelled")
            .groupBy("region")
            .agg(
                F.count("*").alias("order_count"),
                F.round(F.sum("amount"), 2).alias("amount_sum"),
                F.round(F.avg("amount"), 4).alias("amount_avg"),
            )
        )
        rows = collect_sorted(agg, ["region"])
        return finish(args, "aggregate", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
