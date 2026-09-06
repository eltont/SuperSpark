package com.superspark.accelerator

/** Marker + documentation for optimized-mode Spark configs.
  * Actual policy is applied via spark-submit conf in the runner (Gluten-supported settings).
  * This module exists for future JVM extension hooks without inventing unsupported APIs.
  */
object OptimizeFlags {
  val EnabledKey = "spark.superspark.optimize.enabled"
  val MaxBatchSizeKey = "spark.gluten.sql.columnar.maxBatchSize"
}
