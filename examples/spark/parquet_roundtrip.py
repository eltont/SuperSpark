#!/usr/bin/env python3
"""JSON → Parquet → Parquet read checksum round-trip."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    create_spark,
    ensure_dir,
    finish,
    require_input_or_fixtures,
    rows_to_jsonable,
    scale_for,
    write_parquet,
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
    )


def main() -> int:
    parser = build_arg_parser("Parquet write/read round-trip checksum")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "parquet_roundtrip", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        parquet_dir = ensure_dir(Path(args.output) / "parquet_roundtrip" / args.size / "data")
        write_parquet(orders.select("order_id", "amount", "status"), parquet_dir)

        reloaded = spark.read.parquet(str(parquet_dir))
        summary = reloaded.agg(
            F.count("*").alias("row_count"),
            F.round(F.sum("amount"), 2).alias("amount_sum"),
            F.min("order_id").alias("min_order_id"),
            F.max("order_id").alias("max_order_id"),
        )
        _ = summary.count()
        rows = rows_to_jsonable(summary.collect())
        return finish(
            args,
            "parquet_roundtrip",
            rows,
            extras={"parquet_path": str(parquet_dir)},
            spark=spark,
        )
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
