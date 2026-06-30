# Real-world Validation Gap Analysis

## Overview

| Documents | Strict pass | Strict fail | Badcase violations |
| ---: | ---: | ---: | ---: |
| 16 | 5 | 11 | 0 |

## Strict Pass/Fail by Document Type

| Document type | Documents | Strict pass | Strict fail |
| --- | ---: | ---: | ---: |
| general_doc | 3 | 0 | 3 |
| meeting_doc | 3 | 0 | 3 |
| policy_doc | 5 | 0 | 5 |
| procurement_doc | 5 | 5 | 0 |

## Top Failed and Review-required Fields

- general_doc: failed=content (3); review-required=category (3), content (3), created_date (3), source (3), tags (3)
- meeting_doc: failed=content (3), meeting_date (3), meeting_title (3); review-required=action_items (3), attendees (3), content (3), decisions (3), meeting_date (3)
- policy_doc: failed=issuer (5), publish_date (5), content (3); review-required=effective_date (5), keywords (5), content (3)
- procurement_doc: failed=None; review-required=announcement_date (5), procurement_type (5), budget_amount (3), opening_date (3)

## Field Failure Details

- real_general_001_notary_service_guide / category (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / content (validation): Missing required field: content
- real_general_001_notary_service_guide / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / tags (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / category (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / content (validation): Missing required field: content
- real_general_002_biomed_project_guide / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / tags (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / category (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / content (validation): Missing required field: content
- real_general_003_textile_application_flow / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / source (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / tags (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / content (validation): Missing required field: content
- real_meeting_001_changning_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_001_changning_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_001_changning_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / content (validation): Missing required field: content
- real_meeting_002_shaxian_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_002_shaxian_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_002_shaxian_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / content (validation): Missing required field: content
- real_meeting_003_miluo_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_003_miluo_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_003_miluo_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / issuer (validation): Missing required field: issuer
- real_policy_001_training_platform_rules / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / publish_date (validation): Missing required field: publish_date
- real_policy_002_equipment_renewal / content (validation): Missing required field: content
- real_policy_002_equipment_renewal / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / issuer (validation): Missing required field: issuer
- real_policy_002_equipment_renewal / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / publish_date (validation): Missing required field: publish_date
- real_policy_003_science_education_guide / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / issuer (validation): Missing required field: issuer
- real_policy_003_science_education_guide / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / publish_date (validation): Missing required field: publish_date
- real_policy_004_student_loan_relief / content (validation): Missing required field: content
- real_policy_004_student_loan_relief / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / issuer (validation): Missing required field: issuer
- real_policy_004_student_loan_relief / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / publish_date (validation): Missing required field: publish_date
- real_policy_005_ai_industry_guide / content (validation): Missing required field: content
- real_policy_005_ai_industry_guide / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / issuer (validation): Missing required field: issuer
- real_policy_005_ai_industry_guide / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / publish_date (validation): Missing required field: publish_date
- real_procurement_001_broadcast_security_supervision / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_001_broadcast_security_supervision / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_002_special_equipment_bid / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_002_special_equipment_bid / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_003_radiation_monitoring_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_003_radiation_monitoring_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_003_radiation_monitoring_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_003_radiation_monitoring_award / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_004_veterinary_platform_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_004_veterinary_platform_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_004_veterinary_platform_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_004_veterinary_platform_award / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_005_rehabilitation_equipment_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_005_rehabilitation_equipment_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_005_rehabilitation_equipment_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_005_rehabilitation_equipment_award / procurement_type (mapping_review): Fuzzy mapping requires human review.

## Recommended Aliases and Regexes

- meeting_doc.meeting_title: alias `标题` — Observed 3 repeated review-required mappings.
- meeting_doc.meeting_date: regex `explicit labeled date with unambiguous YYYY-MM-DD value` — meeting_date is missing in 3 meeting_doc document(s); only accept a labeled, single date match.
- policy_doc.publish_date: regex `explicit labeled date with unambiguous YYYY-MM-DD value` — publish_date is missing in 5 policy_doc document(s); only accept a labeled, single date match.

## Fields That Must Stay Review-required

- general_doc.created_date: Fuzzy mapping requires human review.
- meeting_doc.meeting_date: Fuzzy mapping requires human review.
- procurement_doc.announcement_date: Fuzzy mapping requires human review.
- procurement_doc.budget_amount: Fuzzy mapping requires human review.
- procurement_doc.opening_date: Fuzzy mapping requires human review.

## Badcase Warnings

- No violations detected; retain the existing badcase guards.

## Fields Not Recommended for Modification

- general_doc.source: Generic metadata source 'source_url' is not semantic evidence for this target.
- general_doc.created_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- general_doc.category: Generic metadata source 'doc_type' is not semantic evidence for this target.
- general_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- general_doc.tags: Generic metadata source 'doc_type' is not semantic evidence for this target.
- meeting_doc.meeting_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- meeting_doc.attendees: Generic metadata source 'doc_type' is not semantic evidence for this target.
- meeting_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- policy_doc.effective_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- policy_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- procurement_doc.announcement_date: Generic metadata source 'source_format' is not semantic evidence for this target.
- procurement_doc.opening_date: Generic metadata source 'source_site' is not semantic evidence for this target.
