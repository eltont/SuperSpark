"""Operator / hook tests against installed Airflow + Spark provider."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("airflow")
pytest.importorskip("airflow.providers.apache.spark")

from airflow import DAG  # noqa: E402
from airflow.models.connection import Connection  # noqa: E402
from airflow.models.dagbag import DagBag  # noqa: E402
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator  # noqa: E402

from superspark_airflow.hooks.superspark import SuperSparkHook  # noqa: E402
from superspark_airflow.operators.superspark_submit import SuperSparkSubmitOperator  # noqa: E402

EXAMPLE_DAGS = Path(__file__).resolve().parents[1] / "example_dags"


def _dag() -> DAG:
    return DAG(
        dag_id="superspark_unit",
        start_date=datetime(2026, 1, 1),
        schedule=None,
        catchup=False,
    )


def test_operator_builds_native_conf():
    with _dag():
        op = SuperSparkSubmitOperator(
            task_id="t1",
            application="/apps/job.py",
            mode="native",
            gluten_jar="/opt/gluten/bundle.jar",
            conf={"spark.executor.memory": "2g", "spark.plugins": "should.not.win"},
        )
    conf = op.build_superspark_conf()
    assert conf["spark.plugins"] == "org.apache.gluten.GlutenPlugin"
    assert conf["spark.executor.memory"] == "2g"
    assert conf["spark.driver.extraClassPath"] == "/opt/gluten/bundle.jar"


def test_operator_baseline_no_gluten():
    with _dag():
        op = SuperSparkSubmitOperator(
            task_id="t2",
            application="/apps/job.py",
            mode="baseline",
        )
    conf = op.build_superspark_conf()
    assert "spark.plugins" not in conf


def test_operator_sets_k8s_image():
    with _dag():
        op = SuperSparkSubmitOperator(
            task_id="t3",
            application="/apps/job.py",
            mode="optimized",
            gluten_jar="/j.jar",
            native_image="reg/superspark/spark-native:x",
            baseline_image="reg/superspark/spark-baseline:x",
        )
    conf = op.build_superspark_conf()
    assert conf["spark.kubernetes.container.image"] == "reg/superspark/spark-native:x"
    assert conf["spark.superspark.optimize.enabled"] == "true"


def test_hook_resolve_defaults():
    extra = {
        "default_mode": "native",
        "gluten_jar": "/from/conn.jar",
        "off_heap_size": "4g",
        "native_image": "img-native",
        "spark_conn_id": "spark_yarn",
    }
    conn = Connection(conn_id="superspark_default", conn_type="superspark", extra=json.dumps(extra))
    with patch.object(SuperSparkHook, "get_connection", return_value=conn):
        hook = SuperSparkHook("superspark_default")
        resolved = hook.resolve_defaults(mode=None, gluten_jar=None)
    assert resolved["mode"] == "native"
    assert resolved["gluten_jar"] == "/from/conn.jar"
    assert resolved["off_heap_size"] == "4g"
    assert resolved["spark_conn_id"] == "spark_yarn"


def test_execute_applies_conf_before_submit():
    with _dag():
        op = SuperSparkSubmitOperator(
            task_id="t4",
            application="/apps/job.py",
            mode="native",
            gluten_jar="/opt/g.jar",
        )
    captured: dict = {}

    def fake_execute(self, context):  # noqa: ANN001
        captured["conf"] = dict(self.conf)
        return "ok"

    with patch.object(SparkSubmitOperator, "execute", fake_execute):
        result = op.execute(context={})
    assert result == "ok"
    assert captured["conf"]["spark.plugins"] == "org.apache.gluten.GlutenPlugin"


def test_require_native_evidence_fails_without_markers():
    with _dag():
        op = SuperSparkSubmitOperator(
            task_id="t5",
            application="/apps/job.py",
            mode="native",
            gluten_jar="/opt/g.jar",
            require_native_evidence=True,
        )
    op._hook = MagicMock()
    op._hook.spark_submit_log = "job finished with no transformers"

    with patch.object(SparkSubmitOperator, "execute", return_value=None):
        with pytest.raises(RuntimeError, match="without native plan evidence"):
            op.execute(context={})


def test_dag_example_imports():
    bag = DagBag(
        dag_folder=str(EXAMPLE_DAGS),
        include_examples=False,
        safe_mode=False,
    )
    assert not bag.import_errors, bag.import_errors
    assert "superspark_smoke" in bag.dags
    dag = bag.dags["superspark_smoke"]
    assert set(dag.task_ids) == {"filter_project_baseline", "filter_project_native"}
