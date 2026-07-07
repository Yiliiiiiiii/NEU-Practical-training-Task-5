# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 50
- Strict pass: 39
- Average recall: 0.743
- Review required: 21
- Required missing: 2
- Badcase violations: 0
- Package verification pass: 50

## Baseline Delta

- Average recall: +0.393
- Review required: -124
- Required missing: -16
- Strict pass: +35

## Metrics By Document Type

| Type | Documents | Strict pass | Recall avg | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 15 | 13 | 0.824 | 11 | 0 |
| meeting_doc | 15 | 15 | 0.764 | 2 | 0 |
| policy_doc | 20 | 11 | 0.666 | 8 | 2 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |
| action_items | 6 | 0 |
| application_conditions | 14 | 0 |
| application_materials | 8 | 0 |
| attendees | 5 | 0 |
| category | 3 | 0 |
| chairperson | 14 | 0 |
| contact | 10 | 0 |
| content | 50 | 0 |
| deadline | 7 | 0 |
| decisions | 9 | 0 |
| doc_type | 20 | 0 |
| document_number | 16 | 0 |
| effective_date | 4 | 0 |
| issuer | 19 | 1 |
| meeting_date | 15 | 0 |
| meeting_location | 2 | 0 |
| meeting_number | 13 | 0 |
| meeting_title | 15 | 0 |
| policy_measures | 6 | 0 |
| process_steps | 14 | 0 |
| publish_date | 19 | 1 |
| responsible_departments | 1 | 0 |
| service_object | 14 | 0 |
| source | 50 | 0 |
| summary | 1 | 0 |
| target_audience | 5 | 0 |
| title | 35 | 0 |
| topics | 14 | 0 |

## Strict Validation

- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold
- real_policy_011_battery_recycling_rules (policy_doc): strict_pass_failed, missing_required_fields
- real_general_011_shanghai_branch_registration (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_013_zhongshan_import_export_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_016_caac_civil_aviation_law (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_017_xinhua_investment_management (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_018_beijing_ecommerce_support (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_019_mof_vat_transition (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_policy_020_customs_foreign_investment_catalog (policy_doc): strict_pass_failed, mapping_recall_below_threshold

## Review-required Analysis

- Total review-required items: 21

## Required Missing Analysis

- Total required missing items: 2

## Badcase Safety

- Badcase violations: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_001_training_platform_rules (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_004_student_loan_relief (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_005_ai_industry_guide (policy_doc): missing=['issuer']; review_required=0; reasons=['strict_pass_failed', 'missing_required_fields', 'mapping_recall_below_threshold']
- real_policy_011_battery_recycling_rules (policy_doc): missing=['publish_date']; review_required=1; reasons=['strict_pass_failed', 'missing_required_fields']
- real_general_011_shanghai_branch_registration (general_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_013_zhongshan_import_export_guide (general_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_016_caac_civil_aviation_law (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_017_xinhua_investment_management (policy_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_018_beijing_ecommerce_support (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_019_mof_vat_transition (policy_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_policy_020_customs_foreign_investment_catalog (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
