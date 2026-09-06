# SuperSpark example scenarios

Self-contained PySpark programs under `spark/`. They do **not** import project accelerator code. Tiny fixtures are deterministic JSONL (`seed=42`); gold results live in `expected/`.

## Setup

```bash
# From repo root
export PATH="$HOME/.local/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-$HOME/.local/opt/jdk-17}"
source scripts/env.sh   # sets SPARK_HOME when bootstrapped

# Generate / refresh tiny fixtures + expected JSON
python3 examples/fixtures/generate_tiny.py
```

Run any scenario with `spark-submit` (or `python` if `pyspark` is on `PYTHONPATH`):

```bash
spark-submit examples/spark/<name>.py --size tiny --check-expected
```

Outputs land under `artifacts/scenario-out/<name>/<size>/result.json`.

## One command per scenario (tiny)

```bash
spark-submit examples/spark/filter_project.py --size tiny --check-expected
spark-submit examples/spark/joins.py --size tiny --check-expected
spark-submit examples/spark/aggregate.py --size tiny --check-expected
spark-submit examples/spark/sort_topk.py --size tiny --check-expected
spark-submit examples/spark/strings.py --size tiny --check-expected
spark-submit examples/spark/skew.py --size tiny --check-expected
spark-submit examples/spark/parquet_roundtrip.py --size tiny --check-expected
spark-submit examples/spark/small_files.py --size tiny --check-expected
spark-submit examples/spark/spill.py --size tiny --check-expected
spark-submit examples/spark/fallback_udf.py --size tiny --check-expected
spark-submit examples/spark/edge_cases.py --size tiny --check-expected
```

## Sizes

| Size | Behavior |
|------|----------|
| `tiny` | Read `examples/fixtures/tiny/*.jsonl`; compare to `examples/expected/*.json` when `--check-expected` |
| `small` | Synthesize ~50× tiny row counts in-process |
| `benchmark` | Synthesize ~2000× tiny row counts in-process |

Common flags: `--seed`, `--size`, `--profile`, `--input`, `--output`, `--master`, `--expected`, `--check-expected`, `--help`.

## SQL equivalents

`spark/sql/filter_project.sql`, `joins.sql`, and `aggregate.sql` mirror the DataFrame logic for the tiny fixtures.

## Fixtures

| File | Rows (tiny) | Used by |
|------|-------------|---------|
| `orders.jsonl` | 40 | filter_project, joins, aggregate, sort_topk, parquet_roundtrip, small_files, spill, fallback_udf |
| `customers.jsonl` | 10 | joins |
| `skew_events.jsonl` / `dim_keys.jsonl` | 100 / 8 | skew |
| `text_rows.jsonl` | 10 | strings |
| `edge_rows.jsonl` | 8 | edge_cases |
| `products.jsonl` / `line_items.jsonl` | 8 / ~80 | reserved for join extensions |

Portable JSONL avoids host parquet tooling; programs may still write parquet under `artifacts/scenario-out/` as part of materializing actions.
