# Content Organization Retrieval Evaluation

## Summary

- Queries: 32
- Mean Recall@3: 1.000

## Strategy Comparison

| Strategy | Recall@1 | Recall@3 | MRR | nDCG@5 |
| --- | ---: | ---: | ---: | ---: |
| flat_blocks | 0.500 | 1.000 | 0.750 | 0.815 |
| heading_aware | 0.500 | 1.000 | 0.750 | 0.815 |
| hybrid | 0.500 | 1.000 | 0.750 | 0.815 |
| keyword_enriched | 0.500 | 1.000 | 0.750 | 0.815 |
| table_protected | 0.500 | 1.000 | 0.750 | 0.815 |

## Per Document Type

- general_doc: Recall@3=1.000
- meeting_doc: Recall@3=1.000
- policy_doc: Recall@3=1.000
- procurement_doc: Recall@3=1.000

## Per Query Failure Cases

- real_general_001_notary_service_guide_q02 (flat_blocks)
- real_general_002_biomed_project_guide_q02 (flat_blocks)
- real_general_003_textile_application_flow_q02 (flat_blocks)
- real_meeting_001_changning_executive_minutes_q02 (flat_blocks)
- real_meeting_002_shaxian_executive_minutes_q02 (flat_blocks)
- real_meeting_003_miluo_executive_minutes_q02 (flat_blocks)
- real_policy_001_training_platform_rules_q02 (flat_blocks)
- real_policy_002_equipment_renewal_q02 (flat_blocks)
- real_policy_003_science_education_guide_q02 (flat_blocks)
- real_policy_004_student_loan_relief_q02 (flat_blocks)
- real_policy_005_ai_industry_guide_q02 (flat_blocks)
- real_procurement_001_broadcast_security_supervision_q02 (flat_blocks)
- real_procurement_002_special_equipment_bid_q02 (flat_blocks)
- real_procurement_003_radiation_monitoring_award_q02 (flat_blocks)
- real_procurement_004_veterinary_platform_award_q02 (flat_blocks)
- real_procurement_005_rehabilitation_equipment_award_q02 (flat_blocks)
- real_general_001_notary_service_guide_q02 (heading_aware)
- real_general_002_biomed_project_guide_q02 (heading_aware)
- real_general_003_textile_application_flow_q02 (heading_aware)
- real_meeting_001_changning_executive_minutes_q02 (heading_aware)

## Chunk Quality Statistics

- Average chunk count: 66.12

## Recommendation

- Use the highest-recall strategy as the default, then inspect failure cases for missing title/table context.
