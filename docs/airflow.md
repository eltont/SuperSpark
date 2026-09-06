# Apache Airflow adaptor

SuperSpark ships an optional Airflow provider under `integrations/airflow/`.

## Purpose

Schedule existing Spark SQL / DataFrame jobs through Airflow while selecting
SuperSpark execution mode (`baseline` | `native` | `optimized`) via operator
parameters — **no application rewrite**.

## Components

| Piece | Role |
|-------|------|
| `SuperSparkSubmitOperator` | Extends Airflow `SparkSubmitOperator` with mode-aware Gluten conf |
| `SuperSparkHook` | Connection type `superspark` for jar / image defaults |
| `build_mode_conf` / `merge_spark_conf` | Shared conf builder (protected engine keys) |
| `example_dags/superspark_smoke_dag.py` | Smoke DAG (baseline → native) |

## Install

```bash
pip install -e "integrations/airflow[dev]"
make test-airflow
```

See `integrations/airflow/README.md` for connection extras and DAG usage.

## Rollback

Use a task with `mode="baseline"` (or omit Gluten jar / native image) — same
application path as the CLI runner rollback story.
