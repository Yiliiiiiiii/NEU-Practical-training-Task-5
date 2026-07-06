# Real-world UIR Evaluation Report

- Dataset size: 45
- Import success: 45 (100.0%)
- Task execution success: 45 (100.0%)
- Package verification success: 45 (100.0%)
- Mapping review required: 91
- High-risk mappings: 0
- Validation failures: 18

## By document type

| Document type | Count | Import | Execute | Package | Validation |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 10 | 10 | 10 | 10 | 10 |
| meeting_doc | 10 | 10 | 10 | 10 | 7 |
| policy_doc | 15 | 15 | 15 | 15 | 0 |
| procurement_doc | 10 | 10 | 10 | 10 | 10 |

## Cases

| Document | Type | Import | Execute | Package | Error |
| --- | --- | --- | --- | --- | --- |
| real_general_001_notary_service_guide | general_doc | yes | yes | yes |  |
| real_general_002_biomed_project_guide | general_doc | yes | yes | yes |  |
| real_general_003_textile_application_flow | general_doc | yes | yes | yes |  |
| real_general_004_tianhe_service_guide | general_doc | yes | yes | yes |  |
| real_general_005_eldercare_technology_guide | general_doc | yes | yes | yes |  |
| real_general_006_soft_science_guide | general_doc | yes | yes | yes |  |
| real_general_007_domestic_cooperation_guide | general_doc | yes | yes | yes |  |
| real_general_008_science_communication_guide | general_doc | yes | yes | yes |  |
| real_general_009_food_technology_guide | general_doc | yes | yes | yes |  |
| real_general_010_cell_gene_therapy_guide | general_doc | yes | yes | yes |  |
| real_meeting_001_changning_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_003_miluo_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_005_miluo_2026_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_006_shandan_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_007_zhenping_49_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_008_wlmqx_2026_01_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_009_kundulun_2026_01_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_010_zhangjiagang_64_minutes | meeting_doc | yes | yes | yes |  |
| real_policy_001_training_platform_rules | policy_doc | yes | yes | yes |  |
| real_policy_002_equipment_renewal | policy_doc | yes | yes | yes |  |
| real_policy_003_science_education_guide | policy_doc | yes | yes | yes |  |
| real_policy_004_student_loan_relief | policy_doc | yes | yes | yes |  |
| real_policy_005_ai_industry_guide | policy_doc | yes | yes | yes |  |
| real_policy_006_technology_incubator_rules | policy_doc | yes | yes | yes |  |
| real_policy_007_one_thing_list | policy_doc | yes | yes | yes |  |
| real_policy_008_sme_leader_training | policy_doc | yes | yes | yes |  |
| real_policy_009_network_safety_work | policy_doc | yes | yes | yes |  |
| real_policy_010_auto_ota_management | policy_doc | yes | yes | yes |  |
| real_policy_011_battery_recycling_rules | policy_doc | yes | yes | yes |  |
| real_policy_012_sme_gradient_rules | policy_doc | yes | yes | yes |  |
| real_policy_013_minor_platform_rules | policy_doc | yes | yes | yes |  |
| real_policy_014_digital_aging_campaign | policy_doc | yes | yes | yes |  |
| real_policy_015_ai_ethics_rules | policy_doc | yes | yes | yes |  |
| real_procurement_001_broadcast_security_supervision | procurement_doc | yes | yes | yes |  |
| real_procurement_002_special_equipment_bid | procurement_doc | yes | yes | yes |  |
| real_procurement_003_radiation_monitoring_award | procurement_doc | yes | yes | yes |  |
| real_procurement_004_veterinary_platform_award | procurement_doc | yes | yes | yes |  |
| real_procurement_005_rehabilitation_equipment_award | procurement_doc | yes | yes | yes |  |
| real_procurement_006_vaccine_tender | procurement_doc | yes | yes | yes |  |
| real_procurement_007_testing_equipment_award | procurement_doc | yes | yes | yes |  |
| real_procurement_008_desktop_award | procurement_doc | yes | yes | yes |  |
| real_procurement_009_pollutant_monitoring_award | procurement_doc | yes | yes | yes |  |
| real_procurement_010_ultrasound_award | procurement_doc | yes | yes | yes |  |

## Typical successes

- real_general_001_notary_service_guide
- real_general_002_biomed_project_guide
- real_general_003_textile_application_flow

## Typical failures

- real_meeting_004_shandan_2025_11_minutes: validation — downstream validation did not pass
- real_meeting_006_shandan_minutes: validation — downstream validation did not pass
- real_meeting_007_zhenping_49_minutes: validation — downstream validation did not pass

## Next steps

- Review failed cases by stage and add a regression fixture before changing behavior.
- Preserve source evidence and human review for ambiguous field mappings.
- Add domain aliases only through the existing review and knowledge workflow.
