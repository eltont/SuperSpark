#!/usr/bin/env python3
"""String transforms: trim, upper/lower, substring, regexp_replace."""

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


def synthesize_stable(spark, size: str):
    base = [
        "  Hello World  ",
        "spark SQL rocks",
        "Café Münchën",
        "foo-bar-baz",
        "UPPER and lower",
        "123-456-7890",
        "a@b.co",
        "   ",
        "Gluten+Velox",
        "repeat repeat",
    ]
    n = len(base) if size == "tiny" else len(base) * max(1, scale_for(size) // 5)
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "id": i,
                "text": base[(i - 1) % len(base)],
                "locale": ["en", "de", "fr", "en"][(i - 1) % 4],
            }
        )
    return spark.createDataFrame(rows)


def main() -> int:
    parser = build_arg_parser("String expression workload")
    args = parser.parse_args()
    from pyspark.sql import functions as F
    spark = create_spark(args.app_name or "strings", args.master, args.profile)

    try:
        inp = require_input_or_fixtures(args, "text_rows.jsonl")
        texts = spark.read.json(inp) if inp else synthesize_stable(spark, args.size)

        transformed = (
            texts.withColumn("trimmed", F.trim(F.col("text")))
            .withColumn("upper_text", F.upper(F.col("trimmed")))
            .withColumn("lower_text", F.lower(F.col("trimmed")))
            .withColumn("prefix5", F.substring(F.col("trimmed"), 1, 5))
            .withColumn("digits_masked", F.regexp_replace(F.col("trimmed"), r"\d", "#"))
            .filter((F.length(F.col("trimmed")) > 0) & F.col("lower_text").rlike("a|e"))
            .select(
                "id",
                "trimmed",
                "upper_text",
                "lower_text",
                "prefix5",
                "digits_masked",
                "locale",
            )
        )
        rows = collect_sorted(transformed, ["id"])
        return finish(args, "strings", rows, spark=spark)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        spark.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
