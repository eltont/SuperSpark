#!/usr/bin/env bash
# Submit Gluten-accelerated Spark job on YARN (job-local conf only).
set -euo pipefail
: "${SPARK_HOME:?}"
: "${GLUTEN_JAR:?}"
: "${GLUTEN_ARCHIVE:?}"  # hdfs or yarn distributed cache archive containing native libs/jar
exec "$SPARK_HOME/bin/spark-submit" --master yarn --deploy-mode cluster \
  --conf spark.plugins=org.apache.gluten.GlutenPlugin \
  --conf spark.shuffle.manager=org.apache.spark.shuffle.sort.ColumnarShuffleManager \
  --conf spark.memory.offHeap.enabled=true \
  --conf "spark.driver.extraClassPath=$GLUTEN_JAR" \
  --conf "spark.executor.extraClassPath=$GLUTEN_JAR" \
  --files "$GLUTEN_JAR" \
  "$@"
