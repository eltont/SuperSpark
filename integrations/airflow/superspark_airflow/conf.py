"""Mode → Spark conf for SuperSpark Airflow tasks.

Mirrors runner semantics: exactly one mode per task
(`baseline` | `native` | `optimized`). Application code stays unchanged;
engine selection is conf (+ optional Kubernetes image).
"""

from __future__ import annotations

from typing import Mapping, MutableMapping

MODES = ("baseline", "native", "optimized")

# Keys that define engine identity; mode always wins over user conf.
PROTECTED_KEYS = frozenset(
    {
        "spark.plugins",
        "spark.shuffle.manager",
        "spark.memory.offHeap.enabled",
        "spark.driver.extraClassPath",
        "spark.executor.extraClassPath",
        "spark.superspark.optimize.enabled",
    }
)

DEFAULT_JDK17_OPENS = (
    "-Dio.netty.tryReflectionSetAccessible=true "
    "--add-opens=java.base/java.nio=ALL-UNNAMED "
    "--add-opens=java.base/java.lang=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens=java.base/java.io=ALL-UNNAMED "
    "--add-opens=java.base/java.net=ALL-UNNAMED "
    "--add-opens=java.base/java.nio.file=ALL-UNNAMED "
    "--add-opens=java.base/java.security=ALL-UNNAMED "
    "--add-opens=java.base/java.util=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
    "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
    "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED "
    "--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED"
)

NATIVE_EVIDENCE_PATTERNS = (
    "ProjectExecTransformer",
    "FilterExecTransformer",
    "HashAggregateExecTransformer",
    "ShuffledHashJoinExecTransformer",
    "SortMergeJoinExecTransformer",
    "WholeStageCodegenTransformer",
    "VeloxColumnarToRowExec",
    "BatchScanExecTransformer",
    "FileSourceScanExecTransformer",
    "ColumnarToRowExec",
    "Native Plan",
    "GlutenPlugin",
)


def validate_mode(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"unknown SuperSpark mode {mode!r}; expected one of {MODES}")
    return mode


def build_mode_conf(
    mode: str,
    *,
    gluten_jar: str | None = None,
    off_heap_size: str = "1536m",
    extra_java_options: str | None = None,
    inject_native_plan_explain: bool = True,
) -> dict[str, str]:
    """Return Spark conf dict for the given SuperSpark mode.

    ``baseline`` omits Gluten. ``native`` / ``optimized`` require ``gluten_jar``.
    """
    mode = validate_mode(mode)
    conf: dict[str, str] = {
        "spark.sql.adaptive.enabled": "true",
    }
    if mode == "baseline":
        return conf

    if not gluten_jar:
        raise ValueError(f"mode {mode!r} requires gluten_jar (path or URI to Gluten/Velox bundle)")

    jopts = extra_java_options if extra_java_options is not None else DEFAULT_JDK17_OPENS
    conf.update(
        {
            "spark.plugins": "org.apache.gluten.GlutenPlugin",
            "spark.shuffle.manager": "org.apache.spark.shuffle.sort.ColumnarShuffleManager",
            "spark.memory.offHeap.enabled": "true",
            "spark.memory.offHeap.size": off_heap_size,
            "spark.driver.extraClassPath": gluten_jar,
            "spark.executor.extraClassPath": gluten_jar,
            "spark.driver.extraJavaOptions": jopts,
            "spark.executor.extraJavaOptions": jopts,
            "spark.gluten.sql.columnar.backend.velox.showTaskMetricsWhenFinished": "true",
        }
    )
    if inject_native_plan_explain:
        conf["spark.gluten.sql.injectNativePlanStringToExplain"] = "true"

    if mode == "optimized":
        conf.update(
            {
                "spark.superspark.optimize.enabled": "true",
                "spark.gluten.sql.columnar.maxBatchSize": "8192",
                "spark.gluten.memory.dynamic.offHeap.sizing.enabled": "true",
            }
        )
    return conf


def apply_kubernetes_image(
    conf: MutableMapping[str, str],
    mode: str,
    *,
    baseline_image: str | None = None,
    native_image: str | None = None,
) -> MutableMapping[str, str]:
    """Set ``spark.kubernetes.container.image`` from mode when images are provided."""
    mode = validate_mode(mode)
    if mode == "baseline":
        if baseline_image:
            conf["spark.kubernetes.container.image"] = baseline_image
    elif native_image:
        conf["spark.kubernetes.container.image"] = native_image
    return conf


def merge_spark_conf(
    mode_conf: Mapping[str, str],
    user_conf: Mapping[str, str] | None = None,
    *,
    protect_engine_keys: bool = True,
) -> dict[str, str]:
    """Merge user conf with mode conf.

    By default, protected engine keys from ``mode_conf`` always win so a task
    cannot accidentally drop Gluten while claiming ``native`` / ``optimized``.
    """
    user = dict(user_conf or {})
    base = dict(mode_conf)
    if not protect_engine_keys:
        merged = {**base, **user}
        return {str(k): str(v) for k, v in merged.items()}

    for key, value in user.items():
        if key in PROTECTED_KEYS and key in base and str(base[key]) != str(value):
            continue
        base[key] = str(value)
    return {str(k): str(v) for k, v in base.items()}


def assert_native_evidence(text: str) -> dict:
    """Scan spark-submit / driver logs for Gluten native plan markers."""
    hits = {pat: text.count(pat) for pat in NATIVE_EVIDENCE_PATTERNS}
    substantial_keys = (
        "ProjectExecTransformer",
        "FilterExecTransformer",
        "HashAggregateExecTransformer",
        "ShuffledHashJoinExecTransformer",
        "SortMergeJoinExecTransformer",
        "WholeStageCodegenTransformer",
        "VeloxColumnarToRowExec",
        "BatchScanExecTransformer",
        "FileSourceScanExecTransformer",
        "Native Plan",
    )
    substantial = sum(hits.get(k, 0) for k in substantial_keys)
    return {
        "hits": hits,
        "substantial_native_nodes": substantial,
        "native_execution_asserted": substantial > 0,
    }
