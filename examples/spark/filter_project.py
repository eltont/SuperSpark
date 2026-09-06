#!/usr/bin/env python3
"""Filter + project: complete orders with amount > 50."""

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


def synthesize(spark, seed: int, size: str):
    from pyspark.sql import functions as F
    n = 40 * scale_for(size)
    return (
        spark.range(1, n + 1)
        .withColumnRenamed("id", "order_id")
        .withColumn("customer_id", ((((F.col("order_id") - 1) % 10) + 1).cast("int")))
        .withColumn(
            "amount",
            F.round(F.col("order_id") * 10.0 + (F.col("order_id") % 7) * 3.5, 2),
        )
        .withColumn(
            "status",
            F.element_at(F.array(F.lit("complete"), F.lit("pending"), F.lit("cancelled")),
                         ((((F.col("order_id") - 1) % 3) + 1).cast("int"))),
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
    parser = build_arg_parser("Filter complete orders with amount > 50 and project columns")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "filter_project", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        if inp:
            orders = spark.read.json(inp)
        else:
            orders = synthesize(spark, args.seed, args.size)

        result = (
            orders.filter((F.col("amount") > 50) & (F.col("status") == "complete"))
            .select("order_id", "customer_id", "amount", "region")
        )
        rows = collect_sorted(result, ["order_id"])
        return finish(args, "filter_project", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
