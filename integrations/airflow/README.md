# SuperSpark ↔ Apache Airflow

Airflow adaptor that submits existing Spark SQL / DataFrame jobs in SuperSpark
modes **without changing application code**.

## Install

```bash
# From repo root (Airflow 2.7+ / 2.10 recommended)
pip install -e "integrations/airflow[dev]"
```

Provider entry point: `superspark-airflow` (connection type `superspark`).

## Modes

| Mode | Behavior |
|------|----------|
| `baseline` | Vanilla Spark conf |
| `native` | Gluten plugin + ColumnarShuffle + off-heap + jar on classpath |
| `optimized` | Native + `spark.superspark.optimize.enabled` batch policy |

Exactly **one mode per task**. Protected engine keys (`spark.plugins`, shuffle manager, extraClassPath, …) always win over `conf=` overrides.

## Quick example

```python
from superspark_airflow import SuperSparkSubmitOperator

native = SuperSparkSubmitOperator(
    task_id="agg_native",
    application="/path/to/job.py",
    mode="native",
    gluten_jar="/opt/gluten/gluten-velox-bundle.jar",
    off_heap_size="8g",
    native_image="registry/superspark/spark-native:3.5.5-gluten1.6.0",  # K8s
    conn_id="spark_default",
    conf={"spark.executor.memory": "4g"},
)
```

Optional connection `superspark_default` (type `superspark`) extra JSON:

```json
{
  "default_mode": "native",
  "gluten_jar": "/opt/gluten/gluten-velox-bundle.jar",
  "off_heap_size": "8g",
  "baseline_image": "registry/superspark/spark-baseline:3.5.5",
  "native_image": "registry/superspark/spark-native:3.5.5-gluten1.6.0",
  "spark_conn_id": "spark_default"
}
```

Then set `superspark_conn_id="superspark_default"` on the operator.

## Example DAG

See `example_dags/superspark_smoke_dag.py`.

## Tests

```bash
make test-airflow
# or
cd integrations/airflow && python -m pytest -q
```

Conf-only tests run without a scheduler. Operator / DagBag tests need Airflow + the Spark provider installed.
