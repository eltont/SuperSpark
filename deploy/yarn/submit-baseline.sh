#!/usr/bin/env bash
# Submit baseline Spark job on YARN without changing cluster defaults.
set -euo pipefail
: "${SPARK_HOME:?}"
exec "$SPARK_HOME/bin/spark-submit" --master yarn --deploy-mode cluster "$@"
