"""SuperSpark connection hook — stores Gluten jar / image defaults in Airflow Connections."""

from __future__ import annotations

import json
from typing import Any

from airflow.hooks.base import BaseHook


class SuperSparkHook(BaseHook):
    """Connection type ``superspark``.

    Extra JSON fields (all optional):

    - ``default_mode``: baseline | native | optimized
    - ``gluten_jar``: path or URI to Gluten/Velox bundle jar
    - ``off_heap_size``: e.g. ``1536m``
    - ``baseline_image`` / ``native_image``: Kubernetes container images
    - ``spark_conn_id``: underlying SparkSubmit connection id (default ``spark_default``)
    """

    conn_type = "superspark"
    hook_name = "SuperSpark"
    default_conn_name = "superspark_default"

    def __init__(self, superspark_conn_id: str = default_conn_name) -> None:
        super().__init__()
        self.superspark_conn_id = superspark_conn_id

    def get_conn(self) -> Any:
        return self.get_connection(self.superspark_conn_id)

    def get_extras(self) -> dict[str, Any]:
        conn = self.get_conn()
        if not conn.extra:
            return {}
        try:
            data = json.loads(conn.extra)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Connection {self.superspark_conn_id} extra is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Connection {self.superspark_conn_id} extra must be a JSON object")
        return data

    def resolve_defaults(
        self,
        *,
        mode: str | None = None,
        gluten_jar: str | None = None,
        off_heap_size: str | None = None,
        baseline_image: str | None = None,
        native_image: str | None = None,
        spark_conn_id: str | None = None,
    ) -> dict[str, Any]:
        """Fill missing operator kwargs from the connection extra."""
        extra = self.get_extras()
        return {
            "mode": mode or extra.get("default_mode") or "baseline",
            "gluten_jar": gluten_jar if gluten_jar is not None else extra.get("gluten_jar"),
            "off_heap_size": off_heap_size or extra.get("off_heap_size") or "1536m",
            "baseline_image": baseline_image if baseline_image is not None else extra.get("baseline_image"),
            "native_image": native_image if native_image is not None else extra.get("native_image"),
            "spark_conn_id": spark_conn_id or extra.get("spark_conn_id") or "spark_default",
        }
