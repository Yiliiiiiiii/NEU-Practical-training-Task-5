# Phase C Report Consistency

- Passed: True
- Generated at: 2026-07-07T07:16:23.217468+00:00

## Metrics

| Metric | Mapping | Semantic | Strict |
| --- | ---: | ---: | ---: |
| dataset_size | 50 | 50 | 50 |
| strict_pass_count | 31 | 34 | 39 |
| required_missing_count | 4 | 4 | 14 |
| review_required_count | 22 | 11 | 22 |
| badcase_violations | 0 | 0 | None |
| llm_auto_accepted_count | None | 0 | None |

## Differences

- None

## Observations

- strict_pass_count: analyzers_use_diagnostic_scope ({"mapping": 31, "semantic": 34, "strict": 39})
- required_missing_count: strict_analyzer_uses_validation_scope ({"mapping": 4, "semantic": 4, "strict": 14})
- review_required_count: analyzers_use_diagnostic_scope ({"mapping": 22, "semantic": 11, "strict": 22})
