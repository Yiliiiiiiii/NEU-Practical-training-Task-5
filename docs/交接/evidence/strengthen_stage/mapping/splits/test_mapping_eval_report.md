# Real-world Mapping Evaluation

## Summary

- Documents: 9
- Auto mapping recall: 0.853
- Assisted mapping recall: 0.868
- Review-required recall: 0.015
- Review-required rate: 0.096
- Required missing: 1
- Package pass rate: 1.000
- Badcase violations: 0

Metric note: legacy `mapping_recall` is retained as assisted mapping recall.

## Per Document Type

| Document type | Documents | Auto recall | Assisted recall | Review rate | Required missing | Badcases | Package pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| general_doc | 7 | 0.870 | 0.870 | 0.078 | 0 | 0 | 1.000 |
| meeting_doc | 1 | 0.750 | 0.750 | 0.100 | 1 | 0 | 1.000 |
| policy_doc | 1 | 0.833 | 1.000 | 0.222 | 0 | 0 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_policy_010_auto_ota_management: missing=[], review_evidence=2
- real_general_005_eldercare_technology_guide: missing=[], review_evidence=1
- real_general_006_soft_science_guide: missing=[], review_evidence=1
- real_general_007_domestic_cooperation_guide: missing=[], review_evidence=1
- real_general_009_food_technology_guide: missing=[], review_evidence=1
- real_general_010_cell_gene_therapy_guide: missing=[], review_evidence=1
- real_meeting_007_zhenping_49_minutes: missing=[], review_evidence=1

## Badcase Violations

- None

## Review Evidence

- real_policy_010_auto_ota_management: 2 item(s)
- real_general_005_eldercare_technology_guide: 1 item(s)
- real_general_006_soft_science_guide: 1 item(s)
- real_general_007_domestic_cooperation_guide: 1 item(s)
- real_general_009_food_technology_guide: 1 item(s)
- real_general_010_cell_gene_therapy_guide: 1 item(s)
- real_meeting_007_zhenping_49_minutes: 1 item(s)

## Package Verification Summary

- Passed: 9
- Failed: 0
