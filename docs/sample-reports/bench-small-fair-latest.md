# Fair small-size bench (both modes in Docker)

Generated: 2026-09-06T03:29:01.254305+00:00
Size: small; warmup=1; reps=5

| Workload | Baseline median ms | Native median ms | Speedup |
|----------|-------------------:|-----------------:|--------:|
| aggregate | 4003 | 4744 | 0.84x |
  - baseline: n=5 median=4003 mean=4003±11 min=3991 max=4020 times=[4020, 3996, 4003, 4007, 3991]
  - native: n=5 median=4744 mean=4863±269 min=4730 max=5343 times=[4731, 4744, 5343, 4730, 4765]
| joins | 3991 | 5840 | 0.68x |
  - baseline: n=5 median=3991 mean=3982±23 min=3956 max=4010 times=[4010, 3994, 3956, 3991, 3961]
  - native: n=5 median=5840 mean=5744±231 min=5332 max=5877 times=[5332, 5877, 5821, 5848, 5840]

Notes:
- Fair comparison: both modes use linux/arm64 Docker images.
- Application elapsed includes container + Spark startup + job.
- `small` is still modest data; not production certification.
- Raw JSON: `/Users/neo/Software/SuperSpark/artifacts/reports/bench-small-fair-1788665341.json`

