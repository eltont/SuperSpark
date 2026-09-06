# SuperSpark

**CPU Spark SQL / DataFrame accelerator** built on [Apache Gluten](https://gluten.apache.org/) and its compatible [Velox](https://velox-lib.io/) backend.

SuperSpark packages a reproducible runtime, job runner, correctness/performance harness, and deployment profiles so existing Spark jobs can opt into native execution **without rewriting application code**.

| | |
|---|---|
| **License** | [Apache License 2.0](LICENSE) |
| **Third-party** | Inherits upstream licenses (Spark, Gluten, Velox, …) — see [NOTICE](NOTICE) |
| **Pinned stack** | Spark **3.5.5** · Gluten **1.6.0** · Velox IBM `dft-2026_02_06` · JDK **17** |

Track build status and gates in [`STATUS.md`](STATUS.md). Version pins live in [`versions.lock.yaml`](versions.lock.yaml).

---

## What you get

| Component | Role |
|-----------|------|
| Runtime images | Matched **baseline** (vanilla Spark) and **native** (Spark + Gluten/Velox) containers |
| Job runner | Submit the same app in `baseline` / `native` / `optimized` modes |
| Examples | Small PySpark scenarios under `examples/spark/` (no accelerator imports) |
| Harness | Fixtures, expected results, fair Docker benches, Markdown reports |
| Deploy profiles | Local Colima/k3d, Kubernetes example, YARN package + wrappers |

**Modes**

| Mode | Meaning |
|------|---------|
| `baseline` | Vanilla Spark |
| `native` | Upstream Gluten/Velox (no SuperSpark optimization) |
| `optimized` | Native + project feature flag (see `docs/decisions/0002-optimization-batch-policy.md`) |

Exactly one mode per run. Unsupported operators fall back to the JVM (or fail explicitly); they are not silently skipped from the suite.

---

## Do I need to change my Spark program?

**Usually no.** For supported batch SQL / DataFrame workloads:

- Keep using ordinary Spark APIs (`DataFrame`, Spark SQL).
- Do **not** import SuperSpark or Gluten APIs from application code.
- Select the engine via **image + spark-submit / SparkApplication config**.

| Change | Needed? |
|--------|---------|
| Rewrite DataFrame / SQL | No (supported ops) |
| Import Gluten / SuperSpark | No |
| Point at native runtime image / Gluten jar | **Yes** |
| Add Gluten Spark confs | **Yes** |
| Size executor **off-heap** + YARN/K8s overhead | **Yes** |
| Python / JVM UDFs | No rewrite — expect JVM fallback |

---

## Quick start (Apple Silicon laptop)

Developed and smoke-tested on macOS arm64 with **Colima** (Linux/arm64 containers). Official Gluten release jars are **amd64**; local ARM uses a documented interim aarch64 artifact (see `docs/compatibility.md`).

### Prerequisites

- Docker-compatible runtime (Colima recommended; Docker Desktop also works)
- JDK 17
- `kubectl`, `k3d` (for local Kubernetes profile)
- ~12+ GiB RAM for the Linux VM; leave headroom for macOS

Portable tools used during development lived under `~/.local` when system Homebrew was unavailable.

```bash
export PATH="$HOME/.local/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-$HOME/.local/opt/jdk-17}"
export DOCKER_HOST="${DOCKER_HOST:-unix://$HOME/.colima/default/docker.sock}"

# Start Colima if needed (example)
# colima start --arch aarch64 --cpu 4 --memory 12 --disk 60 --vm-type=vz
```

### Smoke

```bash
make doctor
make build ARCH=arm64          # builds baseline + native images
make smoke MODE=baseline
make smoke MODE=native         # asserts native plan evidence
make report
```

### Local Kubernetes (k3d)

```bash
make local-up                  # project cluster + RBAC + import images
./runner/bin/superspark scenarios --profile local --size tiny
make local-down                # removes project cluster; keeps artifacts/reports
```

### Fair small bench (both modes in Docker)

```bash
export SUPERSPARK_SCALE_MULT=100   # optional: scale synthesized row counts
python3 benchmarks/reporting/fair_bench.py \
  --workloads aggregate,joins --size small --warmup 1 --reps 5
# → artifacts/reports/bench-small-fair-latest.md
```

Tiny / small wall-clock on a laptop is often **startup-dominated**; treat it as a development signal, not production certification.

---

## Using SuperSpark with existing jobs

### Kubernetes

1. Build/push images for **worker architecture** (`amd64` for most cloud nodes):

   ```bash
   make build ARCH=amd64
   make package ARCH=amd64
   # docker tag / push to your registry
   ```

2. Create namespace, ServiceAccount, and RBAC (see `deploy/k3d/rbac.yaml`).

3. Submit with the **native** image and Gluten confs (job-local; do not change cluster defaults until ready):

```bash
spark-submit \
  --master k8s://https://<api> \
  --deploy-mode cluster \
  --conf spark.kubernetes.container.image=<registry>/superspark/spark-native:3.5.5-gluten1.6.0 \
  --conf spark.kubernetes.namespace=<ns> \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
  --conf spark.plugins=org.apache.gluten.GlutenPlugin \
  --conf spark.shuffle.manager=org.apache.spark.shuffle.sort.ColumnarShuffleManager \
  --conf spark.memory.offHeap.enabled=true \
  --conf spark.memory.offHeap.size=<e.g. 8g> \
  --conf spark.executor.memory=<heap> \
  --conf spark.executor.memoryOverhead=<heap overhead + off-heap room> \
  your-existing-app.py
```

Fill `configs/kubernetes.example.yaml`, then:

```bash
make validate-k8s CONFIG=configs/your-cluster.yaml
# SUPERSPARK_ALLOW_REMOTE_DEPLOY=1 make deploy-k8s CONFIG=...
```

**Rollback:** same app, **baseline** image, omit Gluten plugin confs.

### YARN / Hadoop (e.g. HDP 3.x)

Gluten **1.6.0** targets Spark **3.5.x**. Many HDP 3.x platforms still ship Spark **2.x** — you cannot drop this engine onto that Spark. Typical approach:

1. Inventory versions: `deploy/yarn/inventory.sh`
2. Provide a **side-by-side Spark 3.5.5** + matching **linux_amd64** Gluten jar (not the Mac aarch64 nightly)
3. Distribute jar/archive via HDFS / YARN localized resources
4. Submit with `deploy/yarn/submit-native.sh` (job-local conf only)
5. Pilot one job to a **new output path**; keep `submit-baseline.sh` for rollback

See [`docs/hadoop-migration.md`](docs/hadoop-migration.md).

### Required Gluten Spark settings (reference)

```
spark.plugins=org.apache.gluten.GlutenPlugin
spark.shuffle.manager=org.apache.spark.shuffle.sort.ColumnarShuffleManager
spark.memory.offHeap.enabled=true
spark.memory.offHeap.size=<size>
spark.driver.extraClassPath=/path/to/gluten-velox-bundle.jar
spark.executor.extraClassPath=/path/to/gluten-velox-bundle.jar
```

On JDK 17, also open modules for Netty/Arrow (set in the runner for container smokes), e.g. `--add-opens=java.base/java.nio=ALL-UNNAMED` and `-Dio.netty.tryReflectionSetAccessible=true`.

---

## Command reference

| Target | Purpose |
|--------|---------|
| `make doctor` | Read-only prerequisite / compatibility check |
| `make lock-versions` / `check-updates` | Version lock helpers |
| `make bootstrap` | Provision runtime, images, k3d, smoke |
| `make build ARCH=arm64\|amd64` | Build runtime images |
| `make smoke MODE=baseline\|native` | Deterministic filter/join/agg smoke |
| `make scenarios` / `scenario NAME=…` | Example suite |
| `make bench` / fair_bench.py | Performance trials |
| `make report` | Aggregate run manifests → Markdown/JSON |
| `make local-up` / `local-down` | Project k3d cluster |
| `make package ARCH=…` | Runtime archive |
| `make validate-k8s` / `deploy-k8s` | Remote K8s (explicit opt-in) |
| `make package-yarn` / `validate-yarn` | YARN packaging / preflight |

Logs are written under `artifacts/logs/`. Failures propagate nonzero exit codes.

---

## Repository layout

```text
README.md STATUS.md AGENTS.md Makefile versions.lock.yaml
LICENSE NOTICE
configs/          # local, k3d, kubernetes.example, yarn.example
runtime/docker/   # Dockerfiles (baseline, native, gluten-build)
accelerator/      # project optimization markers / future JVM hooks
runner/           # superspark CLI
examples/spark/   # runnable PySpark scenarios
benchmarks/       # generators, reporting, fair_bench
deploy/           # k3d, kubernetes, yarn
scripts/bootstrap/
docs/             # architecture, compatibility, ops, methodology
artifacts/        # local outputs (mostly gitignored)
```

---

## Documentation

| Doc | Topic |
|-----|--------|
| [`docs/architecture.md`](docs/architecture.md) | Execution path and components |
| [`docs/compatibility.md`](docs/compatibility.md) | Pins, exceptions, platforms |
| [`docs/development.md`](docs/development.md) | Local toolchain |
| [`docs/operations.md`](docs/operations.md) | Bootstrap, teardown, rollback |
| [`docs/performance-methodology.md`](docs/performance-methodology.md) | How we measure |
| [`docs/hadoop-migration.md`](docs/hadoop-migration.md) | YARN / HDFS path |
| [`docs/requirement-checklist.md`](docs/requirement-checklist.md) | Gate → evidence |
| [`examples/README.md`](examples/README.md) | Scenario catalog |

---

## Performance expectations

- **Correctness + native plan evidence** are validated locally (see `STATUS.md`).
- On a laptop, **tiny/small end-to-end times** often favor baseline because container/JVM/plugin startup dominates query time.
- Claim speedups only from fair trials (matched resources, warm-up + reps, compute-heavy data). Spec-oriented ≥1.5× suite wins need dedicated hardware and larger inputs.

---

## License

Copyright 2026 SuperSpark contributors.

Licensed under the **Apache License, Version 2.0** — see [LICENSE](LICENSE).

SuperSpark **inherits and redistributes** components under their own terms (notably Apache Spark, Apache Gluten, and Velox). Attribution and pointers are in [NOTICE](NOTICE). When you redistribute container images or YARN archives that embed those binaries, retain upstream `LICENSE` / `NOTICE` material from those releases.

---

## Contributing / agents

See [`AGENTS.md`](AGENTS.md) for milestone ownership and safety rules (one execution mode per run, no mid-bench version churn, no x86 emulation as performance evidence on Apple Silicon).
