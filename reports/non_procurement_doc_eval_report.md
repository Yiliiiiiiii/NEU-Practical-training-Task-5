# Non-procurement Document Evaluation

## Summary

- Documents: 20
- Strict pass rate: 0.200
- Mapping recall average: 0.349
- Required missing: 18
- Review required: 145
- High-risk auto accepted: 0
- Badcase violations: 0
- Package valid: 20

## Thresholds

- Mapping recall: 0.65
- General document minimum mapped/review targets: 2
- Meeting document minimum mapped/review targets: 2
- Policy document minimum mapped/review targets: 3

## By Document Type

| Type | Documents | Strict pass | Recall avg | Missing required | Package valid |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 4 | 0 | 0.333 | 0 | 4 |
| meeting_doc | 6 | 0 | 0.139 | 6 | 6 |
| policy_doc | 10 | 4 | 0.482 | 12 | 10 |

## Failures

- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_002_equipment_renewal (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_003_science_education_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_001_changning_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_002_shaxian_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_003_miluo_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_general_001_notary_service_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_002_biomed_project_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_003_textile_application_flow (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_007_one_thing_list (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_005_miluo_2026_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_006_shandan_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_general_004_tianhe_service_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold

## Errors

- None

## Documents

| Document | Type | Strict pass | Recall | Missing required | Review required | Package valid |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| real_policy_001_training_platform_rules | policy_doc | 0 | 0.250 | 2 | 5 | 1 |
| real_policy_002_equipment_renewal | policy_doc | 0 | 0.429 | 2 | 4 | 1 |
| real_policy_003_science_education_guide | policy_doc | 0 | 0.286 | 2 | 5 | 1 |
| real_policy_004_student_loan_relief | policy_doc | 0 | 0.429 | 2 | 4 | 1 |
| real_policy_005_ai_industry_guide | policy_doc | 0 | 0.429 | 2 | 4 | 1 |
| real_meeting_001_changning_executive_minutes | meeting_doc | 0 | 0.167 | 1 | 11 | 1 |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | 0 | 0.167 | 1 | 9 | 1 |
| real_meeting_003_miluo_executive_minutes | meeting_doc | 0 | 0.167 | 1 | 9 | 1 |
| real_general_001_notary_service_guide | general_doc | 0 | 0.333 | 0 | 10 | 1 |
| real_general_002_biomed_project_guide | general_doc | 0 | 0.333 | 0 | 10 | 1 |
| real_general_003_textile_application_flow | general_doc | 0 | 0.333 | 0 | 12 | 1 |
| real_policy_006_technology_incubator_rules | policy_doc | 1 | 0.667 | 0 | 4 | 1 |
| real_policy_007_one_thing_list | policy_doc | 0 | 0.333 | 2 | 4 | 1 |
| real_policy_008_sme_leader_training | policy_doc | 1 | 0.667 | 0 | 4 | 1 |
| real_policy_009_network_safety_work | policy_doc | 1 | 0.667 | 0 | 4 | 1 |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | 0 | 0.000 | 1 | 10 | 1 |
| real_meeting_005_miluo_2026_minutes | meeting_doc | 0 | 0.167 | 1 | 9 | 1 |
| real_meeting_006_shandan_minutes | meeting_doc | 0 | 0.167 | 1 | 11 | 1 |
| real_general_004_tianhe_service_guide | general_doc | 0 | 0.333 | 0 | 12 | 1 |
| real_policy_010_auto_ota_management | policy_doc | 1 | 0.667 | 0 | 4 | 1 |
