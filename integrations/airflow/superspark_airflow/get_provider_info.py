"""Airflow provider metadata for SuperSpark."""

from __future__ import annotations


def get_provider_info() -> dict:
    return {
        "package-name": "superspark-airflow",
        "name": "SuperSpark",
        "description": "Submit Spark SQL/DataFrame jobs through SuperSpark (baseline / native / optimized).",
        "versions": ["0.1.0"],
        "integrations": [
            {
                "integration-name": "SuperSpark",
                "external-doc-url": "https://gluten.apache.org/",
                "tags": ["apache", "spark", "gluten"],
            }
        ],
        "operators": [
            {
                "integration-name": "SuperSpark",
                "python-modules": ["superspark_airflow.operators.superspark_submit"],
            }
        ],
        "hooks": [
            {
                "integration-name": "SuperSpark",
                "python-modules": ["superspark_airflow.hooks.superspark"],
            }
        ],
        "connection-types": [
            {
                "hook-class-name": "superspark_airflow.hooks.superspark.SuperSparkHook",
                "connection-type": "superspark",
            }
        ],
    }
