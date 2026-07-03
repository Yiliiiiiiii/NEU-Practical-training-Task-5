# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 35
- Strict pass: 13
- Average recall: 0.568
- Review required: 69
- Required missing: 6
- Badcase violations: 0
- Package verification pass: 35

## Baseline Delta

- Average recall: +0.218
- Review required: -76
- Required missing: -12
- Strict pass: +9

## Metrics By Document Type

| Type | Documents | Strict pass | Recall avg | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 10 | 5 | 0.629 | 31 | 0 |
| meeting_doc | 10 | 0 | 0.434 | 17 | 0 |
| policy_doc | 15 | 8 | 0.616 | 21 | 6 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |
| action_items | 10 | 0 |
| application_conditions | 7 | 0 |
| attendees | 2 | 0 |
| contact | 6 | 0 |
| content | 35 | 0 |
| created_date | 10 | 0 |
| deadline | 3 | 0 |
| deadlines | 2 | 0 |
| doc_type | 15 | 0 |
| document_number | 12 | 0 |
| document_subtype | 10 | 0 |
| effective_date | 15 | 0 |
| issuer | 20 | 3 |
| meeting_date | 10 | 0 |
| meeting_number | 2 | 0 |
| meeting_title | 10 | 0 |
| organizer | 3 | 0 |
| process_steps | 7 | 0 |
| publish_date | 12 | 3 |
| service_object | 7 | 0 |
| source | 35 | 0 |
| title | 25 | 0 |

## Strict Validation

- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_003_science_education_guide (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_001_changning_executive_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_002_shaxian_executive_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_003_miluo_executive_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_001_notary_service_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_002_biomed_project_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_003_textile_application_flow (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_007_one_thing_list (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_005_miluo_2026_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_006_shandan_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_007_domestic_cooperation_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_009_food_technology_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_007_zhenping_49_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_008_wlmqx_2026_01_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_009_kundulun_2026_01_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_010_zhangjiagang_64_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_011_battery_recycling_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_013_minor_platform_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold

## Review-required Analysis

- Total review-required items: 69

## Required Missing Analysis

- Total required missing items: 6

## Badcase Safety

- Badcase violations: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_001_training_platform_rules (policy_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_003_science_education_guide (policy_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_004_student_loan_relief (policy_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_005_ai_industry_guide (policy_doc): missing=['issuer', 'publish_date']; review_required=1; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_meeting_001_changning_executive_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_002_shaxian_executive_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_003_miluo_executive_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_001_notary_service_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_002_biomed_project_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_003_textile_application_flow (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_007_one_thing_list (policy_doc): missing=['issuer']; review_required=2; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_005_miluo_2026_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_006_shandan_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_007_domestic_cooperation_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_009_food_technology_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_007_zhenping_49_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_008_wlmqx_2026_01_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_009_kundulun_2026_01_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_010_zhangjiagang_64_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_011_battery_recycling_rules (policy_doc): missing=['issuer', 'publish_date']; review_required=1; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_013_minor_platform_rules (policy_doc): missing=['publish_date']; review_required=1; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
