# Requirement-to-evidence checklist

| Gate | Requirement | Status | Evidence |
|------|-------------|--------|----------|
| M0 | Host inventory + version lock + architecture | **PASS** | `STATUS.md`, `versions.lock.yaml`, `docs/compatibility.md`, `artifacts/logs/doctor-final.log` |
| M1 | Baseline smoke matching results | **PASS** | `artifacts/logs/smoke-baseline.log` |
| M1 | Native smoke + native plan evidence | **PASS** | `artifacts/logs/smoke-native.log`; manifests assert `Native Plan` |
| M2 | k3d cluster, RBAC, images imported | **PASS** | `artifacts/logs/local-up.log`, `k3d cluster list` → superspark |
| M2 | Executor-loss / cancellation live | **NOT RUN** | `scripts/bootstrap/k3d_integration.sh` |
| M3 | All tiny scenarios baseline/native | **PASS** | latest run manifests under `artifacts/reports/runs/`; `fallback_udf` = EXPECTED_FALLBACK |
| M4 | Optimization feature flag + tiny proof | **PASS** (correctness) / **inconclusive** (speedup on tiny) | optimized aggregate/filter/skew PASS; see `docs/decisions/0002-optimization-batch-policy.md` |
| M5 | Target K8s validation | **NOT RUN** | `configs/kubernetes.example.yaml` |
| M6 | YARN live pilot | **NOT RUN** | `deploy/yarn/`, inventory incomplete |
| M7 | Docs + package + STATUS | **PASS** | README, docs/*, `artifacts/packages/superspark-runtime-arm64.tar.gz` |
| Bootstrap | Colima + images + doctor | **PASS** | doctor 12/0/0; Colima running |
