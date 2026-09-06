"""SuperSpark Airflow provider package."""

from __future__ import annotations

__version__ = "0.1.0"

from superspark_airflow.conf import MODES, build_mode_conf, merge_spark_conf
from superspark_airflow.operators.superspark_submit import SuperSparkSubmitOperator

__all__ = [
    "MODES",
    "SuperSparkSubmitOperator",
    "build_mode_conf",
    "merge_spark_conf",
    "__version__",
]
