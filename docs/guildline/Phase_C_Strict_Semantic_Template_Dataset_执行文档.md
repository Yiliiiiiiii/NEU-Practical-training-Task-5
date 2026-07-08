# Phase C：Strict Semantic Consistency、Template 映射完善与真实样本泛化执行文档

> 交付对象：Codex 代码执行代理  
> 适用项目：SchemaPack Agent / 课题 5 数据格式标准化转换智能体  
> 前置阶段：Phase B+ Review 已完成  
> 本阶段目标：在不牺牲 badcase 安全、不放宽 schema、不自动接受低置信 review 的前提下，继续提升非采购真实复杂文档的 strict semantic consistency、template 映射覆盖和数据集泛化可信度。

---

## 0. 当前状态与阶段判断

Phase B+ 已达成阶段目标。当前最终评测口径如下：

| 指标 | 当前结果 | Phase B+ 目标 | 状态 |
|---|---:|---:|---|
| Dataset size | 35 | 35 | 达成 |
| Average recall | 0.705 | >= 0.70 | 达成 |
| Strict pass | 25/35 | >= 24/35 | 达成 |
| Review required | 12 | <= 45 | 大幅达成 |
| Required missing | 2 | <= 2 | 达成 |
| Badcase violations | 0 | 0 | 达成 |
| Package verification pass | 35/35 | 35/35 | 达成 |

Phase B+ 的成功点：

1. mapping recall 已跨过 0.70 阶段线；
2. strict pass 已达到 25/35；
3. review-required 从高位下降到 12；
4. required missing 已降到 2；
5. badcase violations 和 LLM auto accepted 均保持 0；
6. Codex Review Assistant 没有误 approve 低置信或高风险项，12 条 pending 全部 keep_pending，说明安全边界有效。

本阶段不再以“大幅降低 review-required”为主目标，而是进入 **Phase C：严格语义一致性 + Template 安全扩展 + 样本泛化验证**。

---

## 1. 总体策略

上一轮结论是：

```text
有必要继续扩大样本，也有必要完善 template 映射关系，但顺序应该是：
先修高频字段抽取和 strict validation
再完善 template alias / regex / forbidden pairs
再用 Codex Review 做安全人审闭环
最后扩充真实复杂样本验证泛化能力
```

本执行文档将该结论拆成 5 个顺序执行的 Sprint：

```text
Sprint 0：统一评测口径和报告生成链路
Sprint 1：修复当前 35 个非采购样本中的 P0/P1 高价值缺口
Sprint 2：完善 template 映射、regex、conditional alias 与 forbidden pairs
Sprint 3：Codex Review 安全闭环与 Knowledge Pack 影响预览
Sprint 4：扩充真实复杂样本到 50 个非采购样本并验证泛化
```

核心原则：

1. **不通过删 required fields 提高 strict pass。**
2. **不通过关闭 badcase filter 提高 recall。**
3. **不让 LLM suggestion 自动 accepted。**
4. **不把 low/medium confidence fuzzy mapping 自动 approve。**
5. **不把 package verification 等同于 strict semantic validation。**
6. **新增 alias/regex/template 必须有 source-backed evidence 和 badcase 覆盖。**
7. **扩样本应优先增加复杂真实样本，而不是增加容易通过的样本。**

---

## 2. 本阶段目标

### 2.1 当前 35 个非采购样本目标

| 指标 | 当前 | Phase C 目标 |
|---|---:|---:|
| Average recall | 0.705 | >= 0.74 |
| Strict pass | 25/35 | >= 30/35 |
| Review required | 12 | <= 10，不强求清零 |
| Required missing | 2 | 0 或 <= 1 |
| Badcase violations | 0 | 0 |
| LLM auto accepted | 0 | 0 |
| Package verification | 35/35 | 35/35 |

### 2.2 扩展到 50 个非采购样本后的目标

扩展样本后指标可能短期波动，因此扩展集目标略低于 35 样本目标：

| 指标 | Expanded non-procurement 目标 |
|---|---:|
| Non-procurement dataset size | >= 50 |
| Average recall | >= 0.68，理想 >= 0.70 |
| Strict pass rate | >= 60%，理想 >= 65% |
| Required missing rate | <= 8% |
| Badcase violations | 0 |
| LLM auto accepted | 0 |
| Package verification | 100% |

---

## 3. Sprint 0：统一评测口径和报告链路

### 3.1 背景

Phase B+ 最终 evaluator 显示：

```text
strict pass = 25/35
required missing = 2
review required = 12
average recall = 0.705
```

但 strict validation failure analysis 报告中仍出现：

```text
validation passed = 17
validation failed = 18
required missing = 6
```

这说明两个报告可能存在如下问题之一：

1. 使用了不同时间点的 package root；
2. 使用了不同 strict validation 定义；
3. strict failure analyzer 没有读取最终 Phase B+ 产物；
4. evaluator 和 analyzer 对 `review-required`、`enum_invalid`、`mapping_recall_below_threshold` 的口径不一致；
5. 报告缓存未清理。

### 3.2 任务

#### Task 0.1：审查报告脚本输入输出

检查以下脚本：

```text
scripts/eval_non_procurement_mapping.py
scripts/analyze_strict_validation_failures.py
scripts/analyze_semantic_mapping_quality.py
scripts/analyze_non_procurement_gaps.py
```

确认它们读取的路径是否一致：

```text
reports/real_world_packages
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
reports/non_procurement_baseline_report.json
```

#### Task 0.2：为所有 Phase C 报告增加 run metadata

所有评测报告 JSON/Markdown 必须包含：

```json
{
  "run_id": "phase_c_<timestamp>",
  "generated_at": "ISO-8601",
  "git_branch": "...",
  "git_commit": "...",
  "packages_root": "reports/real_world_packages",
  "gold_path": "examples/real_world/gold/mapping_gold.jsonl",
  "badcases_path": "examples/real_world/gold/real_world_badcases.jsonl",
  "dataset_size": 35,
  "report_version": "phase_c_v1"
}
```

#### Task 0.3：统一 strict validation 口径

定义统一口径：

```text
strict_pass = schema required fields satisfied
              AND no strict type/enum/date/list validation error
              AND no high-risk semantic review-required issue for required field
              AND mapping recall for the case >= configured threshold
```

注意：package verification 不计入 strict semantic validation。

#### Task 0.4：新增报告一致性检查脚本

新增：

```text
scripts/check_phase_c_report_consistency.py
```

功能：

1. 读取以下报告：
   - `reports/non_procurement_mapping_eval_report.json`
   - `reports/semantic_mapping_quality_report.json`
   - `reports/strict_validation_failure_analysis.json`
2. 校验核心指标是否一致或可解释：
   - dataset_size
   - strict_pass_count
   - required_missing_count
   - review_required_count
   - badcase_violations
   - llm_auto_accepted_count
3. 如果不一致，输出具体差异和来源。
4. 生成：
   - `reports/phase_c_report_consistency.json`
   - `reports/phase_c_report_consistency.md`

### 3.3 验收

```text
reports/phase_c_report_consistency.json 存在
所有报告 dataset_size 一致
strict_pass_count 口径差异有明确解释或已统一
required_missing_count 口径差异有明确解释或已统一
badcase_violations 均为 0
llm_auto_accepted_count 均为 0
```

---

## 4. Sprint 1：修复当前 35 样本中的 P0/P1 高价值缺口

### 4.1 当前 ranked fixes

Phase B+ 之后，最重要的缺口如下：

| 优先级 | doc_type | target_field | gap_type | count | action | risk |
|---|---|---|---|---:|---|---|
| P0 | policy_doc | doc_type | transform_invalid | 15 | improve_transform_normalizer | medium |
| P0 | policy_doc | publish_date | candidate_not_extracted | 8 | enhance_candidate_extraction | low |
| P1 | general_doc | application_conditions | candidate_extracted_but_not_ranked | 6 | improve_evidence_ranking | medium |
| P1 | meeting_doc | meeting_date | candidate_not_extracted | 6 | enhance_candidate_extraction | low |
| P1 | meeting_doc | organizer | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| P1 | policy_doc | effective_date | candidate_not_extracted | 5 | enhance_candidate_extraction | low |
| P1 | general_doc | service_object | candidate_not_extracted | 4 | enhance_candidate_extraction | low |
| P1 | meeting_doc | topics | candidate_not_extracted | 4 | enhance_candidate_extraction | low |
| P1 | policy_doc | target_audience | candidate_not_extracted | 4 | enhance_candidate_extraction | low |

本 Sprint 只处理 P0/P1，不做扩样本。

---

### 4.2 Task 1.1：修复 `policy_doc.doc_type enum_invalid`

#### 背景

15 个 policy_doc 全部出现：

```text
policy_doc.doc_type: enum_invalid
```

这不是 candidate extraction 问题，而是 transform normalizer / enum map 问题。应优先修，因为收益大、风险低。

#### 要求

检查：

```text
backend/app/services/transform_service.py
backend/app/services/validation_service.py
backend/app/schemas/target_schema.py
examples/production_like/schemas/policy_doc_v1.json
examples/production_like/mapping_templates/policy_doc_base_v1.json
```

确认 schema 允许的 doc_type enum 值，例如：

```text
policy_doc
policy
政策文件
```

统一成 schema 允许的 canonical value。

#### 实现建议

新增或增强：

```text
DocTypeNormalizer
```

规则：

```python
DOC_TYPE_ENUM_MAP = {
    "政策": "policy_doc",
    "政策文件": "policy_doc",
    "政策通知": "policy_doc",
    "通知": "policy_doc",
    "办法": "policy_doc",
    "规则": "policy_doc",
    "指南": "policy_doc",
    "policy": "policy_doc",
    "policy_doc": "policy_doc",
}
```

注意：

1. 只规范 doc_type 字段；
2. 不根据标题强行改变 schema_id；
3. 不影响 general_doc、meeting_doc、procurement_doc；
4. 若输入值无法识别，保持原值并输出 transform warning。

#### 测试

新增：

```text
backend/tests/test_transform_doc_type_normalizer.py
```

覆盖：

```text
政策 -> policy_doc
政策文件 -> policy_doc
policy -> policy_doc
policy_doc -> policy_doc
会议纪要 不应映射到 policy_doc
unknown_type 保持 warning
```

---

### 4.3 Task 1.2：增强 `policy_doc.publish_date` candidate extraction

#### 背景

`policy_doc.publish_date` 仍有 8 个 candidate_not_extracted，且最终 required missing 中仍有 publish_date 缺口。

#### 安全原则

可以作为 publish_date 的证据：

```text
发布日期
发布时间
发布于
公开日期
官网 metadata.publish_date
official page field: publish_date
source HTML structured field: 发布日期
```

不能自动作为 publish_date 的证据：

```text
成文日期
印发日期
施行日期
生效日期
retrieved_at
抓取时间
网页缓存时间
```

#### 实现位置

```text
backend/app/services/candidate_service.py
backend/tests/test_candidate_service_non_procurement.py
```

#### 实现建议

新增或增强：

```python
extract_policy_publish_date_candidates(uir)
```

候选优先级：

1. metadata 中明确 `publish_date` / `发布日期` / `发布时间`；
2. table row key 为 `发布日期` / `发布时间`；
3. 正文近标题区域出现 `发布日期：YYYY-MM-DD`；
4. 官方网页字段块中出现 `发布日期`；
5. 正文中 `YYYY年M月D日发布` 可作为中置信候选；
6. 落款日期只可作为 issue/effective 候选，不得自动转 publish_date。

每个候选必须带：

```json
{
  "target_hint": "publish_date",
  "source_path": "...",
  "source_blocks": ["..."],
  "evidence_type": "metadata_publish_date|table_publish_date|page_field_publish_date|sentence_publish_date",
  "risk_flags": []
}
```

---

### 4.4 Task 1.3：增强 `policy_doc.effective_date` candidate extraction

#### 背景

`policy_doc.effective_date` 仍有 5 个 candidate_not_extracted。

#### 安全原则

可以作为 effective_date 的证据：

```text
自 YYYY年M月D日起施行
自发布之日起施行
本办法自...起施行
施行日期
生效日期
有效期自...至...
```

不能自动作为 effective_date 的证据：

```text
发布日期
成文日期
retrieved_at
```

#### 实现建议

新增或增强：

```python
extract_policy_effective_date_candidates(uir)
```

处理 `自发布之日起施行` 时：

1. 如果 publish_date 已有高可信候选，可派生 effective_date = publish_date，但必须记录 derived_from；
2. 如果 publish_date 不存在，则 effective_date review-required，不要强行填值。

输出 trace：

```json
{
  "target_hint": "effective_date",
  "source_value": "自发布之日起施行",
  "normalized_value": "2025-...",
  "derived_from": "publish_date",
  "requires_source_field": "publish_date"
}
```

---

### 4.5 Task 1.4：增强 `meeting_doc.meeting_date`

#### 背景

`meeting_doc.meeting_date` 仍有 6 个 candidate_not_extracted。

#### 可接受证据

```text
会议时间：YYYY年M月D日
召开时间：YYYY年M月D日
YYYY年M月D日召开会议
于YYYY年M月D日召开第X次会议
会议于...召开
```

#### 禁止误用

```text
发布日期
发布时间
网页抓取时间
正文引用的历史日期
下一次会议日期
```

#### 实现建议

新增或增强：

```python
extract_meeting_date_candidates(uir)
```

候选分级：

| evidence_type | confidence_hint | 说明 |
|---|---:|---|
| explicit_meeting_time_field | 0.95 | `会议时间` / `召开时间` |
| meeting_opening_sentence | 0.85 | `YYYY年...召开会议` |
| title_near_date | 0.65 | 标题附近日期，review-required |
| unrelated_date | blocked | 发布日期、抓取日期 |

---

### 4.6 Task 1.5：增强 `meeting_doc.organizer`

#### 背景

`meeting_doc.organizer` 仍有 5 个 candidate_not_extracted，review-required 中也有 organizer fuzzy 项。

#### 可接受证据

```text
主办单位
组织单位
召集单位
会议由XX主持召开
XX组织召开会议
XX召开专题会议
```

#### 注意区分

```text
chairperson / 主持人 != organizer
attendees / 参会人员 != organizer
承办单位 可能是 organizer，但不一定是 policy issuer
```

#### 实现建议

新增或增强：

```python
extract_meeting_organizer_candidates(uir)
```

对 `XX组织召开会议`、`XX召开会议` 的句式，只在 XX 是机构名样式时生成候选。否则 keep review-required。

---

### 4.7 Task 1.6：增强 `meeting_doc.topics`

#### 背景

`meeting_doc.topics` 仍有 4 个 candidate_not_extracted。

#### 可接受证据

```text
会议议题
议题
审议事项
会议研究了...
会议审议通过...
会议听取了...
一、关于...
二、关于...
```

#### 实现建议

新增或增强：

```python
extract_meeting_topics_candidates(uir)
```

策略：

1. 优先读取标题路径包含 `议题`、`审议事项`、`会议内容` 的 section；
2. 识别首段中的 `研究了/审议了/听取了/原则同意` 后面的事项；
3. 识别编号列表小标题；
4. 输出 list 候选；
5. 无法安全切分时输出单项 list 并带 `list_split_review_required` flag。

---

### 4.8 Task 1.7：改善 `general_doc.application_conditions` ranking

#### 背景

`general_doc.application_conditions` 当前主要问题是 `candidate_extracted_but_not_ranked`，说明候选存在，但 MappingService 排序没有选中。

#### 实现位置

```text
backend/app/services/mapping_service.py
backend/tests/test_mapping_service_evidence_ranking.py
```

#### Ranking 提升规则

对 `application_conditions` 增加 context boost：

```text
section title contains 申请条件 / 受理条件 / 办理条件 / 申报条件
paragraph contains 应具备 / 符合以下条件 / 满足以下条件
table key exact 申请条件 / 受理条件 / 办理条件
```

风险惩罚：

```text
申请材料 != application_conditions
办理流程 != application_conditions
联系方式 != application_conditions
```

---

### 4.9 Task 1.8：增强 `general_doc.service_object`

#### 可接受证据

```text
服务对象
适用对象
申报对象
支持对象
面向对象
申请主体
申报主体
```

#### 禁止误用

```text
联系人 != service_object
承办单位 != service_object
咨询电话 != service_object
```

---

### 4.10 Sprint 1 验收命令

先启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另一个终端运行：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_candidate_service_non_procurement.py -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_transform_doc_type_normalizer.py -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_mapping_service_evidence_ranking.py -q

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\analyze_semantic_mapping_quality.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\semantic_mapping_quality_report.json --markdown reports\semantic_mapping_quality_report.md
```

Sprint 1 验收：

```text
average_recall >= 0.72
strict_pass >= 28/35
required_missing <= 1
badcase_violations = 0
llm_auto_accepted_count = 0
package verification = 35/35
```

---

## 5. Sprint 2：完善 template 映射关系、regex 与 forbidden pairs

### 5.1 原则

template 映射要完善，但不能乱加。优先级：

```text
safe exact alias > conditional alias > regex rule > evidence ranking > review-required suggestion
```

每新增一条 alias/regex 必须满足：

1. 有真实样本证据；
2. 有正例测试；
3. 有反例测试；
4. 不命中 forbidden pair；
5. mapping_report 能输出 evidence；
6. 不降低 badcase safety。

---

### 5.2 推荐新增 safe aliases

#### general_doc

```json
[
  {"source": "服务对象", "target": "service_object"},
  {"source": "适用对象", "target": "service_object"},
  {"source": "申报对象", "target": "service_object"},
  {"source": "支持对象", "target": "service_object"},
  {"source": "申请主体", "target": "service_object"},
  {"source": "申报主体", "target": "service_object"},
  {"source": "申请条件", "target": "application_conditions"},
  {"source": "受理条件", "target": "application_conditions"},
  {"source": "办理条件", "target": "application_conditions"},
  {"source": "申报条件", "target": "application_conditions"}
]
```

#### meeting_doc

```json
[
  {"source": "会议时间", "target": "meeting_date"},
  {"source": "召开时间", "target": "meeting_date"},
  {"source": "会议日期", "target": "meeting_date"},
  {"source": "会议议题", "target": "topics"},
  {"source": "议题", "target": "topics"},
  {"source": "审议事项", "target": "topics"},
  {"source": "会议内容", "target": "topics"},
  {"source": "主办单位", "target": "organizer"},
  {"source": "组织单位", "target": "organizer"},
  {"source": "召集单位", "target": "organizer"}
]
```

#### policy_doc

```json
[
  {"source": "发布日期", "target": "publish_date", "conditions": {"source_context": ["metadata", "official_page_field", "table_key"]}},
  {"source": "发布时间", "target": "publish_date", "conditions": {"source_context": ["metadata", "official_page_field", "table_key"]}},
  {"source": "公开日期", "target": "publish_date", "conditions": {"source_context": ["metadata", "official_page_field", "table_key"]}},
  {"source": "施行日期", "target": "effective_date"},
  {"source": "生效日期", "target": "effective_date"},
  {"source": "有效期", "target": "valid_until"},
  {"source": "适用对象", "target": "target_audience"},
  {"source": "适用范围", "target": "target_audience"},
  {"source": "政策措施", "target": "policy_measures"},
  {"source": "主要措施", "target": "policy_measures"}
]
```

注意：policy_doc 中 `发布日期 -> publish_date` 只能做 conditional alias，不允许全局裸 alias。

---

### 5.3 推荐 regex rules

#### meeting_date

```regex
(?P<meeting_date>\d{4}年\d{1,2}月\d{1,2}日)\s*(召开|举行).{0,20}(会议|常务会议|专题会议)
(会议时间|召开时间|会议日期)[:：\s]*(?P<meeting_date>\d{4}[年\-/\.][\d]{1,2}[月\-/\.][\d]{1,2}日?)
```

#### meeting_number

```regex
第(?P<meeting_number>[一二三四五六七八九十百千万\d]+)次会议
第(?P<meeting_number>\d+)号会议纪要
会议纪要第(?P<meeting_number>\d+)期
```

#### effective_date

```regex
自(?P<effective_date>\d{4}年\d{1,2}月\d{1,2}日)起施行
本(办法|规则|通知|意见).{0,10}自(?P<effective_date>\d{4}年\d{1,2}月\d{1,2}日)起施行
```

#### publish_date

```regex
(发布日期|发布时间|公开日期)[:：\s]*(?P<publish_date>\d{4}[年\-/\.]\d{1,2}[月\-/\.]\d{1,2}日?)
```

---

### 5.4 forbidden pairs / negative knowledge 必须补齐

新增或确认以下 forbidden pairs：

```json
[
  {"source": "成文日期", "forbidden_target": "publish_date", "reason": "issue date is not necessarily publication date"},
  {"source": "发布日期", "forbidden_target": "effective_date", "reason": "publication date is not necessarily effective date"},
  {"source": "retrieved_at", "forbidden_target": "effective_date", "reason": "retrieval timestamp is not a legal effective date"},
  {"source": "抓取时间", "forbidden_target": "publish_date", "reason": "crawl time is not publication date"},
  {"source": "主持人", "forbidden_target": "attendees", "reason": "chairperson is not attendee list"},
  {"source": "联系人", "forbidden_target": "attendees", "reason": "contact person is not attendee list"},
  {"source": "联系人", "forbidden_target": "service_object", "reason": "contact person is not service object"},
  {"source": "承办单位", "forbidden_target": "issuer", "reason": "organizer/undertaker is not necessarily issuer"},
  {"source": "解读机构", "forbidden_target": "issuer", "reason": "interpretation agency is not issuer"},
  {"source": "发布机构", "forbidden_target": "issuer", "condition": "weak_web_metadata_only", "reason": "web publishing organization may not be legal issuer"}
]
```

---

### 5.5 文件修改位置

优先检查：

```text
examples/production_like/mapping_templates/general_doc_base_v1.json
examples/production_like/mapping_templates/meeting_doc_base_v1.json
examples/production_like/mapping_templates/policy_doc_base_v1.json
backend/app/services/effective_template_service.py
backend/app/services/mapping_service.py
backend/tests/test_non_procurement_templates.py
backend/tests/test_badcase_regression.py
```

---

### 5.6 Sprint 2 验收

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_non_procurement_templates.py -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_badcase_regression.py -q
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

验收：

```text
average_recall >= 0.74
strict_pass >= 30/35
required_missing <= 1
badcase_violations = 0
llm_auto_accepted_count = 0
```

---

## 6. Sprint 3：Codex Review 安全闭环与 Knowledge Pack

### 6.1 背景

Phase B+ 后剩余 12 条 review，Codex Review Assistant 在 apply-safe 下全部 keep_pending：

```text
pending_total = 12
applied_approve = 0
applied_reject = 0
kept_pending = 12
```

说明剩余 review 多为 fuzzy / risk flags / low-confidence，不适合自动 approve。

### 6.2 目标

本阶段 Codex 仍然不能无约束执行 review。它只做：

```text
review evidence pack 生成
人工审核辅助报告生成
safe reject forbidden pair
draft knowledge candidate impact preview
```

### 6.3 Task 3.1：生成 Review Evidence Pack

新增或增强：

```text
scripts/build_review_evidence_pack.py
```

输入：

```text
/api/v1/reviews?status=pending
mapping_report.json
lineage field query if available
source UIR blocks
badcase registry
```

输出：

```text
reports/review_evidence_pack.json
reports/review_evidence_pack.md
```

每条 review 输出：

```json
{
  "review_id": "...",
  "doc_id": "...",
  "doc_type": "...",
  "source_label": "...",
  "source_value": "...",
  "target_field": "...",
  "confidence": 0.0,
  "confidence_tier": "low|medium|high",
  "risk_flags": [],
  "badcase_filter": {},
  "review_required_reason": "...",
  "source_path": "...",
  "source_blocks": ["..."],
  "source_excerpt": "...",
  "lineage_available": true,
  "codex_suggestion": "approve|reject|keep_pending",
  "codex_reason": "...",
  "requires_human": true
}
```

### 6.4 Task 3.2：人工审核后才 apply

Codex 不得直接 approve 这些剩余项。流程：

```text
1. Codex 生成 review_evidence_pack
2. 人工在 reports/review_manual_decisions.jsonl 写入 approve/reject/keep_pending
3. Codex 读取 manual decisions
4. 只执行人工明确 decision 的项
5. 执行后生成 apply report
```

人工决策文件格式：

```jsonl
{"review_id":"...","decision":"approve","reason":"source section explicitly says 主办单位","generalization_scope":"same_doc_type","operator":"human"}
{"review_id":"...","decision":"reject","reason":"联系人 is not attendee","generalization_scope":"never","operator":"human"}
```

新增脚本：

```text
scripts/apply_manual_review_decisions.py
```

禁止：

```text
没有 manual decision 的 review 不得修改
operator 不是 human 的 approve 不得执行
LLM-only suggestion 不得 approve
risk_flags high 的项即使 manual approve，也应输出 warning
```

### 6.5 Task 3.3：Knowledge Candidate 安全过滤

Review approve 后生成 knowledge candidates。Codex 可执行：

```text
1. 读取 /api/v1/knowledge/candidates
2. 只处理本轮人工 approved review 生成的 candidate
3. forbidden pair candidate 直接 reject
4. 低证据泛化 candidate keep_pending
5. 只接受 exact/same_doc_type 条件明确的 candidate
```

### 6.6 Task 3.4：Draft Pack + Impact Preview，不自动 activate

Codex 可以创建 draft pack 和 impact report，但不得自动 activate。

新增或使用已有 API 生成：

```text
reports/phase_c_knowledge_pack_impact.json
reports/phase_c_knowledge_pack_impact.md
```

impact report 必须包含：

```json
{
  "new_aliases": [],
  "new_negative_knowledge": [],
  "affected_doc_types": [],
  "affected_fields": [],
  "expected_mapping_changes": [],
  "badcase_check": {
    "violations": 0
  },
  "old_snapshot_unchanged": true,
  "requires_human_activation": true
}
```

### 6.7 Sprint 3 验收

```text
review_evidence_pack generated
manual decisions applied only when present
no automatic approve for low/medium confidence fuzzy
knowledge candidates filtered
no active pack unless explicitly requested by human
badcase violations = 0
old snapshots unchanged
```

---

## 7. Sprint 4：扩充真实复杂样本到 50 个非采购样本

### 7.1 扩样本时机

只有当当前 35 样本满足以下条件后，才扩样本：

```text
average_recall >= 0.72
strict_pass >= 28/35
badcase_violations = 0
llm_auto_accepted_count = 0
report consistency check passed
```

### 7.2 目标分布

当前非采购：

```text
general_doc: 10
meeting_doc: 10
policy_doc: 15
total: 35
```

扩展后目标：

```text
general_doc: 15
meeting_doc: 15
policy_doc: 20
total: 50
```

新增：

```text
general_doc +5
meeting_doc +5
policy_doc +5
```

procurement_doc 可保持 10，不是本阶段重点。

---

### 7.3 新增样本选择原则

必须优先选择复杂真实样本，而不是容易通过的样本。

#### general_doc 新增样本类型

至少覆盖：

```text
1. 服务对象写在表格中的服务指南
2. 申请条件写成长段落或编号列表
3. 申请材料与申请条件容易混淆的文档
4. 办理流程和申请条件混排的文档
5. 联系人/咨询电话明显但不能误当 service_object 的文档
```

#### meeting_doc 新增样本类型

至少覆盖：

```text
1. 会议日期在正文首段而非字段表中
2. 会议议题没有显式“议题”字段，只写“研究了/审议了”
3. 组织者、主持人、参会人员同时出现的会议纪要
4. 会议编号以“第X次会议”或“会议纪要第X期”出现
5. 决议/行动项与议题混合出现的会议纪要
```

#### policy_doc 新增样本类型

至少覆盖：

```text
1. 联合发文政策
2. 政策解读页面，含解读机构但不是 issuer
3. 发布日期、成文日期、生效日期同时出现
4. 目标对象/适用范围隐含在正文中的政策
5. 有效期、施行日期、废止日期存在混杂的政策
```

---

### 7.4 数据源限制

必须遵守：

```text
公开官方材料
无需登录
无需付费
无需 CAPTCHA
无需反爬绕过
非新闻转载
非社交媒体
非个人信息密集材料
优先 HTML 和 text-layer PDF
不引入 scanned PDF/OCR 作为主线
```

生产 runtime 仍从 UIR / External UIR JSON 开始，不做 raw PDF/OCR API。

---

### 7.5 每个新增样本必须补齐的文件

每新增一个样本，必须同步更新：

```text
examples/real_world/sources/source_manifest.json
examples/real_world/uir/<doc_type>/<new_doc>.json
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
examples/real_world/gold/retrieval_queries.jsonl  # 如适用
examples/real_world/reports/extraction_report.{json,md}
examples/real_world/reports/validation_report.{json,md}
```

### 7.6 Gold label 要求

每条 mapping_gold row 至少包含：

```json
{
  "doc_id": "...",
  "doc_type": "policy_doc|meeting_doc|general_doc",
  "target_field": "...",
  "expected": "mapped|review_required|source_not_present",
  "source_paths": ["..."],
  "source_block_ids": ["..."],
  "evidence_excerpt": "...",
  "known_badcases": []
}
```

禁止只标 title/content/source 等容易字段；必须覆盖该 doc_type 的高价值字段。

### 7.7 新增 badcase 要求

每个新增样本如果包含以下歧义，必须写 badcase：

```text
成文日期 vs 发布日期
发布日期 vs 生效日期
解读机构 vs issuer
承办单位 vs issuer
主持人 vs attendees
联系人 vs service_object/attendees
申请材料 vs application_conditions
办理流程 vs application_conditions
预算金额/控制价 vs award_amount
```

---

### 7.8 扩样本执行命令

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

扩样本后验收：

```text
non-procurement dataset >= 50
package verification = 100%
badcase violations = 0
llm_auto_accepted_count = 0
average_recall >= 0.68, ideally >= 0.70
strict_pass_rate >= 60%
required_missing_rate <= 8%
```

---

## 8. Regression Gates 更新

更新：

```text
reports/evaluation_center/current_metrics.json
reports/evaluation_center/regression_gates.json
```

建议新增 Phase C gates：

```json
[
  {"metric": "non_procurement_average_recall_35", "op": ">=", "threshold": 0.74},
  {"metric": "non_procurement_strict_pass_count_35", "op": ">=", "threshold": 30},
  {"metric": "non_procurement_required_missing_35", "op": "<=", "threshold": 1},
  {"metric": "non_procurement_badcase_violations", "op": "==", "threshold": 0},
  {"metric": "llm_auto_accepted_count", "op": "==", "threshold": 0},
  {"metric": "package_verification_rate", "op": ">=", "threshold": 1.0},
  {"metric": "expanded_non_procurement_dataset_size", "op": ">=", "threshold": 50},
  {"metric": "expanded_non_procurement_average_recall", "op": ">=", "threshold": 0.68},
  {"metric": "expanded_non_procurement_strict_pass_rate", "op": ">=", "threshold": 0.60}
]
```

如果扩样本尚未执行，expanded gates 可先标记为 planned，不要让主 gate 误失败。

运行：

```powershell
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

---

## 9. 最终验证命令

完成全部 Sprint 后运行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

如果 routes、request/response schemas 或 API behavior 有变化，重新导出 OpenAPI：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
git diff -- docs\openapi.json
```

API-backed evaluators：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
backend\.venv\Scripts\python.exe scripts\analyze_semantic_mapping_quality.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\semantic_mapping_quality_report.json --markdown reports\semantic_mapping_quality_report.md
backend\.venv\Scripts\python.exe scripts\check_phase_c_report_consistency.py --out reports\phase_c_report_consistency.json --markdown reports\phase_c_report_consistency.md
```

---

## 10. 禁止事项

Codex 必须遵守：

```text
不删除 required fields。
不放宽 schema enum/type/date/list validation 来制造 strict pass。
不关闭 badcase filter。
不让 LLM suggestion 自动 accepted。
不把 low/medium confidence fuzzy mapping 自动 approve。
不把 成文日期 自动映射为 publish_date。
不把 发布日期 自动映射为 effective_date。
不把 retrieved_at / 抓取时间 自动映射为 publish_date 或 effective_date。
不把 发布机构 全局映射为 issuer。
不把 解读机构 映射为 issuer。
不把 承办单位 无条件映射为 issuer。
不把 主持人 映射为 attendees。
不把 联系人 映射为 attendees 或 service_object。
不把 申请材料 映射为 application_conditions。
不把 办理流程 映射为 application_conditions。
不把 package verification 宣称为 strict semantic validation。
不把 raw PDF/OCR 作为本阶段生产 runtime 范围。
不自动 activate knowledge pack，除非用户明确要求。
不修改历史 task snapshot。
```

---

## 11. 交付物清单

### 代码

```text
backend/app/services/candidate_service.py
backend/app/services/mapping_service.py
backend/app/services/transform_service.py
backend/app/services/validation_service.py
examples/production_like/mapping_templates/*.json
scripts/analyze_semantic_mapping_quality.py
scripts/analyze_strict_validation_failures.py
scripts/check_phase_c_report_consistency.py
scripts/build_review_evidence_pack.py
scripts/apply_manual_review_decisions.py
```

### 测试

```text
backend/tests/test_candidate_service_non_procurement.py
backend/tests/test_transform_doc_type_normalizer.py
backend/tests/test_mapping_service_evidence_ranking.py
backend/tests/test_non_procurement_templates.py
backend/tests/test_badcase_regression.py
backend/tests/test_phase_c_report_consistency.py
```

### 报告

```text
reports/non_procurement_mapping_eval_report.json
reports/non_procurement_mapping_eval_report.md
reports/semantic_mapping_quality_report.json
reports/semantic_mapping_quality_report.md
reports/strict_validation_failure_analysis.json
reports/strict_validation_failure_analysis.md
reports/phase_c_report_consistency.json
reports/phase_c_report_consistency.md
reports/review_evidence_pack.json
reports/review_evidence_pack.md
reports/phase_c_knowledge_pack_impact.json
reports/phase_c_knowledge_pack_impact.md
reports/evaluation_center/current_metrics.json
reports/evaluation_center/regression_gates.json
reports/evaluation_center/regression_gate_report.json
```

### 数据集

扩样本后：

```text
examples/real_world/sources/source_manifest.json
examples/real_world/uir/general/*.json
examples/real_world/uir/meeting/*.json
examples/real_world/uir/policy/*.json
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
examples/real_world/gold/retrieval_queries.jsonl
```

---

## 12. 最终完成定义

Phase C 可完成的标准：

### 当前 35 样本

```text
average_recall >= 0.74
strict_pass >= 30/35
required_missing <= 1
review_required <= 10 或保留为人工必要项
badcase_violations = 0
llm_auto_accepted_count = 0
package verification = 35/35
report consistency check passed
```

### 扩展 50 非采购样本

```text
non-procurement dataset >= 50
package verification = 100%
badcase violations = 0
llm_auto_accepted_count = 0
average_recall >= 0.68，理想 >= 0.70
strict_pass_rate >= 60%，理想 >= 65%
source manifest / UIR / gold / badcase 均完整
```

### Review / Knowledge

```text
Codex 不自动 approve 低置信 review
所有 review apply 均来自 explicit manual decision
draft knowledge pack 有 impact report
active knowledge pack 只在用户明确确认后激活
old task snapshots unchanged
```

---

## 13. 推荐执行顺序摘要

```text
1. 先跑 report consistency，统一 Phase B+ 最终口径。
2. 修 policy_doc.doc_type enum_invalid。
3. 修 publish_date/effective_date/meeting_date/organizer/topics/service_object/application_conditions。
4. 完善 safe alias、conditional alias、regex 和 forbidden pairs。
5. 跑 non-procurement evaluator，确保 35 样本指标提升且安全门为 0。
6. 生成 review evidence pack，让人工处理剩余 12 条 review。
7. 对人工 approve/reject 结果生成 knowledge candidate 和 draft pack impact。
8. 用户确认后再 activate knowledge pack。
9. 扩充非采购真实样本到 50 个。
10. 重新跑全量 evaluator、regression gates 和 verify_all。
```

