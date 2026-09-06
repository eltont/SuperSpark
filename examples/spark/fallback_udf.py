#!/usr/bin/env python3
"""Python UDF path — typically falls back from native columnar execution."""

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


def amount_bucket(amount) -> str:
    if amount is None:
        return "unknown"
    if amount < 100:
        return "low"
    if amount < 300:
        return "mid"
    return "high"


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
    )


def main() -> int:
    parser = build_arg_parser("Python UDF amount bucketing (native fallback case)")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType
    spark = create_spark(args.app_name or "fallback_udf", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        bucket_udf = F.udf(amount_bucket, StringType())
        result = (
            orders.filter(F.col("status") == "complete")
            .withColumn("amount_bucket", bucket_udf(F.col("amount")))
            .select("order_id", "amount", "amount_bucket")
        )
        rows = collect_sorted(result, ["order_id"])
        return finish(args, "fallback_udf", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
