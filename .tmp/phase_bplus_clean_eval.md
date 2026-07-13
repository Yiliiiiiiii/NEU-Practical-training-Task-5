# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 35
- Strict pass: 17
- Average recall: 0.610
- Review required: 58
- Required missing: 4
- Badcase violations: 0
- Package verification pass: 35

## Baseline Delta

- Average recall: +0.260
- Review required: -87
- Required missing: -14
- Strict pass: +13

## Metrics By Document Type

| Type | Documents | Strict pass | Recall avg | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 10 | 5 | 0.629 | 31 | 0 |
| meeting_doc | 10 | 3 | 0.560 | 6 | 0 |
| policy_doc | 15 | 9 | 0.630 | 21 | 4 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |
| application_conditions | 7 | 0 |
| attendees | 2 | 0 |
| chairperson | 9 | 0 |
| contact | 6 | 0 |
| content | 35 | 0 |
| created_date | 10 | 0 |
| deadline | 3 | 0 |
| deadlines | 3 | 0 |
| doc_type | 15 | 0 |
| document_number | 12 | 0 |
| document_subtype | 10 | 0 |
| effective_date | 15 | 0 |
| issuer | 21 | 2 |
| meeting_date | 10 | 0 |
| meeting_number | 7 | 0 |
| meeting_title | 10 | 0 |
| organizer | 3 | 0 |
| process_steps | 7 | 0 |
| publish_date | 13 | 2 |
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
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_006_shandan_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_007_domestic_cooperation_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_009_food_technology_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_007_zhenping_49_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_meeting_010_zhangjiagang_64_minutes (meeting_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_011_battery_recycling_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_013_minor_platform_rules (policy_doc): strict_pass_failed, mapping_recall_below_threshold

## Review-required Analysis

- Total review-required items: 58

## Required Missing Analysis

- Total required missing items: 4

## Badcase Safety

- Badcase violations: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_001_training_platform_rules (policy_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_003_science_education_guide (policy_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_004_student_loan_relief (policy_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_005_ai_industry_guide (policy_doc): missing=['issuer', 'publish_date']; review_required=1; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_meeting_001_changning_executive_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_002_shaxian_executive_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_003_miluo_executive_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_001_notary_service_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_002_biomed_project_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_003_textile_application_flow (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_006_shandan_minutes (meeting_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_007_domestic_cooperation_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_009_food_technology_guide (general_doc): missing=[]; review_required=3; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_007_zhenping_49_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_010_zhangjiagang_64_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_011_battery_recycling_rules (policy_doc): missing=['issuer', 'publish_date']; review_required=0; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_013_minor_platform_rules (policy_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
