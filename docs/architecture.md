# Architecture

## Execution path

```
Application (unchanged PySpark/SQL)
  → Spark planning / AQE
  → GlutenPlugin (Columnar)
  → Velox native operators
  → Spark task output / commit protocol
```

Spark retains scheduling, retries, shuffle coordination, and commit semantics. Native code runs inside executor processes.

## Project-owned components

| Component | Path | Role |
|-----------|------|------|
| Runtime builder | `runtime/`, `scripts/bootstrap/` | Pin, fetch, package, checksum images/jars |
| Job runner | `runner/` | Submit identical apps in baseline/native/optimized |
| Qualification | `accelerator/jvm/`, runner diagnostics | Plan coverage, fallback reasons |
| Optimization | `accelerator/` + configs | Feature-flagged conservative policy |
| Benchmark harness | `benchmarks/` | Generate, compare, report |
| Deployment | `deploy/` | k3d, K8s, YARN profiles |
| Airflow adaptor | `integrations/airflow/` | Mode-aware `SuperSparkSubmitOperator` + hook |

## Modes

Exactly one mode per run. `optimized` must not silently alias to `native`.

## Storage profiles

- **local-file:** shared mount for smoke
- **s3-dev:** MinIO in k3d for multi-pod
- **hdfs:** YARN target profile only

## Memory accounting (local k3d, ~24 GiB host)

Conservative starting point (tune after measurement):

- Colima VM: 12 GiB, 4 vCPU
- Driver pod: 2 GiB total
- 2× executors: 4 GiB total each (heap + off-heap + overhead)
- Leave headroom for macOS + Colima + k3d
