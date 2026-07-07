# Phase D Strict Validation Failure Analysis

| Metric | Value |
| --- | ---: |
| dataset_size | 50 |
| package_count | 50 |
| strict_pass_count | 39 |
| strict_fail_count | 11 |
| required_missing_count | 2 |
| review_required_count | 21 |
| badcase_violation_count | 0 |
| llm_auto_accepted_count | 0 |

## Remaining Failed Documents

- real_general_011_shanghai_branch_registration (general_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_general_013_zhongshan_import_export_guide (general_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_001_training_platform_rules (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_004_student_loan_relief (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_005_ai_industry_guide (policy_doc): strict_pass_failed, missing_required_fields, mapping_recall_below_threshold; required_missing=['issuer']
- real_policy_011_battery_recycling_rules (policy_doc): strict_pass_failed, missing_required_fields; required_missing=['publish_date']
- real_policy_016_caac_civil_aviation_law (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_017_xinhua_investment_management (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_018_beijing_ecommerce_support (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_019_mof_vat_transition (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
- real_policy_020_customs_foreign_investment_catalog (policy_doc): strict_pass_failed, mapping_recall_below_threshold; required_missing=[]
