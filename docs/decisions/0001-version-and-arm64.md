# ADR-0001: Version and ARM64 strategy

- Status: Accepted
- Date: 2026-09-05

## Context

Need a pinned Spark/Gluten/Velox stack on Apple Silicon with Linux containers. Official Gluten 1.6.0 binaries are amd64-only. Host has ~24 GiB RAM and no usable system Homebrew/Docker Desktop.

## Decision

1. Pin Spark **3.5.5**, Gluten **1.6.0**, Velox IBM **`dft-2026_02_06`**, JDK **17**.
2. Use Colima + portable CLI tools under `~/.local`.
3. For ARM64 native smoke, use the Apache nightly `linux_aarch64` Gluten jar as an **interim** artifact, with a Docker source-build recipe for reproducible release-aligned rebuilds.
4. Do not use amd64 emulation for performance claims.

## Consequences

- M1 can proceed without a 64 GiB native compile on the laptop.
- Reports must label interim nightly vs release-built ARM jars.
- `make build ARCH=arm64` attempts source rebuild with low `NUM_THREADS`; may require remote runner.
