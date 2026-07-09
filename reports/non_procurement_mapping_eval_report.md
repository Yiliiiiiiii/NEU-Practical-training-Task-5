# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 50
- Strict pass: 48
- Average recall (legacy assisted): 0.806
- Auto mapping recall: 0.777
- Assisted mapping recall: 0.807
- Review-required recall: 0.029
- Review-required rate: 0.057
- Review required: 24
- Required missing: 0
- Badcase violations: 0
- Package verification pass: 50

Metric note: legacy average recall is retained as assisted mapping recall.

## Baseline Delta

- Average recall: +0.456
- Review required: -121
- Required missing: -18
- Strict pass: +44

## Metrics By Document Type

| Type | Documents | Strict pass | Auto recall | Assisted recall | Review rate | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| general_doc | 15 | 14 | 0.741 | 0.759 | 0.089 | 11 | 0 |
| meeting_doc | 15 | 15 | 0.774 | 0.809 | 0.038 | 5 | 0 |
| policy_doc | 20 | 19 | 0.808 | 0.842 | 0.048 | 8 | 0 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |
| action_items | 8 | 0 |
| application_conditions | 14 | 0 |
| application_materials | 8 | 0 |
| attendees | 7 | 0 |
| category | 8 | 0 |
| chairperson | 14 | 0 |
| contact | 10 | 0 |
| content | 50 | 0 |
| deadline | 7 | 0 |
| decisions | 9 | 0 |
| doc_type | 20 | 0 |
| document_number | 16 | 0 |
| effective_date | 10 | 0 |
| issuer | 21 | 0 |
| meeting_date | 15 | 0 |
| meeting_location | 2 | 0 |
| meeting_number | 15 | 0 |
| meeting_title | 15 | 0 |
| organizer | 1 | 0 |
| policy_measures | 10 | 0 |
| process_steps | 15 | 0 |
| publish_date | 20 | 0 |
| responsible_departments | 1 | 0 |
| service_object | 14 | 0 |
| source | 50 | 0 |
| summary | 1 | 0 |
| target_audience | 9 | 0 |
| title | 35 | 0 |
| topics | 14 | 0 |
| valid_until | 1 | 0 |

## Strict Validation

- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, mapping_recall_below_threshold
- real_general_011_shanghai_branch_registration (general_doc): strict_pass_failed, mapping_recall_below_threshold

## Review-required Analysis

- Total review-required items: 24

## Required Missing Analysis

- Total required missing items: 0

## Badcase Safety

- Badcase violations: 0
- High-risk auto accepted: 0
- LLM auto accepted: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_005_ai_industry_guide (policy_doc): missing=[]; review_required=1; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']
- real_general_011_shanghai_branch_registration (general_doc): missing=[]; review_required=2; reasons=['strict_pass_failed', 'mapping_recall_below_threshold']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
