# 非采购 Mapping 改进计划

## 基线

Average recall `0.3494`；review-required `145`；required missing `18`；strict pass `4/20`；badcase violations `0`。

## 当前 Analyzer Snapshot

Average recall `0.4211`；review-required `139`；required missing `15`；strict pass `4/20`；badcase violations `0`。

API-backed evaluator 当前记录 average recall `0.4211309523809524`、review-required `149`、required missing `12`、package verification `20/20`、badcase violations `0`。Phase 1 仍未达标，因为 recall 与 review-required targets 未达到。

## 高频修复项

| ID | doc_type | target_field | count | gap_type | action | files_to_change | risk | expected_gain |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| F01 | meeting_doc | topics | 5 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 5 topics gaps |
| F02 | general_doc | application_conditions | 4 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 4 application_conditions gaps |
| F03 | policy_doc | issuer | 4 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 4 issuer gaps |
| F04 | general_doc | service_object | 3 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 3 service_object gaps |
| F05 | meeting_doc | meeting_date | 3 | regex_missing | add_regex | examples/production_like/mapping_templates/*.json; backend/tests/test_non_procurement_templates.py | high | reduce 3 meeting_date gaps |
| F06 | policy_doc | publish_date | 3 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 3 publish_date gaps |
| F07 | meeting_doc | meeting_date | 2 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 2 meeting_date gaps |
| F08 | general_doc | service_object | 1 | regex_missing | add_regex | examples/production_like/mapping_templates/*.json; backend/tests/test_non_procurement_templates.py | high | reduce 1 service_object gap |
| F09 | meeting_doc | meeting_number | 1 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 1 meeting_number gap |

## Candidate Extraction 修复方向

- `meeting_doc.topics`：从 agenda sections、first agenda item、reviewed matters 等来源增强 extraction。
- `general_doc.application_conditions`：从 process/condition detail、申请专项资金支持单位等来源增强 extraction。
- `policy_doc.issuer`：从 issuer/issuing body、发文机构、国务院办公厅等来源增强 extraction。
- `general_doc.service_object`：从 service/subject section 增强 extraction。
- `policy_doc.publish_date`：从 publication date/date sentence/signed date 增强 extraction。
- `meeting_doc.meeting_date`：从 meeting date sentence 与中文日期表达增强 extraction。
- `meeting_doc.meeting_number`：从会议编号/发文字号类 evidence 增强 extraction。

## Template Alias 修复

当前 ranked recommendations 中没有选出安全的自动 alias 项。

## Regex Rule 修复

- `meeting_doc.meeting_date`：补充会议日期相关 regex，但必须避免把无关日期误映射为会议日期。
- `general_doc.service_object`：补充申报对象/服务对象相关 regex，并保持 badcase 保护。

## Schema 调整

当前 ranked recommendations 中没有安全的自动 schema 放宽项。不得删除 required fields 来提升指标。

## Transform 修复

当前 ranked recommendations 中没有安全的自动 transform 项。

## Badcase 补充

当前 ranked recommendations 中没有新的自动 badcase 项；已有 forbidden pairs 继续作为 regression gate。

## 拒绝的自动规则

- `policy_doc.source`（10，alias_missing）：拒绝，因为 `source_block_ids` 为空，source label 是 generic metadata。
- `meeting_doc.source`（6，alias_missing）：拒绝，因为 `source_block_ids` 为空，source label 是 generic metadata。
- `general_doc.source`（4，alias_missing）：拒绝，因为 `source_block_ids` 为空，source label 是 generic metadata。

## 验证命令

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
