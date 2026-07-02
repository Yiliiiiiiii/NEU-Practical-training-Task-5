# Non-procurement Mapping Recall Acceptance Report

Generated for the 20-document non-procurement subset in the expanded
30-document real-world dataset.

## Evidence Sources

- Baseline: `reports/non_procurement_baseline_report.{json,md}`
- Offline package gap analysis: `reports/non_procurement_gap_analysis.{json,md}`
- API-backed evaluator: `reports/non_procurement_mapping_eval_report.{json,md}`
- Improvement plan and ranked diagnosis:
  `docs/non_procurement_mapping_improvement_plan.md`

## Acceptance Summary

The phase-one acceptance target is not met in the latest committed API-backed
evaluation. All 20 non-procurement imports failed at
`POST /api/v1/documents/import` with `HTTPStatusError: 502 Bad Gateway`, so the
API-backed metrics are treated as blocked/failed evidence rather than a valid
recall improvement result.

| Check | Target | Latest evidence | Status |
| --- | ---: | ---: | --- |
| Average mapping recall | `>= 0.50` | `0.0` from API-backed evaluator | Not met: evaluator failed for all 20 docs |
| Review-required count | `<= 115` | `0` from API-backed evaluator | Not met / invalid: no mappings were evaluated because imports failed |
| Required missing count | `<= 14` | `0` from API-backed evaluator | Not met / invalid: no mappings were evaluated because imports failed |
| Badcase violations | `0` | `0` | Guard held in the failed run; still recheck after API recovery |
| Package verification | `20/20` | `0/20` | Not met |
| Backend regression tests | No regressions | latest full backend run before this report: `392 passed` | Passed at that checkpoint |
| Frontend and unified verification | Build and `verify_all` pass | not rerun in this documentation task | Pending Task 10 |

## Useful Non-API Evidence

The offline package-based gap analyzer did complete over the non-procurement
subset and is useful for diagnosis:

| Metric | Baseline | Latest gap analysis |
| --- | ---: | ---: |
| Non-procurement documents | 20 | 20 |
| Strict pass count | 4 | 4 |
| Required missing count | 18 | 15 |
| Review-required count | 145 | 139 |
| Average mapping recall | `0.3494047619047619` | `0.4211309523809524` |
| Badcase violations | 0 | 0 |
| Package verification | 20/20 | 20 packages analyzed from complete package outputs |

This indicates safe incremental improvement in package-derived diagnostics, but
it does not satisfy the acceptance gate because the API-backed evaluator must
recover and pass the thresholds.

## Decision

Phase one remains open. The next step is Task 10 full verification: rerun the
backend tests, Ruff, frontend build, unified verification, API-backed
real-world evaluators, non-procurement evaluator, and offline gap analyzer. If
the 502 failure persists, diagnose the import path before claiming metric
success.
