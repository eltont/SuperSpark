#!/usr/bin/env python3
"""Sort-heavy per-region top-N; larger sizes amplify shuffle/spill pressure."""

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
    # Extra width to encourage memory pressure on benchmark
    return (
        spark.range(1, n + 1)
        .withColumnRenamed("id", "order_id")
        .withColumn(
            "amount",
            F.round(F.col("order_id") * 10.0 + (F.col("order_id") % 7) * 3.5, 2),
        )
        .withColumn(
            "region",
            F.element_at(
                F.array(F.lit("west"), F.lit("east"), F.lit("central"), F.lit("south")),
                ((((F.col("order_id") - 1) % 4) + 1).cast("int")),
            ),
        )
        .withColumn("payload", F.concat(F.lit("x" * 64), F.col("order_id").cast("string")))
    )


def main() -> int:
    def extra(p):
        p.add_argument("--per-region", type=int, default=3, help="Top-N rows per region")

    parser = build_arg_parser("Windowed top-N per region (spill-prone at large size)", extra=extra)
    args = parser.parse_args()
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    # Encourage spill on larger profiles via small shuffle partitions / modest memory hint
    spark = create_spark(args.app_name or "spill", args.master, args.profile)
    if args.size == "benchmark":
        spark.conf.set("spark.sql.shuffle.partitions", "16")
        spark.conf.set("spark.reducer.maxSizeInFlight", "24m")

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        w = Window.partitionBy("region").orderBy(F.col("amount").desc(), F.col("order_id").asc())
        topn = (
            orders.withColumn("rn", F.row_number().over(w))
            .filter(F.col("rn") <= args.per_region)
            .select("region", "order_id", "amount")
        )
        ordered = topn.orderBy("region", F.col("amount").desc(), "order_id")
        _ = ordered.count()
        rows = rows_to_jsonable(ordered.collect())
        return finish(args, "spill", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
