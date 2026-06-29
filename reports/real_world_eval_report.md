# Real-world UIR Evaluation Report

- Dataset size: 16
- Import success: 16 (100.0%)
- Task execution success: 16 (100.0%)
- Package verification success: 16 (100.0%)
- Mapping review required: 89
- High-risk mappings: 0
- Validation failures: 16

## By document type

| Document type | Count | Import | Execute | Package | Validation |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 3 | 3 | 3 | 3 | 0 |
| meeting_doc | 3 | 3 | 3 | 3 | 0 |
| policy_doc | 5 | 5 | 5 | 5 | 0 |
| procurement_doc | 5 | 5 | 5 | 5 | 0 |

## Cases

| Document | Type | Import | Execute | Package | Error |
| --- | --- | --- | --- | --- | --- |
| real_general_001_notary_service_guide | general_doc | yes | yes | yes |  |
| real_general_002_biomed_project_guide | general_doc | yes | yes | yes |  |
| real_general_003_textile_application_flow | general_doc | yes | yes | yes |  |
| real_meeting_001_changning_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_meeting_003_miluo_executive_minutes | meeting_doc | yes | yes | yes |  |
| real_policy_001_training_platform_rules | policy_doc | yes | yes | yes |  |
| real_policy_002_equipment_renewal | policy_doc | yes | yes | yes |  |
| real_policy_003_science_education_guide | policy_doc | yes | yes | yes |  |
| real_policy_004_student_loan_relief | policy_doc | yes | yes | yes |  |
| real_policy_005_ai_industry_guide | policy_doc | yes | yes | yes |  |
| real_procurement_001_broadcast_security_supervision | procurement_doc | yes | yes | yes |  |
| real_procurement_002_special_equipment_bid | procurement_doc | yes | yes | yes |  |
| real_procurement_003_radiation_monitoring_award | procurement_doc | yes | yes | yes |  |
| real_procurement_004_veterinary_platform_award | procurement_doc | yes | yes | yes |  |
| real_procurement_005_rehabilitation_equipment_award | procurement_doc | yes | yes | yes |  |

## Typical successes


## Typical failures

- real_general_001_notary_service_guide: validation — downstream validation did not pass
- real_general_002_biomed_project_guide: validation — downstream validation did not pass
- real_general_003_textile_application_flow: validation — downstream validation did not pass

## Next steps

- Review failed cases by stage and add a regression fixture before changing behavior.
- Preserve source evidence and human review for ambiguous field mappings.
- Add domain aliases only through the existing review and knowledge workflow.
