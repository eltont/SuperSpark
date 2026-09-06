"""Hooks package."""

from __future__ import annotations

from typing import Any

__all__ = ["SuperSparkHook"]


def __getattr__(name: str) -> Any:
    if name == "SuperSparkHook":
        from superspark_airflow.hooks.superspark import SuperSparkHook

        return SuperSparkHook
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
