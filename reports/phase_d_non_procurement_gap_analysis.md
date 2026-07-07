# Non-procurement Gap Analysis

## Summary

| Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---:|---:|---:|---:|---:|---:|
| 120 | 88 | 34 | 22 | 0.749355 | 0 |

## By Document Type

| Type | Documents | Strict pass | Review required | Required missing | Average recall | Badcase violations |
|---|---:|---:|---:|---:|---:|---:|
| general_doc | 35 | 33 | 17 | 0 | 0.817517 | 0 |
| meeting_doc | 35 | 27 | 6 | 3 | 0.722619 | 0 |
| policy_doc | 50 | 28 | 11 | 19 | 0.720357 | 0 |

## Top Missing Required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_005_ai_industry_guide | policy_doc | issuer | candidate_not_extracted | 13 | issuer, issuer or issuing body, 工业和信息化部等部门 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | enhance_candidate |
| real_policy_007_one_thing_list | policy_doc | publish_date | candidate_not_extracted | 6 | 1995年10月30日通过, 2025-01-16, 2026年2月2日 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | meeting_date | badcase_sensitive | 3 | 5月20日 | The source omits the year in the meeting sentence; publication context is needed before normalization. Required field is missing. required_field_missing | keep_review_required |

## Top Review-required Fields

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 9 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_policy_006_technology_incubator_rules | policy_doc | issuer | regex_missing | 9 | issuer, 工业和信息化部等部门 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | add_regex |
| real_general_005_eldercare_technology_guide | general_doc | application_conditions | badcase_sensitive | 6 | 申报要求 | Mapping evidence has semantic risk and requires human review. | keep_review_required |
| real_meeting_006_shandan_minutes | meeting_doc | attendees | candidate_not_extracted | 6 | 出席会议 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_007_one_thing_list | policy_doc | publish_date | candidate_not_extracted | 2 | 2025-01-16, 2026年2月2日 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | enhance_candidate |
| real_general_011_shanghai_branch_registration | general_doc | service_object | badcase_sensitive | 1 | 分公司设立登记注册, 申请人为公司 | The FAQ says the applicant should be the company, but it appears inside an error example and should not replace the service-object field automatically. | keep_review_required |
| real_general_011_shanghai_branch_registration | general_doc | summary | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Candidate Extraction Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_general_005_eldercare_technology_guide | general_doc | contact | candidate_not_extracted | 14 | ????, 咨询电话 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_012_sme_gradient_rules | policy_doc | target_audience | candidate_not_extracted | 12 | 各乡镇人民政府等, 各地主管部门和有关单位, 各有关单位, 各省中小企业主管部门, 在京个人消费者, 老年群体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 11 | 2026年第2次常务会议, 2026年第5次常务会议, 汨政办发〔2026〕8号, 第142次常务会议, 第2次常务会议, 第49次, 第62次常务会议 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_008_wlmqx_2026_01_minutes | meeting_doc | topics | candidate_not_extracted | 11 | 传达学习, 传达学习习近平总书记关于生态环境保护, 传达学习全国两会精神, 传达市政府常务会议精神, 听取安全生产工作情况汇报, 研究审议9项议题 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_014_digital_aging_campaign | policy_doc | policy_measures | candidate_not_extracted | 11 | 修订条款, 免征增值税项目, 制定本法, 支持内容及标准, 活动内容, 结合实际抓好落实, 补贴范围和标准 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 9 | 2025-01-16, 2026年2月6日, 2026年3月27日, publication date or date sentence, signed date | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 6 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | action_items | candidate_not_extracted | 6 | 会议强调, 会议要求 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_009_kundulun_2026_01_minutes | meeting_doc | decisions | candidate_not_extracted | 5 | 会议原则同意, 原则同意, 原则通过 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_012_tongguan_food_license | general_doc | service_object | candidate_not_extracted | 3 | 家庭或个人, 申请食品经营许可, 食品经营许可证核发服务事项 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_006_shandan_minutes | meeting_doc | attendees | candidate_not_extracted | 3 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 3 | meeting date sentence | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_016_caac_civil_aviation_law | policy_doc | effective_date | candidate_not_extracted | 3 | 2026年7月1日起施行, 2月9日生效, 自2026年1月1日至2027年12月31日 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_005_ai_industry_guide | policy_doc | issuer | candidate_not_extracted | 3 | issuer or issuing body | Required field is missing. required_field_missing | enhance_candidate |
| real_general_011_shanghai_branch_registration | general_doc | process_steps | candidate_not_extracted | 2 | 办理流程, 申请→受理→办结 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_017_xinhua_investment_management | policy_doc | document_number | candidate_not_extracted | 2 | 公告2026年第10号, 新政发〔2026〕1号 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_011_shanghai_branch_registration | general_doc | summary | candidate_not_extracted | 1 |  | Expected source evidence produced no mapping candidate. | enhance_candidate |

## Alias Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_013_minor_platform_rules | policy_doc | issuer | alias_missing | 3 | issuer | Required field is missing. required_field_missing | add_alias |

## Regex Rule Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_006_technology_incubator_rules | policy_doc | issuer | regex_missing | 3 | issuer | Required field is missing. required_field_missing | add_regex |
| real_general_013_zhongshan_import_export_guide | general_doc | contact | regex_missing | 1 | 咨询电话 | Stable labeled source text lacks a deterministic mapping rule. | add_regex |

## Schema Required-field Gaps

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_011_battery_recycling_rules | policy_doc | publish_date | schema_too_strict | 3 |  | Required field is missing. required_field_missing | review_schema |
| real_policy_016_caac_civil_aviation_law | policy_doc | issuer | schema_too_strict | 1 |  | Required field is missing. required_field_missing | review_schema |

## Transform / Type Normalization Gaps

- None identified.

## Badcase-sensitive Items

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 24 | 1995年10月30日通过, 2026年1月1日, 2026年2月11日, 2026年2月2日, signed date, 信息索引, 成文日期, 生成日期 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 16 | meeting date sentence, 区发展改革委, 区政府办, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | A responsible office in an action item is not necessarily the meeting organizer. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 13 | 出席, 出席会议, 各乡镇、各部门单位, 各单位各部门, 固定列席, 董浜镇要聚焦辖区产业特色 | Fixed observers should remain distinct from formal attendees unless the schema explicitly accepts observer roles. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 10 | 本办法自2025年7月10日起施行, 自印发之日起施行, 自发布之日起生效 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_general_005_eldercare_technology_guide | general_doc | application_conditions | badcase_sensitive | 9 | 一次性告知补齐所有规定的材料, 申报要求, 申请人的身份证, 食品经营许可证申请书 | A required application form is an application material, not an eligibility condition. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 9 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 7 | 2025年12月15日前, 6月9日前, 实施至补贴资金使用完毕截止 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 6 | 11 月 3 日, 5月20日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. | keep_review_required |
| real_policy_004_student_loan_relief | policy_doc | issuer | badcase_sensitive | 6 | issuer or issuing body, joint issuing bodies, 工业和信息化部等部门 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 3 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 3 | 国办函〔2025〕3号 | The document number is concatenated with the repeated title and requires label-aware extraction. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 3 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |
| real_general_011_shanghai_branch_registration | general_doc | service_object | badcase_sensitive | 2 | 分公司设立登记注册, 开展进出口业务企业, 申请人为公司 | The FAQ says the applicant should be the company, but it appears inside an error example and should not replace the service-object field automatically. | keep_review_required |
| real_general_013_zhongshan_import_export_guide | general_doc | application_materials | badcase_sensitive | 1 | 经办人短信验证 | The phrase appears inside an online operation step and should not be treated as a submitted application material without review. | keep_review_required |

## Recommended Fix Plan

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_general_005_eldercare_technology_guide | general_doc | contact | candidate_not_extracted | 14 | ????, 咨询电话 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_012_sme_gradient_rules | policy_doc | target_audience | candidate_not_extracted | 12 | 各乡镇人民政府等, 各地主管部门和有关单位, 各有关单位, 各省中小企业主管部门, 在京个人消费者, 老年群体 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_005_miluo_2026_minutes | meeting_doc | meeting_number | candidate_not_extracted | 11 | 2026年第2次常务会议, 2026年第5次常务会议, 汨政办发〔2026〕8号, 第142次常务会议, 第2次常务会议, 第49次, 第62次常务会议 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_008_wlmqx_2026_01_minutes | meeting_doc | topics | candidate_not_extracted | 11 | 传达学习, 传达学习习近平总书记关于生态环境保护, 传达学习全国两会精神, 传达市政府常务会议精神, 听取安全生产工作情况汇报, 研究审议9项议题 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_014_digital_aging_campaign | policy_doc | policy_measures | candidate_not_extracted | 11 | 修订条款, 免征增值税项目, 制定本法, 支持内容及标准, 活动内容, 结合实际抓好落实, 补贴范围和标准 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_004_student_loan_relief | policy_doc | publish_date | candidate_not_extracted | 9 | 2025-01-16, 2026年2月6日, 2026年3月27日, publication date or date sentence, signed date | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_001_notary_service_guide | general_doc | application_conditions | candidate_not_extracted | 6 | process or condition detail, 申请专项资金支持的单位 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_007_zhenping_49_minutes | meeting_doc | action_items | candidate_not_extracted | 6 | 会议强调, 会议要求 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_009_kundulun_2026_01_minutes | meeting_doc | decisions | candidate_not_extracted | 5 | 会议原则同意, 原则同意, 原则通过 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_012_tongguan_food_license | general_doc | service_object | candidate_not_extracted | 3 | 家庭或个人, 申请食品经营许可, 食品经营许可证核发服务事项 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_meeting_001_changning_executive_minutes | meeting_doc | meeting_date | candidate_not_extracted | 3 | meeting date sentence | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_016_caac_civil_aviation_law | policy_doc | effective_date | candidate_not_extracted | 3 | 2026年7月1日起施行, 2月9日生效, 自2026年1月1日至2027年12月31日 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_005_ai_industry_guide | policy_doc | issuer | candidate_not_extracted | 3 | issuer or issuing body | Required field is missing. required_field_missing | enhance_candidate |
| real_policy_006_technology_incubator_rules | policy_doc | issuer | regex_missing | 3 | issuer | Required field is missing. required_field_missing | add_regex |
| real_policy_013_minor_platform_rules | policy_doc | issuer | alias_missing | 3 | issuer | Required field is missing. required_field_missing | add_alias |
| real_general_011_shanghai_branch_registration | general_doc | process_steps | candidate_not_extracted | 2 | 办理流程, 申请→受理→办结 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_policy_017_xinhua_investment_management | policy_doc | document_number | candidate_not_extracted | 2 | 公告2026年第10号, 新政发〔2026〕1号 | Expected source evidence produced no mapping candidate. | enhance_candidate |
| real_general_013_zhongshan_import_export_guide | general_doc | contact | regex_missing | 1 | 咨询电话 | Stable labeled source text lacks a deterministic mapping rule. | add_regex |

## Do-not-auto-accept List

| Document | Type | Target | Gap | Count | Sources | Reason | Action |
|---|---|---|---|---:|---|---|---|
| real_policy_001_training_platform_rules | policy_doc | publish_date | badcase_sensitive | 24 | 1995年10月30日通过, 2026年1月1日, 2026年2月11日, 2026年2月2日, signed date, 信息索引, 成文日期, 生成日期 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | keep_review_required |
| real_meeting_001_changning_executive_minutes | meeting_doc | organizer | badcase_sensitive | 16 | meeting date sentence, 区发展改革委, 区政府办, 区政府区长吴晓峰, 汨罗市人民政府办公室, 黄国杰 | A responsible office in an action item is not necessarily the meeting organizer. | keep_review_required |
| real_meeting_003_miluo_executive_minutes | meeting_doc | attendees | badcase_sensitive | 13 | 出席, 出席会议, 各乡镇、各部门单位, 各单位各部门, 固定列席, 董浜镇要聚焦辖区产业特色 | Fixed observers should remain distinct from formal attendees unless the schema explicitly accepts observer roles. | keep_review_required |
| real_policy_001_training_platform_rules | policy_doc | effective_date | badcase_sensitive | 10 | 本办法自2025年7月10日起施行, 自印发之日起施行, 自发布之日起生效 | The effective date is explicit but differs from the authored and published dates; retain its distinct date semantics. | keep_review_required |
| real_general_005_eldercare_technology_guide | general_doc | application_conditions | badcase_sensitive | 9 | 一次性告知补齐所有规定的材料, 申报要求, 申请人的身份证, 食品经营许可证申请书 | A required application form is an application material, not an eligibility condition. | keep_review_required |
| real_general_001_notary_service_guide | general_doc | category | badcase_sensitive | 9 | 办理事项及证明材料清单, 建设推广工作网上申报流程说明, 经费额度 | The source/target pair is forbidden or was blocked by a badcase guard. | keep_review_required |
| real_policy_008_sme_leader_training | policy_doc | valid_until | badcase_sensitive | 7 | 2025年12月15日前, 6月9日前, 实施至补贴资金使用完毕截止 | The date is a reporting deadline rather than an explicit policy validity end date. | keep_review_required |
| real_meeting_004_shandan_2025_11_minutes | meeting_doc | meeting_date | badcase_sensitive | 6 | 11 月 3 日, 5月20日, 生成日期 | The page generation timestamp is not the meeting date stated in the narrative. | keep_review_required |
| real_policy_004_student_loan_relief | policy_doc | issuer | badcase_sensitive | 6 | issuer or issuing body, joint issuing bodies, 工业和信息化部等部门 | Mapping evidence has semantic risk and requires human review. Required field is missing. required_field_missing | keep_review_required |
| real_general_004_tianhe_service_guide | general_doc | title | badcase_sensitive | 3 | 人力资源服务发展壮大支持 | The item name wraps across lines and must be merged under the guide heading before choosing the title. | keep_review_required |
| real_policy_007_one_thing_list | policy_doc | document_number | badcase_sensitive | 3 | 国办函〔2025〕3号 | The document number is concatenated with the repeated title and requires label-aware extraction. | keep_review_required |
| real_policy_005_ai_industry_guide | policy_doc | summary | badcase_sensitive | 3 | 揭榜挂帅申报指南 | The first PDF page has a page number, attachment label, title, and subtitle; the subtitle can inform a summary but is not itself a complete summary. | keep_review_required |
| real_general_011_shanghai_branch_registration | general_doc | service_object | badcase_sensitive | 2 | 分公司设立登记注册, 开展进出口业务企业, 申请人为公司 | The FAQ says the applicant should be the company, but it appears inside an error example and should not replace the service-object field automatically. | keep_review_required |
| real_general_013_zhongshan_import_export_guide | general_doc | application_materials | badcase_sensitive | 1 | 经办人短信验证 | The phrase appears inside an online operation step and should not be treated as a submitted application material without review. | keep_review_required |
