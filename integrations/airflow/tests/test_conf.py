"""Unit tests for SuperSpark mode conf (no Airflow runtime required)."""

from __future__ import annotations

import pytest

from superspark_airflow.conf import (
    PROTECTED_KEYS,
    assert_native_evidence,
    apply_kubernetes_image,
    build_mode_conf,
    merge_spark_conf,
    validate_mode,
)


def test_validate_mode_rejects_unknown():
    with pytest.raises(ValueError, match="unknown SuperSpark mode"):
        validate_mode("turbo")


def test_baseline_omits_gluten():
    conf = build_mode_conf("baseline")
    assert "spark.plugins" not in conf
    assert conf["spark.sql.adaptive.enabled"] == "true"


def test_native_requires_jar():
    with pytest.raises(ValueError, match="requires gluten_jar"):
        build_mode_conf("native")


def test_native_conf_includes_gluten():
    conf = build_mode_conf("native", gluten_jar="/opt/gluten/bundle.jar", off_heap_size="2g")
    assert conf["spark.plugins"] == "org.apache.gluten.GlutenPlugin"
    assert conf["spark.shuffle.manager"] == "org.apache.spark.shuffle.sort.ColumnarShuffleManager"
    assert conf["spark.memory.offHeap.enabled"] == "true"
    assert conf["spark.memory.offHeap.size"] == "2g"
    assert conf["spark.driver.extraClassPath"] == "/opt/gluten/bundle.jar"
    assert conf["spark.executor.extraClassPath"] == "/opt/gluten/bundle.jar"
    assert "spark.superspark.optimize.enabled" not in conf


def test_optimized_sets_flag():
    conf = build_mode_conf("optimized", gluten_jar="/j.jar")
    assert conf["spark.superspark.optimize.enabled"] == "true"
    assert conf["spark.gluten.sql.columnar.maxBatchSize"] == "8192"


def test_merge_protects_engine_keys():
    mode = build_mode_conf("native", gluten_jar="/j.jar")
    user = {
        "spark.plugins": "com.evil.DropGluten",
        "spark.executor.memory": "4g",
        "spark.sql.shuffle.partitions": "8",
    }
    merged = merge_spark_conf(mode, user)
    assert merged["spark.plugins"] == "org.apache.gluten.GlutenPlugin"
    assert merged["spark.executor.memory"] == "4g"
    assert merged["spark.sql.shuffle.partitions"] == "8"
    assert PROTECTED_KEYS  # sanity


def test_merge_unprotected_allows_override():
    mode = build_mode_conf("native", gluten_jar="/j.jar")
    merged = merge_spark_conf(mode, {"spark.plugins": "x"}, protect_engine_keys=False)
    assert merged["spark.plugins"] == "x"


def test_kubernetes_image_by_mode():
    conf: dict[str, str] = {}
    apply_kubernetes_image(
        conf,
        "native",
        baseline_image="superspark/spark-baseline:3.5.5",
        native_image="superspark/spark-native:3.5.5-gluten1.6.0",
    )
    assert conf["spark.kubernetes.container.image"] == "superspark/spark-native:3.5.5-gluten1.6.0"

    conf2: dict[str, str] = {}
    apply_kubernetes_image(
        conf2,
        "baseline",
        baseline_image="superspark/spark-baseline:3.5.5",
        native_image="superspark/spark-native:3.5.5-gluten1.6.0",
    )
    assert conf2["spark.kubernetes.container.image"] == "superspark/spark-baseline:3.5.5"


def test_native_evidence():
    ok = assert_native_evidence("Plan: ProjectExecTransformer and Native Plan shown")
    assert ok["native_execution_asserted"] is True
    bad = assert_native_evidence("only JVM WholeStageCodegenExec")
    assert bad["native_execution_asserted"] is False
