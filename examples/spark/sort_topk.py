#!/usr/bin/env python3
"""Global top-K by amount (descending), order_id ascending tie-break."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    create_spark,
    finish,
    require_input_or_fixtures,
    rows_to_jsonable,
    scale_for,
)


def synthesize(spark, size: str):
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
    def extra(p):
        p.add_argument("--k", type=int, default=10, help="Top-K rows to keep")

    parser = build_arg_parser("Sort and take top-K orders by amount", extra=extra)
    args = parser.parse_args()
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    spark = create_spark(args.app_name or "sort_topk", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        w = Window.orderBy(F.col("amount").desc(), F.col("order_id").asc())
        topk = (
            orders.withColumn("rn", F.row_number().over(w))
            .filter(F.col("rn") <= args.k)
            .select("order_id", "customer_id", "amount", "status", "region")
        )
        ordered = topk.orderBy(F.col("amount").desc(), F.col("order_id").asc())
        _ = ordered.count()
        rows = rows_to_jsonable(ordered.collect())
        return finish(args, "sort_topk", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
