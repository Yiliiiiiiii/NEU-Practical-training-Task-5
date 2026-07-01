# Real-world Mapping Evaluation

## Summary

- Documents: 30
- Mapping recall: 0.401
- Package pass rate: 1.000
- Badcase violations: 0

## Per Document Type

| Document type | Documents | Mapping recall | Package pass rate |
| --- | ---: | ---: | ---: |
| general_doc | 4 | 0.333 | 1.000 |
| meeting_doc | 6 | 0.139 | 1.000 |
| policy_doc | 10 | 0.470 | 1.000 |
| procurement_doc | 10 | 0.473 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |
| issuer | 6 | 0 |
| meeting_title | 6 | 0 |
| publish_date | 6 | 0 |

## Missing Or Ambiguous

- real_policy_001_training_platform_rules: missing=['issuer', 'publish_date'], review_evidence=5
- real_policy_002_equipment_renewal: missing=['issuer', 'publish_date'], review_evidence=4
- real_policy_003_science_education_guide: missing=['issuer', 'publish_date'], review_evidence=5
- real_policy_004_student_loan_relief: missing=['issuer', 'publish_date'], review_evidence=4
- real_policy_005_ai_industry_guide: missing=['issuer', 'publish_date'], review_evidence=4
- real_procurement_001_broadcast_security_supervision: missing=[], review_evidence=2
- real_procurement_002_special_equipment_bid: missing=[], review_evidence=2
- real_procurement_003_radiation_monitoring_award: missing=[], review_evidence=4
- real_procurement_004_veterinary_platform_award: missing=[], review_evidence=4
- real_procurement_005_rehabilitation_equipment_award: missing=[], review_evidence=4
- real_meeting_001_changning_executive_minutes: missing=['meeting_title'], review_evidence=11
- real_meeting_002_shaxian_executive_minutes: missing=['meeting_title'], review_evidence=9
- real_meeting_003_miluo_executive_minutes: missing=['meeting_title'], review_evidence=9
- real_general_001_notary_service_guide: missing=[], review_evidence=10
- real_general_002_biomed_project_guide: missing=[], review_evidence=10
- real_general_003_textile_application_flow: missing=[], review_evidence=12
- real_policy_006_technology_incubator_rules: missing=[], review_evidence=4
- real_policy_007_one_thing_list: missing=['issuer', 'publish_date'], review_evidence=4
- real_policy_008_sme_leader_training: missing=[], review_evidence=4
- real_policy_009_network_safety_work: missing=[], review_evidence=4
- real_procurement_006_vaccine_tender: missing=[], review_evidence=3
- real_procurement_007_testing_equipment_award: missing=[], review_evidence=4
- real_procurement_008_desktop_award: missing=[], review_evidence=3
- real_procurement_009_pollutant_monitoring_award: missing=[], review_evidence=4
- real_procurement_010_ultrasound_award: missing=[], review_evidence=5
- real_meeting_004_shandan_2025_11_minutes: missing=['meeting_title'], review_evidence=10
- real_meeting_005_miluo_2026_minutes: missing=['meeting_title'], review_evidence=9
- real_meeting_006_shandan_minutes: missing=['meeting_title'], review_evidence=11
- real_general_004_tianhe_service_guide: missing=[], review_evidence=12
- real_policy_010_auto_ota_management: missing=[], review_evidence=4

## Badcase Violations

- None

## Review Evidence

- real_policy_001_training_platform_rules: 5 item(s)
- real_policy_002_equipment_renewal: 4 item(s)
- real_policy_003_science_education_guide: 5 item(s)
- real_policy_004_student_loan_relief: 4 item(s)
- real_policy_005_ai_industry_guide: 4 item(s)
- real_procurement_001_broadcast_security_supervision: 2 item(s)
- real_procurement_002_special_equipment_bid: 2 item(s)
- real_procurement_003_radiation_monitoring_award: 4 item(s)
- real_procurement_004_veterinary_platform_award: 4 item(s)
- real_procurement_005_rehabilitation_equipment_award: 4 item(s)
- real_meeting_001_changning_executive_minutes: 11 item(s)
- real_meeting_002_shaxian_executive_minutes: 9 item(s)
- real_meeting_003_miluo_executive_minutes: 9 item(s)
- real_general_001_notary_service_guide: 10 item(s)
- real_general_002_biomed_project_guide: 10 item(s)
- real_general_003_textile_application_flow: 12 item(s)
- real_policy_006_technology_incubator_rules: 4 item(s)
- real_policy_007_one_thing_list: 4 item(s)
- real_policy_008_sme_leader_training: 4 item(s)
- real_policy_009_network_safety_work: 4 item(s)
- real_procurement_006_vaccine_tender: 3 item(s)
- real_procurement_007_testing_equipment_award: 4 item(s)
- real_procurement_008_desktop_award: 3 item(s)
- real_procurement_009_pollutant_monitoring_award: 4 item(s)
- real_procurement_010_ultrasound_award: 5 item(s)
- real_meeting_004_shandan_2025_11_minutes: 10 item(s)
- real_meeting_005_miluo_2026_minutes: 9 item(s)
- real_meeting_006_shandan_minutes: 11 item(s)
- real_general_004_tianhe_service_guide: 12 item(s)
- real_policy_010_auto_ota_management: 4 item(s)

## Package Verification Summary

- Passed: 30
- Failed: 0
