# Real-world Mapping Evaluation

## Summary

- Documents: 18
- Auto mapping recall: 0.772
- Assisted mapping recall: 0.868
- Review-required recall: 0.096
- Review-required rate: 0.114
- Required missing: 7
- Package pass rate: 1.000
- Badcase violations: 0

Metric note: legacy `mapping_recall` is retained as assisted mapping recall.

## Per Document Type

| Document type | Documents | Auto recall | Assisted recall | Review rate | Required missing | Badcases | Package pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| general_doc | 3 | 0.722 | 0.889 | 0.167 | 2 | 0 | 1.000 |
| meeting_doc | 6 | 0.806 | 0.917 | 0.125 | 1 | 0 | 1.000 |
| policy_doc | 9 | 0.767 | 0.833 | 0.087 | 4 | 0 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_policy_001_training_platform_rules: missing=[], review_evidence=1
- real_policy_002_equipment_renewal: missing=[], review_evidence=1
- real_policy_005_ai_industry_guide: missing=[], review_evidence=1
- real_meeting_001_changning_executive_minutes: missing=[], review_evidence=1
- real_meeting_002_shaxian_executive_minutes: missing=[], review_evidence=1
- real_meeting_003_miluo_executive_minutes: missing=[], review_evidence=1
- real_general_001_notary_service_guide: missing=[], review_evidence=1
- real_general_002_biomed_project_guide: missing=[], review_evidence=1
- real_general_003_textile_application_flow: missing=[], review_evidence=2
- real_policy_007_one_thing_list: missing=[], review_evidence=1
- real_policy_008_sme_leader_training: missing=[], review_evidence=1
- real_policy_009_network_safety_work: missing=[], review_evidence=1
- real_meeting_004_shandan_2025_11_minutes: missing=[], review_evidence=1
- real_meeting_005_miluo_2026_minutes: missing=[], review_evidence=1
- real_meeting_006_shandan_minutes: missing=[], review_evidence=2

## Badcase Violations

- None

## Review Evidence

- real_policy_001_training_platform_rules: 1 item(s)
- real_policy_002_equipment_renewal: 1 item(s)
- real_policy_005_ai_industry_guide: 1 item(s)
- real_meeting_001_changning_executive_minutes: 1 item(s)
- real_meeting_002_shaxian_executive_minutes: 1 item(s)
- real_meeting_003_miluo_executive_minutes: 1 item(s)
- real_general_001_notary_service_guide: 1 item(s)
- real_general_002_biomed_project_guide: 1 item(s)
- real_general_003_textile_application_flow: 2 item(s)
- real_policy_007_one_thing_list: 1 item(s)
- real_policy_008_sme_leader_training: 1 item(s)
- real_policy_009_network_safety_work: 1 item(s)
- real_meeting_004_shandan_2025_11_minutes: 1 item(s)
- real_meeting_005_miluo_2026_minutes: 1 item(s)
- real_meeting_006_shandan_minutes: 2 item(s)

## Package Verification Summary

- Passed: 18
- Failed: 0
