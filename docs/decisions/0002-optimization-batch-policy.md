# SuperSpark optimization: conservative memory/batch policy

## Hypothesis

Unmodified Gluten/Velox on small-to-medium local workloads often uses default columnar batch sizes and static off-heap sizing that under-utilize memory or cause excess row/native transitions under pressure. A conservative policy enabling dynamic off-heap sizing and a bounded batch size (8192) should reduce elapsed time on aggregation/join workloads without changing results.

## Feature flag

- Enabled when mode=`optimized` (runner sets configs) AND `artifacts/OPTIMIZATION_ENABLED` exists for suite inclusion.
- Disable: remove the flag file or run `MODE=native`.

## Affected workloads

Primary: `aggregate`, `joins`, `filter_project`
Held-out: `skew` (detect overfitting)

## Implementation

No custom native operators in v1. Uses Gluten-supported settings:

- `spark.superspark.optimize.enabled=true` (marker)
- `spark.gluten.sql.columnar.maxBatchSize=8192`
- `spark.gluten.memory.dynamic.offHeap.sizing.enabled=true`

## Proof requirement

Compare baseline / native / optimized with identical inputs; report medians and correctness. If no attributable improvement beyond noise, leave disabled and record unsuccessful experiment.
