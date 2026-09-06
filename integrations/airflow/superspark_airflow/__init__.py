"""SuperSpark Airflow provider package."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"

from superspark_airflow.conf import MODES, build_mode_conf, merge_spark_conf

__all__ = [
    "MODES",
    "SuperSparkSubmitOperator",
    "build_mode_conf",
    "merge_spark_conf",
    "__version__",
]


def __getattr__(name: str) -> Any:
    # Lazy: avoid importing Airflow when only conf helpers are needed.
    if name == "SuperSparkSubmitOperator":
        from superspark_airflow.operators.superspark_submit import SuperSparkSubmitOperator

        return SuperSparkSubmitOperator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
