# Real-world Mapping Evaluation

## Summary

- Documents: 18
- Auto mapping recall: 0.763
- Assisted mapping recall: 0.807
- Review-required recall: 0.044
- Review-required rate: 0.050
- Required missing: 8
- Package pass rate: 1.000
- Badcase violations: 0

Metric note: legacy `mapping_recall` is retained as assisted mapping recall.

## Per Document Type

| Document type | Documents | Auto recall | Assisted recall | Review rate | Required missing | Badcases | Package pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| general_doc | 3 | 0.722 | 0.889 | 0.130 | 2 | 0 | 1.000 |
| meeting_doc | 6 | 0.778 | 0.806 | 0.039 | 2 | 0 | 1.000 |
| policy_doc | 9 | 0.767 | 0.783 | 0.030 | 4 | 0 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_policy_001_training_platform_rules: missing=[], review_evidence=1
- real_policy_005_ai_industry_guide: missing=[], review_evidence=1
- real_general_001_notary_service_guide: missing=[], review_evidence=1
- real_general_002_biomed_project_guide: missing=[], review_evidence=1
- real_general_003_textile_application_flow: missing=[], review_evidence=1
- real_meeting_005_miluo_2026_minutes: missing=[], review_evidence=1
- real_meeting_006_shandan_minutes: missing=[], review_evidence=1

## Badcase Violations

- None

## Review Evidence

- real_policy_001_training_platform_rules: 1 item(s)
- real_policy_005_ai_industry_guide: 1 item(s)
- real_general_001_notary_service_guide: 1 item(s)
- real_general_002_biomed_project_guide: 1 item(s)
- real_general_003_textile_application_flow: 1 item(s)
- real_meeting_005_miluo_2026_minutes: 1 item(s)
- real_meeting_006_shandan_minutes: 1 item(s)

## Package Verification Summary

- Passed: 18
- Failed: 0
