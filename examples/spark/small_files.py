#!/usr/bin/env python3
"""Many small partition files then coalesce and re-aggregate."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


from common import (
    build_arg_parser,
    collect_sorted,
    create_spark,
    ensure_dir,
    finish,
    require_input_or_fixtures,
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
            "region",
            F.element_at(
                F.array(F.lit("west"), F.lit("east"), F.lit("central"), F.lit("south")),
                ((((F.col("order_id") - 1) % 4) + 1).cast("int")),
            ),
        )
    )


def main() -> int:
    parser = build_arg_parser("Write many small files then coalesce/read")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "small_files", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "orders.jsonl")
        orders = spark.read.json(inp) if inp else synthesize(spark, args.size)

        scattered = ensure_dir(Path(args.output) / "small_files" / args.size / "scattered")
        # One partition per row for tiny → many small files; capped for larger sizes.
        n_parts = min(orders.count(), 40 if args.size == "tiny" else 200)
        (
            orders.select("order_id", "region")
            .repartition(n_parts)
            .write.mode("overwrite")
            .parquet(str(scattered))
        )

        coalesced_dir = ensure_dir(Path(args.output) / "small_files" / args.size / "coalesced")
        reloaded = spark.read.parquet(str(scattered)).coalesce(2)
        write_parquet(reloaded, coalesced_dir)

        summary = (
            spark.read.parquet(str(coalesced_dir))
            .groupBy("region")
            .agg(F.count("*").alias("cnt"))
        )
        rows = collect_sorted(summary, ["region"])
        return finish(
            args,
            "small_files",
            rows,
            extras={"scattered": str(scattered), "coalesced": str(coalesced_dir), "n_parts": n_parts},
            spark=spark,
        )
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
