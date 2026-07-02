# Non-procurement Mapping Evaluation Report

## Summary

- Dataset size: 20
- Strict pass: 0
- Average recall: 0.000
- Review required: 0
- Required missing: 0
- Badcase violations: 0
- Package verification pass: 0

## Baseline Delta

- Average recall: -0.349
- Review required: -145
- Required missing: -18
- Strict pass: -4

## Metrics By Document Type

| Type | Documents | Strict pass | Recall avg | Review required | Required missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_doc | 4 | 0 | 0.000 | 0 | 0 |
| meeting_doc | 6 | 0 | 0.000 | 0 | 0 |
| policy_doc | 10 | 0 | 0.000 | 0 | 0 |

## Field-level Recall

| Field | Mapped or review | Required missing |
| --- | ---: | ---: |

## Strict Validation

- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_002_equipment_renewal (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_003_science_education_guide (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_001_changning_executive_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_002_shaxian_executive_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_003_miluo_executive_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_general_001_notary_service_guide (general_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_general_002_biomed_project_guide (general_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_general_003_textile_application_flow (general_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_006_technology_incubator_rules (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_007_one_thing_list (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_008_sme_leader_training (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_009_network_safety_work (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_005_miluo_2026_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_meeting_006_shandan_minutes (meeting_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_general_004_tianhe_service_guide (general_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid
- real_policy_010_auto_ota_management (policy_doc): strict_pass_failed, evaluation_error, mapping_recall_below_threshold, mapped_or_review_targets_below_threshold, package_invalid

## Review-required Analysis

- Total review-required items: 0

## Required Missing Analysis

- Total required missing items: 0

## Badcase Safety

- Badcase violations: 0

## Typical Improvements

- See gap analysis for ranked improvement candidates.

## Remaining Gaps

- real_policy_001_training_platform_rules (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_002_equipment_renewal (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_003_science_education_guide (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_004_student_loan_relief (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_005_ai_industry_guide (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_001_changning_executive_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_002_shaxian_executive_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_003_miluo_executive_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_general_001_notary_service_guide (general_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_general_002_biomed_project_guide (general_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_general_003_textile_application_flow (general_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_006_technology_incubator_rules (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_007_one_thing_list (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_008_sme_leader_training (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_009_network_safety_work (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_004_shandan_2025_11_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_005_miluo_2026_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_meeting_006_shandan_minutes (meeting_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_general_004_tianhe_service_guide (general_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']
- real_policy_010_auto_ota_management (policy_doc): missing=[]; review_required=0; reasons=['strict_pass_failed', 'evaluation_error', 'mapping_recall_below_threshold', 'mapped_or_review_targets_below_threshold', 'package_invalid']

## Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
