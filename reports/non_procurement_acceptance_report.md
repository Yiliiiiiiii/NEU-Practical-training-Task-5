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
evaluation. The evaluator successfully processed all 20 non-procurement
documents, but the recall and review-required thresholds are still outside the
acceptance bounds.

| Check | Target | Latest evidence | Status |
| --- | ---: | ---: | --- |
| Average mapping recall | `>= 0.50` | `0.4211309523809524` | Not met |
| Review-required count | `<= 115` | `149` | Not met |
| Required missing count | `<= 14` | `12` | Met |
| Badcase violations | `0` | `0` | Met |
| Package verification | `20/20` | `20/20` | Met |
| Backend regression tests | No regressions | latest full backend run before this report: `392 passed` | Passed at that checkpoint |
| Frontend and unified verification | Build and `verify_all` pass | frontend build passed; `verify_all --check-openapi` passed | Met |

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

This indicates safe incremental improvement in package-derived diagnostics. The
API-backed evaluator agrees on average recall and package verification, but it
counts 149 review-required mappings and 12 required missing mappings. The
required-missing gate is now within target; the recall and review-required gates
remain open.

## Decision

Phase one remains open. The next step is to reduce review-required mappings and
raise average recall without weakening badcase filters or auto-accepting
ambiguous evidence.
