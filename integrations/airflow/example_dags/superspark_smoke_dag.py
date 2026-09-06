"""Example DAG: SuperSpark smoke workloads via Airflow.

Point AIRFLOW__CORE__DAGS_FOLDER (or a symlink) at this directory after
``pip install -e integrations/airflow``. Configure a Spark connection
(``spark_default``) and optionally ``superspark_default`` with gluten_jar.
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG

from superspark_airflow import SuperSparkSubmitOperator

ROOT = os.environ.get("SUPERSPARK_ROOT", "/opt/superspark")
GLUTEN_JAR = os.environ.get(
    "SUPERSPARK_GLUTEN_JAR",
    f"{ROOT}/artifacts/cache/gluten-velox-bundle-spark3.5_2.12-linux_aarch64-1.6.0-SNAPSHOT.jar",
)
APP = f"{ROOT}/examples/spark/filter_project.py"
APP_ARGS = [
    "--size",
    "tiny",
    "--seed",
    "42",
    "--output",
    f"{ROOT}/artifacts/data/outputs/airflow-filter",
    "--input",
    f"{ROOT}/examples/fixtures/tiny",
    "--expected",
    f"{ROOT}/examples/expected/filter_project.json",
    "--check-expected",
]

with DAG(
    dag_id="superspark_smoke",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["superspark", "smoke"],
) as dag:
    baseline = SuperSparkSubmitOperator(
        task_id="filter_project_baseline",
        application=APP,
        application_args=APP_ARGS,
        mode="baseline",
        conn_id="spark_default",
        verbose=True,
    )

    native = SuperSparkSubmitOperator(
        task_id="filter_project_native",
        application=APP,
        application_args=APP_ARGS,
        mode="native",
        gluten_jar=GLUTEN_JAR,
        conn_id="spark_default",
        verbose=True,
    )

    baseline >> native
