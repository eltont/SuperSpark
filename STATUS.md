# Spark Accelerator — Status

**Last updated:** 2026-09-05  
**Execution mode:** Sequential lead agent (bounded research delegated once for Gluten/ARM pins)  
**Current milestone:** M7 handoff (local gates largely complete; remote NOT RUN)

## Summary

Working Gluten/Velox Spark accelerator on Apple Silicon via Colima Linux/arm64 containers. Pinned **Spark 3.5.5 + Gluten 1.6.0 + Velox IBM `dft-2026_02_06` + JDK 17**. Official Gluten release binaries are amd64-only; local native uses Apache nightly `linux_aarch64` interim jar (documented).

## Host notes

- ~24 GiB RAM (not 32), arm64 M4
- System Homebrew unusable (permissions); portable tools in `~/.local`
- Docker via Colima (no Docker Desktop)
- Interactive blocker cleared: Lima guestagent/templates installed under `~/.local`

## Milestone status

| Gate | Status | Evidence |
|------|--------|----------|
| M0 inventory/lock | **PASS** | `versions.lock.yaml`, `docs/compatibility.md`, `artifacts/logs/doctor.log` |
| M1 baseline smoke | **PASS** | `artifacts/logs/smoke-baseline.log` |
| M1 native smoke + plan evidence | **PASS** | `artifacts/logs/smoke-native.log`, run manifests with `Native Plan` hits |
| M2 k3d up / RBAC / images | **PASS** (partial) | `artifacts/logs/local-up.log`, `artifacts/kubeconfig-superspark.yaml` |
| M2 executor-loss / cancel live | **NOT RUN** | procedure in `scripts/bootstrap/k3d_integration.sh` (set `SUPERSPARK_RUN_EXEC_LOSS=1`) |
| M3 tiny scenarios baseline/native | **PASS** | all 11 workloads; `fallback_udf` native = EXPECTED_FALLBACK |
| M4 optimization flag | **IMPLEMENTED + measured tiny** | `docs/decisions/0002-optimization-batch-policy.md`; optimized aggregate/filter_project PASS; tiny timings are not performance certification |
| M5 target K8s | **NOT RUN** | `configs/kubernetes.example.yaml`, `deploy/kubernetes/` |
| M6 YARN live | **NOT RUN** | `deploy/yarn/`, inventory incomplete |
| M7 docs/package | **PASS** (local) | README, docs/*, `artifacts/packages/superspark-runtime-arm64.tar.gz` |

## Exact commands that worked

```bash
export PATH="$HOME/.local/bin:$PATH"
export JAVA_HOME="$HOME/.local/opt/jdk-17"
export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
make doctor
# Colima started during bootstrap; images built
make smoke MODE=baseline
make smoke MODE=native
make local-up
./runner/bin/superspark scenarios --profile local --size tiny
make report
```

## Fair small bench (2026-09-05 evening)

Both modes in linux/arm64 Docker; `SUPERSPARK_SCALE_MULT=100` → ~200k-row synthesize; 1 warmup + 5 alternating reps.

| Workload | Baseline median | Native median | Speedup |
|----------|----------------:|--------------:|--------:|
| aggregate | 4003 ms | 4744 ms | **0.84×** |
| joins | 3991 ms | 5840 ms | **0.68×** |

Evidence: `artifacts/reports/bench-small-fair-latest.md`. Native plans still execute; end-to-end wall clock remains startup-dominated (fresh container each trial). **No speedup proven on this laptop with this methodology.**

## Blockers / next actions

1. **Live executor-loss on k3d:** wire Spark-on-K8s multi-executor submit then run `SUPERSPARK_RUN_EXEC_LOSS=1`.
2. **ARM64 release-aligned jar:** rebuild from `runtime/docker/Dockerfile.gluten-build` on a ≥64GB ARM runner; replace interim nightly.
3. **Performance signal:** keep a warm Spark session and/or push to multi-million-row / Parquet-on-disk benches so compute dwarfs startup; or use dedicated Linux hardware.
4. **Remote K8s/YARN:** fill example configs; live pilots remain NOT RUN without cluster access.

## Agent handoffs

Sequential execution after one research subagent for version/ARM evidence. No conflicting parallel edits.
