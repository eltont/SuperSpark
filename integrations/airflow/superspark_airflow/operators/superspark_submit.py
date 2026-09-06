"""Airflow operator that submits Spark apps in a SuperSpark execution mode."""

from __future__ import annotations

from typing import Any, Sequence

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from superspark_airflow.conf import (
    apply_kubernetes_image,
    assert_native_evidence,
    build_mode_conf,
    merge_spark_conf,
    validate_mode,
)
from superspark_airflow.hooks.superspark import SuperSparkHook


class SuperSparkSubmitOperator(SparkSubmitOperator):
    """SparkSubmitOperator with SuperSpark mode-aware Gluten/Velox conf.

    Application code is unchanged. Select engine with ``mode``:

    - ``baseline`` — vanilla Spark
    - ``native`` — Gluten/Velox
    - ``optimized`` — native + SuperSpark optimization flag

    Exactly one mode per task. Protected engine conf keys from the mode cannot
    be overridden by ``conf=`` (prevents accidental Gluten drop).
    """

    template_fields: Sequence[str] = (
        *SparkSubmitOperator.template_fields,
        "mode",
        "gluten_jar",
        "off_heap_size",
        "baseline_image",
        "native_image",
        "superspark_conn_id",
    )
    ui_color = "#1B4F72"

    def __init__(
        self,
        *,
        mode: str = "baseline",
        gluten_jar: str | None = None,
        off_heap_size: str = "1536m",
        baseline_image: str | None = None,
        native_image: str | None = None,
        superspark_conn_id: str | None = None,
        require_native_evidence: bool = False,
        conf: dict[str, Any] | None = None,
        conn_id: str = "spark_default",
        name: str = "superspark",
        **kwargs: Any,
    ) -> None:
        self.mode = validate_mode(mode)
        self.gluten_jar = gluten_jar
        self.off_heap_size = off_heap_size
        self.baseline_image = baseline_image
        self.native_image = native_image
        self.superspark_conn_id = superspark_conn_id
        self.require_native_evidence = require_native_evidence
        self._user_conf = dict(conf or {})
        self._resolved_conf: dict[str, str] | None = None

        # Placeholder conf; final merge happens in execute after connection resolve.
        super().__init__(conf=dict(self._user_conf), conn_id=conn_id, name=name, **kwargs)

    def _resolve_from_connection(self) -> None:
        if not self.superspark_conn_id:
            return
        hook = SuperSparkHook(superspark_conn_id=self.superspark_conn_id)
        resolved = hook.resolve_defaults(
            mode=self.mode,
            gluten_jar=self.gluten_jar,
            off_heap_size=self.off_heap_size,
            baseline_image=self.baseline_image,
            native_image=self.native_image,
            spark_conn_id=self._conn_id,
        )
        self.mode = validate_mode(resolved["mode"])
        self.gluten_jar = resolved["gluten_jar"]
        self.off_heap_size = resolved["off_heap_size"]
        self.baseline_image = resolved["baseline_image"]
        self.native_image = resolved["native_image"]
        if resolved.get("spark_conn_id"):
            self._conn_id = resolved["spark_conn_id"]

    def build_superspark_conf(self) -> dict[str, str]:
        """Build final Spark conf for this task (public for tests / dry-run)."""
        mode_conf = build_mode_conf(
            self.mode,
            gluten_jar=self.gluten_jar,
            off_heap_size=self.off_heap_size,
        )
        merged = merge_spark_conf(mode_conf, self._user_conf)
        apply_kubernetes_image(
            merged,
            self.mode,
            baseline_image=self.baseline_image,
            native_image=self.native_image,
        )
        self._resolved_conf = merged
        return merged

    def execute(self, context: Any) -> Any:
        self._resolve_from_connection()
        final_conf = self.build_superspark_conf()
        self.conf = final_conf
        # SparkSubmitOperator / hook read self._conf in some versions
        if hasattr(self, "_conf"):
            self._conf = final_conf

        self.log.info(
            "SuperSpark mode=%s gluten_jar=%s protected_engine=on",
            self.mode,
            self.gluten_jar,
        )
        result = super().execute(context)

        if self.require_native_evidence and self.mode in ("native", "optimized"):
            # Prefer hook-captured output when available; otherwise skip soft.
            log_blob = ""
            hook = getattr(self, "_hook", None)
            if hook is not None:
                for attr in ("_driver_status", "_yarn_application_id", "spark_submit_log"):
                    val = getattr(hook, attr, None)
                    if isinstance(val, str):
                        log_blob += val + "\n"
            # Also allow XCom / context push from custom wrappers
            ti = context.get("ti") if isinstance(context, dict) else None
            if ti is not None:
                pushed = ti.xcom_pull(task_ids=self.task_id, key="spark_submit_log")
                if isinstance(pushed, str):
                    log_blob += pushed
            if log_blob:
                evidence = assert_native_evidence(log_blob)
                if not evidence["native_execution_asserted"]:
                    raise RuntimeError(
                        "SuperSpark native/optimized mode completed without native plan evidence "
                        f"(mode={self.mode})"
                    )
                self.log.info(
                    "Native plan evidence OK: substantial_nodes=%s",
                    evidence["substantial_native_nodes"],
                )
            else:
                self.log.warning(
                    "require_native_evidence=True but no spark-submit log was available to scan"
                )
        return result
