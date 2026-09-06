# Performance methodology

See build spec §11. Modes: baseline / native / optimized.

- Warm-up: at least one; five measured reps when feasible for bench profile.
- Measure application_ms and action_ms; force materialization.
- Do not use x86 emulation timings on Apple Silicon as certification.
- Tiny scenarios: correctness only (no speedup gate).
- Manifest schema implemented in `runner/python/superspark_runner.py` and aggregated by `benchmarks/reporting/report.py`.
