# Real-world Validation Gap Analysis

## Overview

| Documents | Strict pass | Strict fail | Badcase violations |
| ---: | ---: | ---: | ---: |
| 30 | 10 | 20 | 0 |

## Strict Pass/Fail by Document Type

| Document type | Documents | Strict pass | Strict fail |
| --- | ---: | ---: | ---: |
| general_doc | 4 | 0 | 4 |
| meeting_doc | 6 | 0 | 6 |
| policy_doc | 10 | 0 | 10 |
| procurement_doc | 10 | 10 | 0 |

## Top Failed and Review-required Fields

- general_doc: failed=content (4); review-required=application_conditions (4), application_materials (4), category (4), content (4), created_date (4)
- meeting_doc: failed=meeting_date (6), meeting_title (6), content (5); review-required=action_items (6), attendees (6), deadlines (6), decision_items (6), decisions (6)
- policy_doc: failed=content (8), issuer (6), publish_date (6); review-required=effective_date (10), keywords (10), source (10), target_audience (10), content (8)
- procurement_doc: failed=None; review-required=announcement_date (10), procurement_type (10), opening_date (7), budget_amount (6), bid_deadline (1)

## Field Failure Details

- real_general_001_notary_service_guide / application_conditions (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / application_materials (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / category (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / content (validation): Missing required field: content
- real_general_001_notary_service_guide / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / document_subtype (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / process_steps (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / published_at (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / service_object (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_general_001_notary_service_guide / tags (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / application_conditions (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / application_materials (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / category (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / content (validation): Missing required field: content
- real_general_002_biomed_project_guide / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / document_subtype (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / process_steps (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / published_at (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / service_object (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_general_002_biomed_project_guide / tags (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / application_conditions (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / application_materials (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / attachments (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / category (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / contact (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / content (validation): Missing required field: content
- real_general_003_textile_application_flow / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / document_subtype (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / process_steps (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / published_at (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / service_object (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / source (mapping_review): Fuzzy mapping requires human review.
- real_general_003_textile_application_flow / tags (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / application_conditions (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / application_materials (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / attachments (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / category (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / contact (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / content (validation): Missing required field: content
- real_general_004_tianhe_service_guide / created_date (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / document_subtype (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / process_steps (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / published_at (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / service_object (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_general_004_tianhe_service_guide / tags (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / agenda_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / content (validation): Missing required field: content
- real_meeting_001_changning_executive_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / departments (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_001_changning_executive_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_001_changning_executive_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_001_changning_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / content (validation): Missing required field: content
- real_meeting_002_shaxian_executive_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_002_shaxian_executive_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_002_shaxian_executive_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_002_shaxian_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / content (validation): Missing required field: content
- real_meeting_003_miluo_executive_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_003_miluo_executive_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_003_miluo_executive_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_003_miluo_executive_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_004_shandan_2025_11_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_004_shandan_2025_11_minutes / organizer (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_004_shandan_2025_11_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / content (validation): Missing required field: content
- real_meeting_005_miluo_2026_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_005_miluo_2026_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_005_miluo_2026_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_005_miluo_2026_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / action_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / agenda_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / attendees (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / content (validation): Missing required field: content
- real_meeting_006_shandan_minutes / deadlines (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / decision_items (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / decisions (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / departments (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / meeting_date (validation): Missing required field: meeting_date
- real_meeting_006_shandan_minutes / meeting_location (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / meeting_title (validation): Missing required field: meeting_title
- real_meeting_006_shandan_minutes / source (mapping_review): Fuzzy mapping requires human review.
- real_meeting_006_shandan_minutes / topics (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / document_number (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / issuer (validation): Missing required field: issuer
- real_policy_001_training_platform_rules / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / publish_date (validation): Missing required field: publish_date
- real_policy_001_training_platform_rules / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_001_training_platform_rules / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / content (validation): Missing required field: content
- real_policy_002_equipment_renewal / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / issuer (validation): Missing required field: issuer
- real_policy_002_equipment_renewal / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / publish_date (validation): Missing required field: publish_date
- real_policy_002_equipment_renewal / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_002_equipment_renewal / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / document_number (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / issuer (validation): Missing required field: issuer
- real_policy_003_science_education_guide / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / publish_date (validation): Missing required field: publish_date
- real_policy_003_science_education_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_003_science_education_guide / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / content (validation): Missing required field: content
- real_policy_004_student_loan_relief / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / issuer (validation): Missing required field: issuer
- real_policy_004_student_loan_relief / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / publish_date (validation): Missing required field: publish_date
- real_policy_004_student_loan_relief / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_004_student_loan_relief / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / content (validation): Missing required field: content
- real_policy_005_ai_industry_guide / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / issuer (validation): Missing required field: issuer
- real_policy_005_ai_industry_guide / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / publish_date (validation): Missing required field: publish_date
- real_policy_005_ai_industry_guide / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_005_ai_industry_guide / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_006_technology_incubator_rules / content (validation): Missing required field: content
- real_policy_006_technology_incubator_rules / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_006_technology_incubator_rules / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_006_technology_incubator_rules / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_006_technology_incubator_rules / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_007_one_thing_list / content (validation): Missing required field: content
- real_policy_007_one_thing_list / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_007_one_thing_list / issuer (validation): Missing required field: issuer
- real_policy_007_one_thing_list / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_007_one_thing_list / publish_date (validation): Missing required field: publish_date
- real_policy_007_one_thing_list / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_007_one_thing_list / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_008_sme_leader_training / content (validation): Missing required field: content
- real_policy_008_sme_leader_training / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_008_sme_leader_training / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_008_sme_leader_training / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_008_sme_leader_training / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_009_network_safety_work / content (validation): Missing required field: content
- real_policy_009_network_safety_work / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_009_network_safety_work / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_009_network_safety_work / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_009_network_safety_work / target_audience (mapping_review): Fuzzy mapping requires human review.
- real_policy_010_auto_ota_management / content (validation): Missing required field: content
- real_policy_010_auto_ota_management / effective_date (mapping_review): Fuzzy mapping requires human review.
- real_policy_010_auto_ota_management / keywords (mapping_review): Fuzzy mapping requires human review.
- real_policy_010_auto_ota_management / source (mapping_review): Fuzzy mapping requires human review.
- real_policy_010_auto_ota_management / target_audience (mapping_review): Fuzzy mapping requires human review.
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
- real_procurement_006_vaccine_tender / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_006_vaccine_tender / bid_deadline (mapping_review): Fuzzy mapping requires human review.
- real_procurement_006_vaccine_tender / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_007_testing_equipment_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_007_testing_equipment_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_007_testing_equipment_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_007_testing_equipment_award / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_008_desktop_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_008_desktop_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_008_desktop_award / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_009_pollutant_monitoring_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_009_pollutant_monitoring_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_009_pollutant_monitoring_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_009_pollutant_monitoring_award / procurement_type (mapping_review): Fuzzy mapping requires human review.
- real_procurement_010_ultrasound_award / announcement_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_010_ultrasound_award / budget_amount (mapping_review): Fuzzy mapping requires human review.
- real_procurement_010_ultrasound_award / opening_date (mapping_review): Fuzzy mapping requires human review.
- real_procurement_010_ultrasound_award / procurement_id (mapping_review): Fuzzy mapping requires human review.
- real_procurement_010_ultrasound_award / procurement_type (mapping_review): Fuzzy mapping requires human review.

## Recommended Aliases and Regexes

- general_doc.content: alias `page_count` — Observed 2 repeated review-required mappings.
- meeting_doc.meeting_title: alias `标题` — Observed 6 repeated review-required mappings.
- meeting_doc.content: alias `page_count` — Observed 2 repeated review-required mappings.
- meeting_doc.meeting_date: regex `explicit labeled date with unambiguous YYYY-MM-DD value` — meeting_date is missing in 6 meeting_doc document(s); only accept a labeled, single date match.
- policy_doc.publish_date: regex `explicit labeled date with unambiguous YYYY-MM-DD value` — publish_date is missing in 6 policy_doc document(s); only accept a labeled, single date match.

## Fields That Must Stay Review-required

- general_doc.created_date: Fuzzy mapping requires human review.
- meeting_doc.meeting_date: Fuzzy mapping requires human review.
- procurement_doc.announcement_date: Fuzzy mapping requires human review.
- procurement_doc.budget_amount: Fuzzy mapping requires human review.
- procurement_doc.opening_date: Fuzzy mapping requires human review.
- procurement_doc.bid_deadline: Fuzzy mapping requires human review.

## Badcase Warnings

- No violations detected; retain the existing badcase guards.

## Fields Not Recommended for Modification

- general_doc.source: Generic metadata source 'source_url' is not semantic evidence for this target.
- general_doc.created_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- general_doc.category: Generic metadata source 'doc_type' is not semantic evidence for this target.
- general_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- general_doc.tags: Generic metadata source 'doc_type' is not semantic evidence for this target.
- general_doc.document_subtype: Generic metadata source 'doc_type' is not semantic evidence for this target.
- general_doc.published_at: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- general_doc.service_object: Generic metadata source 'source_format' is not semantic evidence for this target.
- general_doc.process_steps: Generic metadata source 'source_site' is not semantic evidence for this target.
- meeting_doc.meeting_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- meeting_doc.attendees: Generic metadata source 'doc_type' is not semantic evidence for this target.
- meeting_doc.source: Generic metadata source 'source_url' is not semantic evidence for this target.
- meeting_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- policy_doc.effective_date: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- policy_doc.target_audience: Generic metadata source 'retrieved_at' is not semantic evidence for this target.
- policy_doc.source: Generic metadata source 'source_url' is not semantic evidence for this target.
- policy_doc.content: Generic metadata source 'extraction_truncated' is not semantic evidence for this target.
- procurement_doc.announcement_date: Generic metadata source 'source_format' is not semantic evidence for this target.
- procurement_doc.opening_date: Generic metadata source 'source_site' is not semantic evidence for this target.
