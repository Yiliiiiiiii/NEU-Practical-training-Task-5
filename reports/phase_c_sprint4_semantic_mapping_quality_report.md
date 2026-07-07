# Semantic Mapping Quality Report

## 总体指标

| 指标 | 值 |
| --- | ---: |
| dataset_size | 50 |
| average_recall | 0.7184920634920635 |
| strict_pass_count | 34 |
| strict_total | 50 |
| review_required_count | 11 |
| required_missing_count | 4 |
| badcase_violations | 0 |
| llm_auto_accepted_count | 0 |

## 按文档类型

| doc_type | gap_count |
| --- | ---: |
| general_doc | 27 |
| meeting_doc | 35 |
| policy_doc | 48 |

## 按目标字段

| target_field | gap_count |
| --- | ---: |
| action_items | 2 |
| application_conditions | 11 |
| application_materials | 1 |
| attendees | 6 |
| contact | 6 |
| decisions | 3 |
| document_number | 3 |
| effective_date | 6 |
| issuer | 6 |
| meeting_date | 4 |
| meeting_number | 7 |
| organizer | 6 |
| policy_measures | 7 |
| process_steps | 2 |
| publish_date | 16 |
| service_object | 6 |
| summary | 1 |
| target_audience | 6 |
| title | 1 |
| topics | 7 |
| valid_until | 3 |

## Ranked Fixes

| rank | doc_type | target_field | gap_type | count | action | risk |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | policy_doc | publish_date | candidate_not_extracted | 15 | enhance_candidate_extraction | low |
| 2 | meeting_doc | meeting_number | candidate_not_extracted | 7 | enhance_candidate_extraction | low |
| 3 | meeting_doc | topics | candidate_not_extracted | 7 | enhance_candidate_extraction | low |
| 4 | policy_doc | policy_measures | candidate_not_extracted | 7 | enhance_candidate_extraction | low |
| 5 | general_doc | application_conditions | candidate_extracted_but_not_ranked | 6 | improve_evidence_ranking | medium |
| 6 | general_doc | contact | candidate_not_extracted | 6 | enhance_candidate_extraction | low |
| 7 | general_doc | service_object | candidate_not_extracted | 6 | enhance_candidate_extraction | low |
| 8 | meeting_doc | organizer | candidate_not_extracted | 6 | enhance_candidate_extraction | low |
| 9 | policy_doc | target_audience | candidate_not_extracted | 6 | enhance_candidate_extraction | low |
| 10 | general_doc | application_conditions | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| 11 | meeting_doc | attendees | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| 12 | policy_doc | effective_date | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| 13 | policy_doc | issuer | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| 14 | meeting_doc | meeting_date | candidate_not_extracted | 4 | enhance_candidate_extraction | low |
| 15 | meeting_doc | decisions | candidate_not_extracted | 3 | enhance_candidate_extraction | low |
| 16 | policy_doc | document_number | candidate_not_extracted | 3 | enhance_candidate_extraction | low |
| 17 | policy_doc | valid_until | candidate_not_extracted | 3 | enhance_candidate_extraction | low |
| 18 | general_doc | process_steps | candidate_not_extracted | 2 | enhance_candidate_extraction | low |
| 19 | meeting_doc | action_items | candidate_not_extracted | 2 | enhance_candidate_extraction | low |
| 20 | general_doc | application_materials | candidate_not_extracted | 1 | enhance_candidate_extraction | low |
| 21 | general_doc | title | candidate_not_extracted | 1 | enhance_candidate_extraction | low |
| 22 | meeting_doc | attendees | candidate_extracted_but_not_ranked | 1 | improve_evidence_ranking | medium |
| 23 | policy_doc | effective_date | candidate_extracted_but_not_ranked | 1 | improve_evidence_ranking | medium |
| 24 | policy_doc | summary | candidate_not_extracted | 1 | enhance_candidate_extraction | low |

## Unsafe Candidates

- None

## Strict Validation Failures

- None

## 禁止自动修复项

- Forbidden pairs, medium/low-confidence fuzzy mappings, LLM-only suggestions, and source-untraceable mappings must not be auto accepted.

## 下一步建议

- policy_doc.publish_date: enhance_candidate_extraction (15)
- meeting_doc.meeting_number: enhance_candidate_extraction (7)
- meeting_doc.topics: enhance_candidate_extraction (7)
- policy_doc.policy_measures: enhance_candidate_extraction (7)
- general_doc.application_conditions: improve_evidence_ranking (6)
- general_doc.contact: enhance_candidate_extraction (6)
- general_doc.service_object: enhance_candidate_extraction (6)
- meeting_doc.organizer: enhance_candidate_extraction (6)
- policy_doc.target_audience: enhance_candidate_extraction (6)
- general_doc.application_conditions: enhance_candidate_extraction (5)
