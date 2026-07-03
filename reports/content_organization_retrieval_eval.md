# Content Organization Retrieval Evaluation

## Summary

- Queries: 90
- Mean Recall@3: 0.400

## Strategy Comparison

| Strategy | Recall@1 | Recall@3 | MRR | nDCG@5 |
| --- | ---: | ---: | ---: | ---: |
| flat_blocks | 0.178 | 0.644 | 0.409 | 0.453 |
| heading_aware | 0.233 | 0.367 | 0.345 | 0.318 |
| hybrid | 0.200 | 0.311 | 0.310 | 0.279 |
| keyword_enriched | 0.233 | 0.367 | 0.345 | 0.318 |
| table_protected | 0.200 | 0.311 | 0.310 | 0.279 |

## Per Document Type

- general_doc: Recall@3=0.360
- meeting_doc: Recall@3=0.710
- policy_doc: Recall@3=0.393
- procurement_doc: Recall@3=0.140

## Per Query Failure Cases

- real_policy_001_training_platform_rules_q01 (flat_blocks)
- real_policy_001_training_platform_rules_q02 (flat_blocks)
- real_policy_002_equipment_renewal_q02 (flat_blocks)
- real_policy_003_science_education_guide_q01 (flat_blocks)
- real_policy_003_science_education_guide_q02 (flat_blocks)
- real_policy_004_student_loan_relief_q01 (flat_blocks)
- real_policy_004_student_loan_relief_q02 (flat_blocks)
- real_policy_005_ai_industry_guide_q01 (flat_blocks)
- real_policy_005_ai_industry_guide_q02 (flat_blocks)
- real_procurement_001_broadcast_security_supervision_q01 (flat_blocks)
- real_procurement_001_broadcast_security_supervision_q02 (flat_blocks)
- real_procurement_002_special_equipment_bid_q01 (flat_blocks)
- real_procurement_002_special_equipment_bid_q02 (flat_blocks)
- real_procurement_003_radiation_monitoring_award_q01 (flat_blocks)
- real_procurement_003_radiation_monitoring_award_q02 (flat_blocks)
- real_procurement_004_veterinary_platform_award_q01 (flat_blocks)
- real_procurement_004_veterinary_platform_award_q02 (flat_blocks)
- real_procurement_005_rehabilitation_equipment_award_q01 (flat_blocks)
- real_procurement_005_rehabilitation_equipment_award_q02 (flat_blocks)
- real_meeting_001_changning_executive_minutes_q02 (flat_blocks)

## Chunk Quality Statistics

- Average chunk count: 65.96

## Recommendation

- Use the highest-recall strategy as the default, then inspect failure cases for missing title/table context.
