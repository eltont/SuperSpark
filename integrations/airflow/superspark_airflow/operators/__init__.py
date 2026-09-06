"""Operators package."""

from __future__ import annotations

from typing import Any

__all__ = ["SuperSparkSubmitOperator"]


def __getattr__(name: str) -> Any:
    if name == "SuperSparkSubmitOperator":
        from superspark_airflow.operators.superspark_submit import SuperSparkSubmitOperator

        return SuperSparkSubmitOperator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
