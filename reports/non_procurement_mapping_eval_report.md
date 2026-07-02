# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 20
- Strict pass: 4
- Average recall: 0.421
- Review required: 149
- Required missing: 12
- Badcase violations: 0
- Package verification pass: 20

## Baseline Delta

- Average recall: +0.072
- Review required: +4
- Required missing: -6
- Strict pass: +0

## Metrics By Document Type

| Type | Documents | Strict pass | Recall avg | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 4 | 0 | 0.333 | 49 | 0 |
| meeting_doc | 6 | 0 | 0.333 | 54 | 0 |
| policy_doc | 10 | 4 | 0.509 | 46 | 12 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |
| action_items | 6 | 0 |
| agenda_items | 3 | 0 |
| application_conditions | 4 | 0 |
| application_materials | 4 | 0 |
| attachments | 2 | 0 |
| attendees | 6 | 0 |
| category | 4 | 0 |
| contact | 2 | 0 |
| content | 20 | 0 |
| created_date | 4 | 0 |
| deadline | 3 | 0 |
| deadlines | 6 | 0 |
| decision_items | 6 | 0 |
| decisions | 6 | 0 |
| departments | 2 | 0 |
| doc_type | 10 | 0 |
| document_number | 8 | 0 |
| document_subtype | 4 | 0 |
| effective_date | 10 | 0 |
| issuer | 7 | 6 |
| keywords | 10 | 0 |
| meeting_date | 6 | 0 |
| meeting_location | 6 | 0 |
| meeting_title | 6 | 0 |
| organizer | 2 | 0 |
| process_steps | 4 | 0 |
| publish_date | 5 | 6 |
| published_at | 4 | 0 |
| service_object | 4 | 0 |
| source | 20 | 0 |
| summary | 1 | 0 |
| tags | 4 | 0 |
| target_audience | 10 | 0 |
| title | 14 | 0 |
| topics | 6 | 0 |

## Strict Validation

- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_002_equipment_renewal (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_003_science_education_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
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
- real_general_004_tianhe_service_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold

## Review-required Analysis

- Total review-required items: 149

## Required Missing Analysis

- Total required missing items: 12

## Badcase Safety

- Badcase violations: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_001_training_platform_rules (policy_doc): missing=['issuer', 'publish_date']; review_required=5; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_002_equipment_renewal (policy_doc): missing=['issuer', 'publish_date']; review_required=7; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_003_science_education_guide (policy_doc): missing=['issuer', 'publish_date']; review_required=5; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_004_student_loan_relief (policy_doc): missing=['issuer', 'publish_date']; review_required=4; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_005_ai_industry_guide (policy_doc): missing=['issuer', 'publish_date']; review_required=4; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_meeting_001_changning_executive_minutes (meeting_doc): missing=[]; review_required=10; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_002_shaxian_executive_minutes (meeting_doc): missing=[]; review_required=8; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_003_miluo_executive_minutes (meeting_doc): missing=[]; review_required=9; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_001_notary_service_guide (general_doc): missing=[]; review_required=11; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_002_biomed_project_guide (general_doc): missing=[]; review_required=12; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_003_textile_application_flow (general_doc): missing=[]; review_required=13; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_007_one_thing_list (policy_doc): missing=['issuer', 'publish_date']; review_required=5; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): missing=[]; review_required=9; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_005_miluo_2026_minutes (meeting_doc): missing=[]; review_required=8; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_meeting_006_shandan_minutes (meeting_doc): missing=[]; review_required=10; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_004_tianhe_service_guide (general_doc): missing=[]; review_required=13; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
