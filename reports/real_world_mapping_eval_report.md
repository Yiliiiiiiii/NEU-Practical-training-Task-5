# Real-world Mapping Evaluation

## Summary

- Documents: 60
- Mapping recall: 0.683
- Package pass rate: 1.000
- Badcase violations: 0

## Per Document Type

| Document type | Documents | Mapping recall | Package pass rate |
| --- | ---: | ---: | ---: |
| general_doc | 15 | 0.821 | 1.000 |
| meeting_doc | 15 | 0.687 | 1.000 |
| policy_doc | 20 | 0.644 | 1.000 |
| procurement_doc | 10 | 0.571 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |
| issuer | 2 | 0 |
| publish_date | 2 | 0 |

## Missing Or Ambiguous

- real_policy_005_ai_industry_guide: missing=['issuer'], review_evidence=0
- real_procurement_001_broadcast_security_supervision: missing=[], review_evidence=3
- real_procurement_002_special_equipment_bid: missing=[], review_evidence=3
- real_procurement_003_radiation_monitoring_award: missing=[], review_evidence=3
- real_procurement_004_veterinary_platform_award: missing=[], review_evidence=3
- real_procurement_005_rehabilitation_equipment_award: missing=[], review_evidence=3
- real_general_001_notary_service_guide: missing=[], review_evidence=1
- real_general_002_biomed_project_guide: missing=[], review_evidence=1
- real_general_003_textile_application_flow: missing=[], review_evidence=1
- real_policy_006_technology_incubator_rules: missing=[], review_evidence=1
- real_policy_007_one_thing_list: missing=[], review_evidence=1
- real_procurement_006_vaccine_tender: missing=[], review_evidence=4
- real_procurement_007_testing_equipment_award: missing=[], review_evidence=4
- real_procurement_008_desktop_award: missing=[], review_evidence=2
- real_procurement_009_pollutant_monitoring_award: missing=[], review_evidence=3
- real_procurement_010_ultrasound_award: missing=[], review_evidence=4
- real_meeting_006_shandan_minutes: missing=[], review_evidence=1
- real_general_005_eldercare_technology_guide: missing=[], review_evidence=1
- real_general_006_soft_science_guide: missing=[], review_evidence=1
- real_general_007_domestic_cooperation_guide: missing=[], review_evidence=1
- real_general_008_science_communication_guide: missing=[], review_evidence=1
- real_general_009_food_technology_guide: missing=[], review_evidence=1
- real_general_010_cell_gene_therapy_guide: missing=[], review_evidence=1
- real_meeting_010_zhangjiagang_64_minutes: missing=[], review_evidence=1
- real_policy_011_battery_recycling_rules: missing=['publish_date'], review_evidence=1
- real_policy_012_sme_gradient_rules: missing=[], review_evidence=1
- real_policy_013_minor_platform_rules: missing=[], review_evidence=1
- real_policy_015_ai_ethics_rules: missing=[], review_evidence=1
- real_general_011_shanghai_branch_registration: missing=[], review_evidence=2
- real_policy_016_caac_civil_aviation_law: missing=['issuer', 'publish_date'], review_evidence=0
- real_policy_017_xinhua_investment_management: missing=[], review_evidence=2
- real_policy_019_mof_vat_transition: missing=[], review_evidence=1

## Badcase Violations

- None

## Review Evidence

- real_procurement_001_broadcast_security_supervision: 3 item(s)
- real_procurement_002_special_equipment_bid: 3 item(s)
- real_procurement_003_radiation_monitoring_award: 3 item(s)
- real_procurement_004_veterinary_platform_award: 3 item(s)
- real_procurement_005_rehabilitation_equipment_award: 3 item(s)
- real_general_001_notary_service_guide: 1 item(s)
- real_general_002_biomed_project_guide: 1 item(s)
- real_general_003_textile_application_flow: 1 item(s)
- real_policy_006_technology_incubator_rules: 1 item(s)
- real_policy_007_one_thing_list: 1 item(s)
- real_procurement_006_vaccine_tender: 4 item(s)
- real_procurement_007_testing_equipment_award: 4 item(s)
- real_procurement_008_desktop_award: 2 item(s)
- real_procurement_009_pollutant_monitoring_award: 3 item(s)
- real_procurement_010_ultrasound_award: 4 item(s)
- real_meeting_006_shandan_minutes: 1 item(s)
- real_general_005_eldercare_technology_guide: 1 item(s)
- real_general_006_soft_science_guide: 1 item(s)
- real_general_007_domestic_cooperation_guide: 1 item(s)
- real_general_008_science_communication_guide: 1 item(s)
- real_general_009_food_technology_guide: 1 item(s)
- real_general_010_cell_gene_therapy_guide: 1 item(s)
- real_meeting_010_zhangjiagang_64_minutes: 1 item(s)
- real_policy_011_battery_recycling_rules: 1 item(s)
- real_policy_012_sme_gradient_rules: 1 item(s)
- real_policy_013_minor_platform_rules: 1 item(s)
- real_policy_015_ai_ethics_rules: 1 item(s)
- real_general_011_shanghai_branch_registration: 2 item(s)
- real_policy_017_xinhua_investment_management: 2 item(s)
- real_policy_019_mof_vat_transition: 1 item(s)

## Package Verification Summary

- Passed: 60
- Failed: 0
