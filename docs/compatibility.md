# Compatibility matrix

**Access date:** 2026-09-05 (local) / 2026-09-06 UTC

## Selected combination

| Component | Selected | Latest available at resolve | Compatible? | Notes |
|-----------|----------|-----------------------------|-------------|-------|
| Gluten | 1.6.0 (`v1.6.0` / `89718982`) | 1.6.0 | yes | Latest stable release |
| Spark | 3.5.5 | 4.2.0 / 3.5.9 | partial | Newest Spark unsupported by Gluten 1.6.0; 3.5.5 is Gluten's Spark 3.5 pin |
| Scala | 2.12 | 2.13 (Spark 4) | yes for 3.5.5 | |
| JDK | 17 (Temurin) | 21+ | yes | Gluten 1.6.0: JDK 8/17 |
| Velox | IBM `dft-2026_02_06` @ `f247a8e9…` | newer upstream exists | yes | Must use Gluten fork pin |
| Base image | `eclipse-temurin:17-jdk-jammy` | floating tag until digest pinned at build | yes | Digests recorded in build manifests |
| k3d | v5.8.3 | v5.9.0 | yes | Pinned for reproducibility |
| kubectl | v1.32.2 | newer patch | yes | |
| Colima | v0.8.1 | newer | yes | Docker Desktop not installed; no sudo for system brew |

## Evidence URLs

- https://gluten.apache.org/downloads/ (accessed 2026-09-06)
- https://downloads.apache.org/gluten/1.6.0/
- https://github.com/apache/gluten/releases/tag/v1.6.0
- https://raw.githubusercontent.com/apache/gluten/v1.6.0/docs/get-started/Velox.md
- https://raw.githubusercontent.com/apache/gluten/v1.6.0/ep/build-velox/src/get-velox.sh
- https://archive.apache.org/dist/spark/spark-3.5.5/
- https://nightlies.apache.org/gluten/nightly-release-jdk17/
- https://k3d.io/stable/

## Exceptions (explicit)

1. **Spark not latest:** Latest Spark is 4.2.0; Gluten 1.6.0 tops out at Spark 4.0.x. Chose **3.5.5** (documented Gluten Spark 3.5 pin, Scala 2.12, aarch64 nightly jar available). Upgrade path: Gluten release that lists Spark 3.5.9/4.0.x/4.1.x → re-lock → rerun gates.

2. **No official ARM64 Gluten binary:** Release tarballs are CentOS7 x86_64 static. Local ARM64 strategy: (a) interim nightly `linux_aarch64` jar for smoke; (b) `runtime/docker/Dockerfile.gluten-build` source rebuild with `CPU_TARGET=aarch64` and `NUM_THREADS=2` on ≥64GB preferred (host has ~24GB — remote ARM builder recommended for full rebuild).

3. **Docker Desktop absent:** Host lacks Docker.app and cannot use system Homebrew (`/opt/homebrew` owned by another user, mode 700; sudo password required). Using portable `~/.local` binaries + Colima/Lima.

4. **Host RAM ~24 GiB** (not 32): Adjust local executor budgets downward vs. the build-spec suggestion.

## Platform support

| Platform | Status |
|----------|--------|
| linux/arm64 containers on Apple Silicon (Colima) | development target |
| linux/amd64 target K8s | package path; live validation NOT RUN without cluster |
| YARN/Hadoop 3.x | package + inventory; live pilot NOT RUN without cluster |
| Native macOS Spark+Gluten | out of scope (Linux containers only) |
