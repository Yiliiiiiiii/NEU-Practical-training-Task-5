# Non-procurement Gap Analysis

## Summary

| Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---:|---:|---:|---:|---:|---:|
| 35 | 12 | 70 | 9 | 0.559592 | 0 |

## By Document Type

| Type | Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---|---:|---:|---:|---:|---:|---:|
| general_doc | 10 | 5 | 31 | 0 | 0.629167 | 0 |
| meeting_doc | 10 | 0 | 17 | 3 | 0.434167 | 0 |
| policy_doc | 15 | 7 | 22 | 6 | 0.596825 | 0 |

## Top Missing Required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 3 | 11 月 3 日, 5月20日, 二〇二五年十一月三日, 生成日期 | Required field is missing. required_field_missing | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | issuer | candidate_not_extracted | 3 | issuer or issuing body, 国务院办公厅, 工业和信息化部等部门 | Required field is missing. required_field_missing | enhance_candidate |
| real_policy_005_ai_industry_guide | policy_doc | publish_date | candidate_not_extracted | 3 | 2026年2月11日, publication date or date sentence | Required field is missing. required_field_missing | enhance_candidate |

## Top Review-required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 13 | 自2026年4月1日起施行, 自印发之日起施行 | Expected source evidence produced no mapping candidate. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | created_date | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | document_subtype | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | action_items | candidate_not_extracted | 10 | 会议强调, 会议要求 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_002_biomed_project_guide | general_doc | issuer | candidate_not_extracted | 8 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | document_number | candidate_not_extracted | 5 | paragraph_regex.document_number | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 4 | source_site | Fuzzy mapping requires human review. | add_alias |
| real_general_001_notary_service_guide | general_doc | deadline | candidate_not_extracted | 3 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | organizer | candidate_not_extracted | 3 | 汨罗市人民政府办公室 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 2 | 出席 | Expected source evidence produced no mapping candidate. | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | deadlines | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Candidate Extraction Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_002_equipment_renewal | policy_doc | effective_date | candidate_not_extracted | 12 | 自2026年4月1日起施行 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | document_subtype | candidate_not_extracted | 10 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | action_items | candidate_not_extracted | 10 | 会议强调, 会议要求 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | created_date | candidate_not_extracted | 9 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | deadline | candidate_not_extracted | 9 | 截止时间 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | topics | candidate_not_extracted | 9 | agenda sections, first agenda item, reviewed matters, 习近平主席, 传达学习, 听取全市安全生产 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_002_biomed_project_guide | general_doc | issuer | candidate_not_extracted | 6 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 5 | 汨政办发〔2026〕8号, 第1次, 第49次, 第64次 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | issuer | candidate_not_extracted | 5 | issuer or issuing body, issuing bodies, 八部门署名, 发文机构, 国务院办公厅 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 4 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | service_object | candidate_not_extracted | 4 | service or subject section, 申报主体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | chairperson | candidate_not_extracted | 4 | 于占江主持, 李靖主持, 沈晶主持, 马建国主持 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 4 | 2026年1月15日, 2026年1月7日, meeting date sentence, 二〇二五年十一月三日 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_012_sme_gradient_rules | policy_doc | target_audience | candidate_not_extracted | 4 | 各地主管部门和有关单位, 各省中小企业主管部门, 未成年人网络平台, 老年群体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_011_battery_recycling_rules | policy_doc | policy_measures | candidate_not_extracted | 3 | 根据, 活动内容, 结合实际抓好落实 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 3 | 2025-01-16, publication date or date sentence, signed date | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | deadlines | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_009_kundulun_2026_01_minutes | meeting_doc | decisions | candidate_not_extracted | 2 | 会议原则通过, 原则同意 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | organizer | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | document_number | candidate_not_extracted | 2 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_007_domestic_cooperation_guide | general_doc | application_materials | candidate_not_extracted | 1 | 推荐函 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_009_food_technology_guide | general_doc | contact | candidate_not_extracted | 1 | 咨询电话 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | attendees | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_010_zhangjiagang_64_minutes | meeting_doc | meeting_location | candidate_not_extracted | 1 | 市政府501会议室 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_011_battery_recycling_rules | policy_doc | responsible_departments | candidate_not_extracted | 1 | 负责 | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Alias Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 4 | source_site | Fuzzy mapping requires human review. | add_alias |
| real_policy_002_equipment_renewal | policy_doc | document_number | alias_missing | 2 | paragraph_regex.document_number | Fuzzy mapping requires human review. | add_alias |

## Regex Rule Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_002_shaxian_executive_minutes | meeting_doc | meeting_date | regex_missing | 4 | 2026-06-16, 2026年3月6日, meeting sentence, opening sentence | Stable labeled source text lacks a deterministic mapping rule. | add_regex |

## Schema Required-field Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_011_battery_recycling_rules | policy_doc | publish_date | schema_too_strict | 1 |  | Required field is missing. required_field_missing | review_schema |

## Transform / Type Normalization Gaps

- None identified.

## Badcase-sensitive Items

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 7 | 2026年2月11日, signed date, 信息索引, 发布时间, 成文日期, 生成日期 | The authored date is distinct from the explicit publication date. | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 5 | meeting date sentence, 区政府办, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | A responsible office in an action item is not necessarily the meeting organizer. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 3 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The PDF separates a generic attachment marker, title, and subtitle into adjacent blocks; the subtitle is useful for classification but is not a stable category value. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 3 | 出席, 出席会议, 各乡镇、各部门单位 | Responsible organizations in an action paragraph are not necessarily meeting attendees. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 3 | 本办法自2025年7月10日起施行, 自印发之日起施行 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_policy_003_science_education_guide | policy_doc | issuer | badcase_sensitive | 3 | issuer or issuing body, joint issuing bodies, 发文机构, 工业和信息化部等部门 | The extracted body identifies responsible departments but omits the formal joint-order issuer preamble. Required field is missing. required_field_missing | keep_review_required |
| real_general_007_domestic_cooperation_guide | general_doc | issuer | badcase_sensitive | 2 |  | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 2 | 11 月 3 日, 5月20日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. Required field is missing. required_field_missing | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 2 | 2025年12月15日前, 6月9日前 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_general_006_soft_science_guide | general_doc | created_date | badcase_sensitive | 1 |  | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 1 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 1 | paragraph_regex.document_number | Fuzzy mapping requires human review. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 1 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |

## Recommended Fix Plan

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_meeting_001_changning_executive_minutes | meeting_doc | topics | candidate_not_extracted | 9 | agenda sections, first agenda item, reviewed matters, 习近平主席, 传达学习, 听取全市安全生产 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_005_eldercare_technology_guide | general_doc | deadline | candidate_not_extracted | 6 | 截止时间 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 5 | 汨政办发〔2026〕8号, 第1次, 第49次, 第64次 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_001_training_platform_rules | policy_doc | issuer | candidate_not_extracted | 5 | issuer or issuing body, issuing bodies, 八部门署名, 发文机构, 国务院办公厅 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 4 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | service_object | candidate_not_extracted | 4 | service or subject section, 申报主体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | chairperson | candidate_not_extracted | 4 | 于占江主持, 李靖主持, 沈晶主持, 马建国主持 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 4 | 2026年1月15日, 2026年1月7日, meeting date sentence, 二〇二五年十一月三日 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_002_shaxian_executive_minutes | meeting_doc | meeting_date | regex_missing | 4 | 2026-06-16, 2026年3月6日, meeting sentence, opening sentence | Stable labeled source text lacks a deterministic mapping rule. | add_regex |
| real_policy_001_training_platform_rules | policy_doc | source | alias_missing | 4 | source_site | Fuzzy mapping requires human review. | add_alias |
| real_policy_012_sme_gradient_rules | policy_doc | target_audience | candidate_not_extracted | 4 | 各地主管部门和有关单位, 各省中小企业主管部门, 未成年人网络平台, 老年群体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_011_battery_recycling_rules | policy_doc | policy_measures | candidate_not_extracted | 3 | 根据, 活动内容, 结合实际抓好落实 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 3 | 2025-01-16, publication date or date sentence, signed date | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | action_items | candidate_not_extracted | 2 | 会议强调, 会议要求 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_009_kundulun_2026_01_minutes | meeting_doc | decisions | candidate_not_extracted | 2 | 会议原则通过, 原则同意 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_002_equipment_renewal | policy_doc | document_number | alias_missing | 2 | paragraph_regex.document_number | Fuzzy mapping requires human review. | add_alias |
| real_policy_011_battery_recycling_rules | policy_doc | effective_date | candidate_not_extracted | 2 | 自2026年4月1日起施行 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_007_domestic_cooperation_guide | general_doc | application_materials | candidate_not_extracted | 1 | 推荐函 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_009_food_technology_guide | general_doc | contact | candidate_not_extracted | 1 | 咨询电话 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_010_zhangjiagang_64_minutes | meeting_doc | meeting_location | candidate_not_extracted | 1 | 市政府501会议室 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_011_battery_recycling_rules | policy_doc | responsible_departments | candidate_not_extracted | 1 | 负责 | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Do-not-auto-accept List

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 7 | 2026年2月11日, signed date, 信息索引, 发布时间, 成文日期, 生成日期 | The authored date is distinct from the explicit publication date. | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 5 | meeting date sentence, 区政府办, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | A responsible office in an action item is not necessarily the meeting organizer. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 3 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The PDF separates a generic attachment marker, title, and subtitle into adjacent blocks; the subtitle is useful for classification but is not a stable category value. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 3 | 出席, 出席会议, 各乡镇、各部门单位 | Responsible organizations in an action paragraph are not necessarily meeting attendees. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 3 | 本办法自2025年7月10日起施行, 自印发之日起施行 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_policy_003_science_education_guide | policy_doc | issuer | badcase_sensitive | 3 | issuer or issuing body, joint issuing bodies, 发文机构, 工业和信息化部等部门 | The extracted body identifies responsible departments but omits the formal joint-order issuer preamble. Required field is missing. required_field_missing | keep_review_required |
| real_general_007_domestic_cooperation_guide | general_doc | issuer | badcase_sensitive | 2 |  | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 2 | 11 月 3 日, 5月20日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. Required field is missing. required_field_missing | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 2 | 2025年12月15日前, 6月9日前 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_general_006_soft_science_guide | general_doc | created_date | badcase_sensitive | 1 |  | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 1 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 1 | paragraph_regex.document_number | Fuzzy mapping requires human review. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 1 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |
