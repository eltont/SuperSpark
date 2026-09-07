# Agent guide — SuperSpark

## Mission

Deliver a working Gluten/Velox Spark accelerator with evidence at every milestone gate (M0–M7). Prefer measured results over scaffolding.

## Ownership

| Stream | Owns |
|--------|------|
| Lead | Architecture, version lock, STATUS.md, integration, gates |
| Runtime | Docker/Colima/k3d, images, bootstrap |
| Scenarios | `examples/spark/*`, fixtures, correctness |
| Engine | Native packaging, optimization flag, profiling |
| Review | Fairness of benches, deployment safety |

When delegation is unavailable, execute sequentially and record that in `STATUS.md`.

## Rules

1. Update `STATUS.md` after every milestone.
2. Never change `versions.lock.yaml` mid-benchmark.
3. Do not use x86 emulation timings as performance evidence on Apple Silicon.
4. Official Gluten release binaries are amd64-only; ARM64 uses interim nightly or source rebuild — document which.
5. One execution mode per run (`baseline` | `native` | `optimized`).
6. Serialize heavy native builds and benchmarks on this laptop.
7. Ask the user only when an external fact blocks safe progress.
8. **Git identity (hard rule):** every commit’s author **and** committer must be `eltont <6650713+eltont@users.noreply.github.com>`. Never commit as `Cursor Agent` / `cursoragent@cursor.com`. Do not rely on Cloud Agent defaults; before the first commit in a session set repo-local identity (`git config --local user.name eltont` and `user.email 6650713+eltont@users.noreply.github.com`) or pass equivalent `-c` / `GIT_AUTHOR_*` / `GIT_COMMITTER_*` overrides. Do not add a `Co-authored-by: Cursor Agent` trailer.

## Resource lock

Use `artifacts/resource.lock` (PID + purpose). Scripts must refuse to start a conflicting heavy job when the lock is held.
