# SuperSpark report

Generated: 2026-09-06T01:15:35.459068+00:00

| Workload | Mode | Size | Status | App ms | Native evidence |
|----------|------|------|--------|--------|-----------------|
| aggregate | baseline | tiny | PASS | 3287 | False |
| aggregate | native | tiny | PASS | 4677 | True |
| aggregate | optimized | tiny | PASS | 5233 | True |
| edge_cases | baseline | tiny | PASS | 3242 | False |
| edge_cases | native | tiny | PASS | 4722 | True |
| fallback_udf | baseline | tiny | PASS | 4439 | False |
| fallback_udf | native | tiny | EXPECTED_FALLBACK | 5875 | True |
| filter_project | baseline | tiny | PASS | 3680 | False |
| filter_project | native | tiny | PASS | 4873 | True |
| filter_project | optimized | tiny | PASS | 4765 | True |
| joins | baseline | tiny | PASS | 3811 | False |
| joins | native | tiny | PASS | 5193 | True |
| parquet_roundtrip | baseline | tiny | PASS | 3811 | False |
| parquet_roundtrip | native | tiny | PASS | 5719 | True |
| skew | baseline | tiny | PASS | 3745 | False |
| skew | native | tiny | PASS | 5275 | True |
| skew | optimized | tiny | PASS | 5266 | True |
| small_files | baseline | tiny | PASS | 4332 | False |
| small_files | native | tiny | PASS | 6304 | True |
| sort_topk | baseline | tiny | PASS | 3273 | False |
| sort_topk | native | tiny | PASS | 4747 | True |
| spill | baseline | tiny | PASS | 3319 | False |
| spill | native | tiny | PASS | 4730 | True |
| strings | baseline | tiny | PASS | 3299 | False |
| strings | native | tiny | PASS | 5309 | True |

## Speedups (latest per workload)

- aggregate: baseline_med=3304ms native_med=4692ms speedup=0.70x
- edge_cases: baseline_med=3233ms native_med=4670ms speedup=0.69x
- fallback_udf: baseline_med=4439ms native_med=5875ms speedup=0.76x
- filter_project: baseline_med=3734ms native_med=4728ms speedup=0.79x
- joins: baseline_med=3532ms native_med=5234ms speedup=0.67x
- parquet_roundtrip: baseline_med=3698ms native_med=5464ms speedup=0.68x
- skew: baseline_med=3258ms native_med=4757ms speedup=0.68x
- small_files: baseline_med=4350ms native_med=6146ms speedup=0.71x
- sort_topk: baseline_med=3273ms native_med=4747ms speedup=0.69x
- spill: baseline_med=3250ms native_med=4805ms speedup=0.68x
- strings: baseline_med=3299ms native_med=5309ms speedup=0.62x

Suite geometric-mean speedup: 0.6963224731720165

Notes: tiny sizes are correctness-oriented; do not treat as production performance certification.
