# 非采购 Mapping 改进计划

## 基线

Average recall `0.3494`；review-required `145`；required missing `18`；strict pass `4/20`；badcase violations `0`。

## 深化前 Analyzer Snapshot

Average recall `0.4211`；review-required `139`；required missing `15`；strict pass `4/20`；badcase violations `0`。

最新 API-backed evaluator 记录 average recall `0.5677551020408163`、review-required `69`、required missing `6`、strict pass `13/35`、package verification `35/35`、badcase violations `0`。既定 recall 与 review-required 阈值已达到；剩余重点是 meeting/policy strict validity 与 required-field 缺口。

## 深化后验收结果

在扩展到 35 个非采购样本后，干净数据库上的 API-backed evaluator 结果为：

```text
average recall: 0.5677551020408163
review-required: 69
required missing: 6
package verification: 35/35
badcase violations: 0
```

已完成的窄修复包括：通用申报主体/申报方式候选、会议首段日期/编号/主持人候选、政策落款机构、教育部官方页面发布日期、政府网页发布日期、`source_url` aliases，以及将 fuzzy review 最低相似度由 0.45 收紧到 0.55。低置信度 fuzzy 仍然只能进入 Review，不能自动接受。

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
- `policy_doc.publish_date`：只从明确 publication evidence 增强 extraction；落款成文日期不自动当作发布日期。
- `meeting_doc.meeting_date`：从 meeting date sentence 与中文日期表达增强 extraction。
- `meeting_doc.meeting_number`：从会议编号/发文字号类 evidence 增强 extraction。

## Template Alias 修复

已加入可追溯的 `source_url` aliases、通用申报字段 aliases；删除了会把“成文日期”当作发布日期、把“发布机构”无条件当作发文机关的高风险 aliases。

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

- `retrieved_at -> effective_date`：拒绝并作为 Knowledge Pack badcase control。
- `成文日期 -> publish_date`：保留 Review；除非存在独立、明确的发布日期证据。
- `发布机构 -> issuer`：不作为通用 alias；联合发文或解读机构仍需可追溯证据。

## 验证命令

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
