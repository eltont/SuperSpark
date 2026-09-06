#!/usr/bin/env python3
"""Inner join orders ↔ customers; gold tier + complete status."""

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
    n = 40 * scale_for(size)
    orders = (
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
    customers = (
        spark.range(1, 11)
        .withColumnRenamed("id", "customer_id")
        .withColumn("name", F.format_string("Customer_%02d", F.col("customer_id")))
        .withColumn(
            "tier",
            F.element_at(
                F.array(F.lit("gold"), F.lit("silver"), F.lit("bronze")),
                ((((F.col("customer_id") - 1) % 3) + 1).cast("int")),
            ),
        )
        .withColumn(
            "country",
            F.element_at(
                F.array(F.lit("US"), F.lit("CA"), F.lit("UK"), F.lit("DE")),
                ((((F.col("customer_id") - 1) % 4) + 1).cast("int")),
            ),
        )
    )
    return orders, customers


def main() -> int:
    parser = build_arg_parser("Join orders to customers; filter gold + complete")
    parser.add_argument("--input-orders", default=None)
    parser.add_argument("--input-customers", default=None)
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "joins", args.master, args.profile)

    try:
        if args.size == "tiny":
            orders_path = args.input_orders or resolve_input(args, "orders.jsonl")
            cust_path = args.input_customers or resolve_input(args, "customers.jsonl")
            orders = spark.read.json(orders_path)
            customers = spark.read.json(cust_path)
        else:
            orders, customers = synthesize(spark, args.size)

        joined = (
            orders.alias("o")
            .join(customers.alias("c"), on="customer_id", how="inner")
            .filter((F.col("c.tier") == "gold") & (F.col("o.status") == "complete"))
            .select(
                F.col("o.order_id").alias("order_id"),
                F.col("o.customer_id").alias("customer_id"),
                F.col("c.name").alias("name"),
                F.col("c.country").alias("country"),
                F.col("o.amount").alias("amount"),
                F.col("o.region").alias("region"),
            )
        )
        rows = collect_sorted(joined, ["order_id"])
        return finish(args, "joins", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
