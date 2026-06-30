# Real-world Mapping Evaluation

## Summary

- Documents: 16
- Mapping recall: 0.426
- Package pass rate: 1.000
- Badcase violations: 0

## Per Document Type

| Document type | Documents | Mapping recall | Package pass rate |
| --- | ---: | ---: | ---: |
| general_doc | 3 | 0.250 | 1.000 |
| meeting_doc | 3 | 0.000 | 1.000 |
| policy_doc | 5 | 0.357 | 1.000 |
| procurement_doc | 5 | 0.623 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |
| content | 9 | 0 |
| issuer | 5 | 0 |
| meeting_date | 3 | 0 |
| meeting_title | 3 | 0 |
| publish_date | 5 | 0 |

## Missing Or Ambiguous

- real_general_001_notary_service_guide: missing=['content'], review_evidence=5
- real_general_002_biomed_project_guide: missing=['content'], review_evidence=5
- real_general_003_textile_application_flow: missing=['content'], review_evidence=5
- real_meeting_001_changning_executive_minutes: missing=['meeting_title', 'meeting_date', 'content'], review_evidence=7
- real_meeting_002_shaxian_executive_minutes: missing=['meeting_title', 'meeting_date', 'content'], review_evidence=7
- real_meeting_003_miluo_executive_minutes: missing=['meeting_title', 'meeting_date', 'content'], review_evidence=7
- real_policy_001_training_platform_rules: missing=['issuer', 'publish_date'], review_evidence=2
- real_policy_002_equipment_renewal: missing=['issuer', 'publish_date', 'content'], review_evidence=3
- real_policy_003_science_education_guide: missing=['issuer', 'publish_date'], review_evidence=2
- real_policy_004_student_loan_relief: missing=['issuer', 'publish_date', 'content'], review_evidence=3
- real_policy_005_ai_industry_guide: missing=['issuer', 'publish_date', 'content'], review_evidence=3
- real_procurement_001_broadcast_security_supervision: missing=[], review_evidence=2
- real_procurement_002_special_equipment_bid: missing=[], review_evidence=2
- real_procurement_003_radiation_monitoring_award: missing=[], review_evidence=4
- real_procurement_004_veterinary_platform_award: missing=[], review_evidence=4
- real_procurement_005_rehabilitation_equipment_award: missing=[], review_evidence=4

## Badcase Violations

- None

## Review Evidence

- real_general_001_notary_service_guide: 5 item(s)
- real_general_002_biomed_project_guide: 5 item(s)
- real_general_003_textile_application_flow: 5 item(s)
- real_meeting_001_changning_executive_minutes: 7 item(s)
- real_meeting_002_shaxian_executive_minutes: 7 item(s)
- real_meeting_003_miluo_executive_minutes: 7 item(s)
- real_policy_001_training_platform_rules: 2 item(s)
- real_policy_002_equipment_renewal: 3 item(s)
- real_policy_003_science_education_guide: 2 item(s)
- real_policy_004_student_loan_relief: 3 item(s)
- real_policy_005_ai_industry_guide: 3 item(s)
- real_procurement_001_broadcast_security_supervision: 2 item(s)
- real_procurement_002_special_equipment_bid: 2 item(s)
- real_procurement_003_radiation_monitoring_award: 4 item(s)
- real_procurement_004_veterinary_platform_award: 4 item(s)
- real_procurement_005_rehabilitation_equipment_award: 4 item(s)

## Package Verification Summary

- Passed: 16
- Failed: 0
