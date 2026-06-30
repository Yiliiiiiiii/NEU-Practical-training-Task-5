# Non-procurement Document Evaluation

## Summary

- Documents: 11
- Strict pass rate: 0.000
- Mapping recall average: 0.237
- Required missing: 25
- Review required: 95
- High-risk auto accepted: 0
- Badcase violations: 0
- Package valid: 11

## Thresholds

- Mapping recall: 0.65
- General document minimum mapped/review targets: 2
- Meeting document minimum mapped/review targets: 2
- Policy document minimum mapped/review targets: 3

## By Document Type

| Type | Documents | Strict pass | Recall avg | Missing required | Package valid |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 3 | 0 | 0.250 | 3 | 3 |
| meeting_doc | 3 | 0 | 0.000 | 9 | 3 |
| policy_doc | 5 | 0 | 0.370 | 13 | 5 |

## Failures

- real_general_001_notary_service_guide (general_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_general_002_biomed_project_guide (general_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_general_003_textile_application_flow (general_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_001_changning_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_002_shaxian_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_003_miluo_executive_minutes (meeting_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_002_equipment_renewal (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_003_science_education_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold

## Errors

- None

## Documents

| Document | Type | Strict pass | Recall | Missing required | Review required | Package valid |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| real_general_001_notary_service_guide | general_doc | 0 | 0.250 | 1 | 11 | 1 |
| real_general_002_biomed_project_guide | general_doc | 0 | 0.250 | 1 | 11 | 1 |
| real_general_003_textile_application_flow | general_doc | 0 | 0.250 | 1 | 13 | 1 |
| real_meeting_001_changning_executive_minutes | meeting_doc | 0 | 0.000 | 3 | 13 | 1 |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | 0 | 0.000 | 3 | 11 | 1 |
| real_meeting_003_miluo_executive_minutes | meeting_doc | 0 | 0.000 | 3 | 11 | 1 |
| real_policy_001_training_platform_rules | policy_doc | 0 | 0.286 | 2 | 5 | 1 |
| real_policy_002_equipment_renewal | policy_doc | 0 | 0.333 | 3 | 5 | 1 |
| real_policy_003_science_education_guide | policy_doc | 0 | 0.333 | 2 | 5 | 1 |
| real_policy_004_student_loan_relief | policy_doc | 0 | 0.400 | 3 | 5 | 1 |
| real_policy_005_ai_industry_guide | policy_doc | 0 | 0.500 | 3 | 5 | 1 |
