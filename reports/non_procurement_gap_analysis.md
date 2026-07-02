# Non-procurement Gap Analysis

## Summary

| Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---:|---:|---:|---:|---:|---:|
| 20 | 4 | 139 | 15 | 0.421131 | 0 |

## By Document Type

| Type | Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---|---:|---:|---:|---:|---:|---:|
| general_doc | 4 | 0 | 44 | 0 | 0.333333 | 0 |
| meeting_doc | 6 | 0 | 53 | 3 | 0.333333 | 0 |
| policy_doc | 10 | 4 | 42 | 12 | 0.508929 | 0 |

## Top Missing Required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | issuer | candidate_not_extracted | 6 | issuer or issuing body, issuing bodies, joint issuing bodies, 发文机构, 国务院办公厅 | Required field is missing. required_field_missing | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 6 | 2025-01-16, publication date or date sentence, signed date, 信息索引, 发布时间, 生成日期 | Required field is missing. required_field_missing | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 3 | 11 月 3 日, meeting date sentence, 二〇二五年十一月三日, 生成日期 | Required field is missing. required_field_missing | enhance_candidate |

## Top Review-required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 10 | 本办法自2025年7月10日起施行, 自印发之日起施行 | Expected source evidence produced no mapping candidate. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | keywords | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 10 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_policy_001_training_platform_rules | policy_doc | target_audience | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | action_items | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | attendees | candidate_not_extracted | 6 | 出席 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | deadlines | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | decision_items | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | decisions | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_location | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | source | alias_missing | 6 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_meeting_001_changning_executive_minutes | meeting_doc | topics | candidate_not_extracted | 6 | agenda sections, first agenda item, reviewed matters, 习近平主席 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 4 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_materials | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 4 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | Expected source evidence produced no mapping candidate. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | created_date | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | document_subtype | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | process_steps | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | published_at | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | service_object | candidate_not_extracted | 4 | service or subject section, 申报对象 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | source | alias_missing | 4 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_general_001_notary_service_guide | general_doc | tags | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_003_textile_application_flow | general_doc | attachments | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_003_textile_application_flow | general_doc | contact | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | agenda_items | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | departments | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | document_number | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | organizer | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Candidate Extraction Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | keywords | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | target_audience | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_002_equipment_renewal | policy_doc | effective_date | candidate_not_extracted | 7 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | action_items | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | deadlines | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | decision_items | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | decisions | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_location | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | topics | candidate_not_extracted | 6 | agenda sections, first agenda item, reviewed matters, 习近平主席 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | attendees | candidate_not_extracted | 5 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 4 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_materials | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | created_date | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | document_subtype | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | process_steps | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | published_at | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | tags | candidate_not_extracted | 4 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | issuer | candidate_not_extracted | 4 | issuer or issuing body, issuing bodies, 发文机构, 国务院办公厅 | Required field is missing. required_field_missing | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | service_object | candidate_not_extracted | 3 | service or subject section | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 3 | 2025-01-16, publication date or date sentence, signed date | Required field is missing. required_field_missing | enhance_candidate |
| real_general_003_textile_application_flow | general_doc | attachments | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_003_textile_application_flow | general_doc | contact | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | agenda_items | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | departments | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 2 | meeting date sentence, 二〇二五年十一月三日 | Required field is missing. required_field_missing | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | document_number | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_004_tianhe_service_guide | general_doc | category | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 1 | 汨政办发〔2026〕8号 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | organizer | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Alias Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 10 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_meeting_001_changning_executive_minutes | meeting_doc | source | alias_missing | 6 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_general_001_notary_service_guide | general_doc | source | alias_missing | 4 | source_url | Fuzzy mapping requires human review. | add_alias |

## Regex Rule Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_002_shaxian_executive_minutes | meeting_doc | meeting_date | regex_missing | 3 | 2026-06-16, meeting sentence, opening sentence | Stable labeled source text lacks a deterministic mapping rule. | add_regex |
| real_general_004_tianhe_service_guide | general_doc | service_object | regex_missing | 1 | 申报对象 | Stable labeled source text lacks a deterministic mapping rule. | add_regex |

## Schema Required-field Gaps

- None identified.

## Transform / Type Normalization Gaps

- None identified.

## Badcase-sensitive Items

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 4 | meeting date sentence, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | The PDF line is split across two blocks and identifies the chair, not an explicit organizing body. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 3 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The PDF separates a generic attachment marker, title, and subtitle into adjacent blocks; the subtitle is useful for classification but is not a stable category value. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 3 | 本办法自2025年7月10日起施行, 自印发之日起施行 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 3 | signed date, 信息索引, 发布时间, 生成日期 | The flattened table cell combines an index, generated date, and issuing body; it must be parsed into subfields before any mapping. Required field is missing. required_field_missing | keep_review_required |
| real_policy_003_science_education_guide | policy_doc | issuer | badcase_sensitive | 2 | issuer or issuing body, joint issuing bodies, 发文机构 | Required field is missing. required_field_missing | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 2 | 2025年12月15日前, 6月9日前 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 1 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 1 | 出席 | The document distinguishes attendees, invited observers, government-office observers, and departmental observers; those roles should not be merged automatically. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 1 | 11 月 3 日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. Required field is missing. required_field_missing | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 1 | 国办函〔2025〕3号 | The document number is concatenated with the repeated title and requires label-aware extraction. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 1 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |

## Recommended Fix Plan

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 10 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_meeting_001_changning_executive_minutes | meeting_doc | source | alias_missing | 6 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_meeting_001_changning_executive_minutes | meeting_doc | topics | candidate_not_extracted | 5 | agenda sections, first agenda item, reviewed matters, 习近平主席 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 4 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | source | alias_missing | 4 | source_url | Fuzzy mapping requires human review. | add_alias |
| real_policy_001_training_platform_rules | policy_doc | issuer | candidate_not_extracted | 4 | issuer or issuing body, issuing bodies, 发文机构, 国务院办公厅 | Required field is missing. required_field_missing | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | service_object | candidate_not_extracted | 3 | service or subject section | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | meeting_date | regex_missing | 3 | 2026-06-16, meeting sentence, opening sentence | Stable labeled source text lacks a deterministic mapping rule. | add_regex |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 3 | 2025-01-16, publication date or date sentence, signed date | Required field is missing. required_field_missing | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 2 | meeting date sentence, 二〇二五年十一月三日 | Required field is missing. required_field_missing | enhance_candidate |
| real_general_004_tianhe_service_guide | general_doc | service_object | regex_missing | 1 | 申报对象 | Stable labeled source text lacks a deterministic mapping rule. | add_regex |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 1 | 汨政办发〔2026〕8号 | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Do-not-auto-accept List

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 4 | meeting date sentence, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | The PDF line is split across two blocks and identifies the chair, not an explicit organizing body. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 3 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The PDF separates a generic attachment marker, title, and subtitle into adjacent blocks; the subtitle is useful for classification but is not a stable category value. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 3 | 本办法自2025年7月10日起施行, 自印发之日起施行 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 3 | signed date, 信息索引, 发布时间, 生成日期 | The flattened table cell combines an index, generated date, and issuing body; it must be parsed into subfields before any mapping. Required field is missing. required_field_missing | keep_review_required |
| real_policy_003_science_education_guide | policy_doc | issuer | badcase_sensitive | 2 | issuer or issuing body, joint issuing bodies, 发文机构 | Required field is missing. required_field_missing | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 2 | 2025年12月15日前, 6月9日前 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 1 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 1 | 出席 | The document distinguishes attendees, invited observers, government-office observers, and departmental observers; those roles should not be merged automatically. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 1 | 11 月 3 日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. Required field is missing. required_field_missing | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 1 | 国办函〔2025〕3号 | The document number is concatenated with the repeated title and requires label-aware extraction. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 1 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |
