# Phase H：UIR / 非采购语义映射通过率 0.85 提升执行计划

> 交付对象：Codex 执行工程任务  
> 当前基线：`main@7fd38c77 feat: add phase D/E/F review safety reports`  
> 目标：在不关闭 badcase、不让 LLM 自动接受、不伪造 blind/shadow 指标的前提下，把本地 50-sample 非采购语义映射质量与 strict validation 推近或达到 0.85，并建立可复现的人工审查/DeepSeek 候选治理闭环。

---

## 0. 当前问题判断

当前项目主链路已经稳定：UIR / External UIR 可以导入、执行、生成 Package，并通过 package verifier。真正未达标的是字段语义自动映射与 UIR Quality Gate 自动通过能力。

当前关键指标：

| 指标 | 当前值 | 说明 |
|---|---:|---|
| Real-world import / execution / package verify | 60/60 | 主链路没问题 |
| Real-world mapping recall | 0.6831896552 | 全量真实集语义映射未达 0.85 |
| Phase D / G non-procurement average recall | 0.7426031746 | 本地 50 样本仍未达 0.85 |
| Phase G semantic mapping quality recall | 0.7184920635 | 更严格语义质量口径更低 |
| Strict pass | 39/50 | 约 0.78，还差至少 4 个 strict pass 文档才到 43/50 |
| Required missing | 2 或 4 / 14，取决于报告口径 | 需统一报告口径，并减少 issuer / publish_date 缺失 |
| Review-required | 21 / 22 | 仍高于目标，需要减少低风险 review-required |
| Badcase violations | 0 | 必须保持 |
| LLM auto accepted | 0 | 必须保持 |
| Secret leaks | 0 | 必须保持 |
| Production blind 0.85 | blocked | 没有独立 blind/shadow gold corpus，不能声明 |

根因不是“任务没跑通”，而是：

1. `policy_doc` 是最大瓶颈，尤其是 `publish_date`、`issuer`、`effective_date`、`policy_measures`、`target_audience`、`document_number`、`valid_until`。
2. 很多缺口是 `candidate_not_extracted`，说明候选根本没进池，而不是单纯 ranking 错。
3. `date_format_invalid`、`missing_required`、`semantic_review_required` 同时存在，导致 strict validation pass 卡在 39/50。
4. badcase 与 review-required 策略是故意保守的，不能通过降低安全阈值刷 0.85。
5. 当前 DeepSeek 可达，但本轮 ablation 没有可测贡献，需要把它接入 evidence-linked candidate proposal + simulated human review，而不是 LLM 直接 accepted。
6. 单个 review/knowledge 任务对单样本有效，但无法显著拉动 50 样本平均值，必须按 gap ranking 批量修候选抽取与证据排序。

---

## 1. Phase H 总目标与硬性约束

### 1.1 本地工程目标

Phase H 的目标不是直接宣称 production blind 0.85，而是先达成本地可复现质量门槛：

| Gate | 目标 |
|---|---:|
| `phase_h_non_procurement_mapping_eval.average_recall` | ≥ 0.85，stretch ≥ 0.88 |
| `phase_h_semantic_mapping_quality.average_recall` | ≥ 0.83，stretch ≥ 0.85 |
| `strict_pass` | ≥ 43/50，stretch ≥ 45/50 |
| `required_missing` | ≤ 1，stretch = 0 |
| `review_required` | ≤ 12，stretch ≤ 8 |
| `badcase_violations` | 0，硬约束 |
| `llm_auto_accepted_count` | 0，硬约束 |
| `secret_leaks` | 0，硬约束 |
| `package_verification` | 50/50，硬约束 |
| `report_consistency` | passed，硬约束 |

### 1.2 Production blind 声明约束

即使本地 50-sample 达到 0.85，也不能声明 production blind 0.85，除非完成：

```text
examples/production_shadow/manifest.json
examples/production_shadow/gold/mapping_gold.jsonl
```

并且 blind/shadow corpus 与当前 60-sample real-world corpus 去重，gold labels 冻结，badcase registry 冻结，report status 从 blocked/not_run 变为 passed。

### 1.3 禁止性原则

Codex 执行时不得做以下事情：

- 不关闭 badcase filter。
- 不降低 confidence threshold 来刷指标。
- 不把 `review-required`、`badcase-blocked`、`source-not-present` 静默改为 accepted。
- 不让 DeepSeek / LLM suggestion 自动 accepted。
- 不让 DeepSeek / LLM 激活 schema/template/knowledge pack。
- 不让 draft knowledge pack 影响当前 task。
- 不修改历史 task snapshot。
- 不把 package verification 说成 strict semantic correctness。
- 不把 blocked/not_run 的 blind/shadow 报告说成已达 0.85。
- 不用 gold labels 参与生产 mapping 决策；gold 只能用于 evaluator。

---

## 2. 执行总览

Phase H 分 8 条工作流执行：

| 工作流 | 目标 | 预期收益 |
|---|---|---|
| A. 报告口径统一 | 统一 Phase G/H 指标定义，避免 2、4、14 missing 混乱 | 保证验收可信 |
| B. Gap drilldown 机器可读化 | 输出 doc/field/gap_type/risk/action 明细 | 指导精确修复 |
| C. 候选抽取增强 | 解决 `candidate_not_extracted` 主因 | recall 主提升 |
| D. Evidence ranking 增强 | 解决 `candidate_extracted_but_not_ranked` | review 降低、precision 提升 |
| E. Strict validation 修复 | 日期格式、required missing、semantic review | strict pass 提升 |
| F. Simulated Human Review + DeepSeek 审查闭环 | 让 DeepSeek 只产候选，由子智能体/规则模拟人工审查 | 安全利用 LLM |
| G. Review → Knowledge Pack 安全激活 | 把安全 approve 的 alias/pattern 沉淀为 future-task knowledge | 持续增益 |
| H. Blind/shadow corpus scaffold | 补齐生产 0.85 声明的前置条件 | 为最终验收铺路 |

---

## 3. 工作流 A：报告口径统一

### 3.1 问题

当前多个报告对 missing/review/recall 的口径不同：

- `phase_g_non_procurement_mapping_eval_report`：recall 0.7426031746，strict pass 39，missing 2，review 21。
- `phase_g_semantic_mapping_quality_report`：recall 0.7184920635，strict pass 34，missing 4，review 11。
- `phase_g_strict_validation_failure_analysis`：required missing 14，review-required 22。

这些可能分别统计：文档级 missing、字段级 missing、strict validator issue count、mapping decision issue count。必须在报告中明确。

### 3.2 Codex 任务

1. 查找现有报告生成脚本：

```powershell
rg "phase_g|semantic_mapping_quality|strict_validation_failure|report_consistency|non_procurement_mapping" scripts backend -n
```

2. 新增或修改统一指标聚合脚本：

```text
scripts/build_phase_h_report_consistency.py
```

3. 输出统一说明：

```text
reports/phase_h_report_consistency.json
reports/phase_h_report_consistency.md
```

4. 在 consistency report 中明确每个字段：

```json
{
  "metric_definitions": {
    "average_recall": "mean per-document mapping recall over evaluator dataset",
    "strict_pass_count": "number of documents whose strict validation passed",
    "required_missing_doc_count": "number of documents with at least one required missing",
    "required_missing_field_count": "total missing required field incidents",
    "review_required_doc_count": "number of documents with at least one review-required decision",
    "review_required_field_count": "total review-required mapping decisions",
    "badcase_violations": "forbidden mapping accepted count",
    "llm_auto_accepted_count": "LLM-only or LLM-suggested accepted without review count"
  }
}
```

5. 报告中不能只写 `missing`，必须写：

```text
required_missing_doc_count
required_missing_field_count
review_required_doc_count
review_required_field_count
```

### 3.3 验收标准

```powershell
backend\.venv\Scripts\python.exe scripts\build_phase_h_report_consistency.py `
  --reports-root reports `
  --out reports\phase_h_report_consistency.json `
  --markdown reports\phase_h_report_consistency.md
```

通过条件：

- `status = passed`
- 无 conflicting metric names
- 所有 Phase H 报告包含 metric definitions 或引用统一 definitions
- JSON 与 Markdown 数字一致

---

## 4. 工作流 B：Gap drilldown 机器可读化

### 4.1 目标

现在已经知道 gap 大头，但 Codex 需要精确到每个文档、字段、gap 类型、source anchor、推荐修复动作。新增 drilldown 报告，直接指导修复。

### 4.2 Codex 任务

新增脚本：

```text
scripts/analyze_phase_h_mapping_gaps.py
```

输入：

```text
reports/phase_g_non_procurement_mapping_eval_report.json
reports/phase_g_semantic_mapping_quality_report.json
reports/phase_g_strict_validation_failure_analysis.json
examples/real_world/gold/...
examples/real_world/uir/...
```

输出：

```text
reports/phase_h_mapping_gap_drilldown.json
reports/phase_h_mapping_gap_drilldown.md
```

JSON schema 建议：

```json
{
  "summary": {
    "dataset_size": 50,
    "gap_count": 0,
    "by_doc_type": {},
    "by_target_field": {},
    "by_gap_type": {},
    "top_ranked_fixes": []
  },
  "items": [
    {
      "doc_id": "real_policy_XXX",
      "doc_type": "policy_doc",
      "target_field": "publish_date",
      "gap_type": "candidate_not_extracted",
      "gold_value_shape": "date",
      "current_decision": null,
      "candidate_present": false,
      "source_anchor_present": false,
      "risk": "low|medium|high",
      "recommended_action": "enhance_candidate_extraction",
      "notes": "..."
    }
  ]
}
```

### 4.3 Gap 类型标准化

必须至少覆盖：

```text
candidate_not_extracted
candidate_extracted_but_not_ranked
candidate_ranked_but_review_required
candidate_ranked_but_badcase_blocked
value_normalization_failed
date_format_invalid
missing_required
schema_route_low_confidence
source_not_present
```

### 4.4 验收标准

- 能列出 top 30 gap。
- 能按 doc_type、target_field、gap_type 排序。
- Markdown 中给出每个 top gap 的修复建议。
- 不把 gold value 写入 mapping runtime 所用文件。

---

## 5. 工作流 C：候选抽取增强

候选抽取是 Phase H 的主战场。优先按 `candidate_not_extracted` 排名修。

### 5.1 Codex 先定位代码

执行：

```powershell
rg "candidate" backend/app -n
rg "extract" backend/app/services -n
rg "mapping" backend/app/services -n
rg "policy_doc|meeting_doc|general_doc" backend/app -n
```

找到实际负责以下逻辑的文件：

```text
candidate extraction
field candidate model
mapping template aliases
regex / type / fuzzy matching
normalization / date normalization
validation
```

不要盲目新建平行实现；应接入现有服务。

---

## 6. C1：policy_doc.publish_date 候选抽取

### 6.1 当前问题

`policy_doc.publish_date` 是最大缺口，Phase G semantic report 中 `publish_date` gap_count=16，其中 15 个是 `candidate_not_extracted`。

### 6.2 目标

把 `policy_doc.publish_date` 的 candidate_not_extracted 从 15 降到 ≤ 3，且 forbidden `发布日期 -> effective_date` 仍不得自动接受。

### 6.3 规则设计

新增或增强 `publish_date` 候选抽取规则。候选来源按优先级排序：

#### 高置信 source labels

```text
发布日期
发布日
发布时间
发文日期
成文日期
印发日期
公布日期
公开日期
颁布日期
制发日期
```

#### 正文模式

```regex
(?P<label>发布日期|发文日期|成文日期|印发日期|公布日期|公开日期|颁布日期|制发日期)[：: ]*(?P<date>\d{4}[年\-/\. ]\d{1,2}[月\-/\. ]\d{1,2}日?)
(?P<date>\d{4}年\d{1,2}月\d{1,2}日)印发
(?P<date>\d{4}年\d{1,2}月\d{1,2}日)发布
(?P<date>\d{4}年\d{1,2}月\d{1,2}日)公布
```

#### 元数据模式

支持从 UIR metadata / attributes / block labels 中读取：

```text
doc_meta.publish_date
metadata.publish_date
metadata.date_published
source_meta.publish_date
page_meta.publish_time
```

#### 排除标签

以下不能作为 `publish_date` 的高置信候选，只能进入 review 或映射到其他字段：

```text
生效日期
施行日期
执行日期
有效期至
截止日期
申报截止
申请截止
报名截止
retrieved_at
抓取时间
更新时间
页面更新时间
```

### 6.4 日期标准化

所有日期候选进入统一 normalizer：

```text
2026年7月7日 -> 2026-07-07
2026/7/7 -> 2026-07-07
2026.7.7 -> 2026-07-07
2026-7-7 -> 2026-07-07
```

只接受完整年月日。仅年月或仅年份：

```text
2026年7月 -> review_required: partial_date
2026年 -> review_required: partial_date
```

### 6.5 Evidence 字段

每个候选必须输出：

```json
{
  "source_label": "发布日期",
  "source_text": "发布日期：2026年7月7日",
  "normalized_value": "2026-07-07",
  "source_anchor": {...},
  "rule_id": "policy.publish_date.label_date.v1",
  "confidence": 0.92,
  "risk_flags": []
}
```

### 6.6 测试

新增或扩展测试：

```text
backend/tests/.../test_policy_publish_date_extraction.py
```

覆盖：

- `发布日期：2026年7月7日` -> publish_date accepted。
- `发文日期：2026-07-07` -> publish_date accepted。
- `2026年7月7日印发` -> publish_date accepted 或 high-confidence candidate。
- `自2026年8月1日起施行` -> 不得映射到 publish_date，应进入 effective_date。
- `有效期至2026年12月31日` -> 不得映射到 publish_date，应进入 valid_until。
- `retrieved_at: 2026-07-07` -> 不得映射到 publish_date accepted。
- `页面更新时间：2026-07-07` -> review_required 或 ignored。

---

## 7. C2：policy_doc.issuer 候选抽取

### 7.1 当前问题

strict validation 中 `issuer` required missing 高，policy_doc 失败 10 个，issuer missing 是主要原因之一。

### 7.2 目标

把 policy_doc `issuer` required missing 降到 ≤ 2，最好 0；同时继续禁止 `承办单位 -> issuer` 高风险自动映射。

### 7.3 高置信 issuer 来源

#### 标签型

```text
发文机关
发布机构
发布单位
制定机关
制定单位
印发机关
印发单位
颁布机关
颁布单位
主办单位（仅政策发布上下文）
```

#### 红头/标题区模式

很多政策文档顶部会出现：

```text
上海市人民政府办公厅
北京市发展和改革委员会
XX局 XX委员会 关于印发……的通知
```

规则：

- 在文档前 N 个 block 中查找机构名。
- 如果机构名后紧跟 `关于印发|关于发布|关于公布|通知|办法|意见|公告`，可作为 issuer 高置信候选。
- 多个机构并列时保留数组或用 `；` 拼接，同时保留原始 evidence。

#### 正文模式

```regex
由(?P<issuer>[^，。；]+?)(发布|印发|制定|颁布)
(?P<issuer>[^，。；]+?)(发布|印发|制定|颁布)了?《
经(?P<issuer>[^，。；]+?)同意.*印发
```

### 7.4 明确排除项

以下不能自动 accepted 为 `issuer`：

```text
承办单位
协办单位
联系人
联系电话
咨询电话
受理单位
办理机构
服务窗口
页面来源
网站名称
转载来源
```

这些可以进入 `risk_flags: ["issuer_ambiguous_source"]` 或 `review_required`。

### 7.5 Evidence

```json
{
  "target_field": "issuer",
  "source_label": "发文机关",
  "source_text": "发文机关：上海市人民政府办公厅",
  "rule_id": "policy.issuer.authority_label.v1",
  "confidence": 0.94,
  "risk_flags": []
}
```

### 7.6 测试

覆盖：

- `发文机关：上海市人民政府办公厅` -> accepted。
- 顶部机构 + `关于印发...的通知` -> accepted。
- `承办单位：XX中心` -> 不得 accepted 为 issuer。
- `页面来源：XX网站` -> 不得 accepted 为 issuer。
- 联合发文：`XX局 XX委 关于印发...` -> issuer 多值或合并值。

---

## 8. C3：policy_doc.effective_date / valid_until 日期角色分类

### 8.1 目标

减少 `effective_date`、`valid_until` 的 candidate_not_extracted 和 date role 混淆，同时继续阻断 `发布日期 -> effective_date`。

### 8.2 effective_date 模式

```regex
自(?P<date>\d{4}年\d{1,2}月\d{1,2}日)起(施行|实施|执行)
(?P<date>\d{4}年\d{1,2}月\d{1,2}日)(起)?(施行|实施|执行)
施行日期[：: ]*(?P<date>...)
生效日期[：: ]*(?P<date>...)
```

### 8.3 valid_until 模式

```regex
有效期至(?P<date>...)
截至(?P<date>...)
截止日期[：: ]*(?P<date>...)
本政策有效期.*?(?P<date>...)
```

### 8.4 Badcase 必须保留

- `发布日期` 不能自动映射为 `effective_date`。
- `retrieved_at` 不能自动映射为 `effective_date`。
- `有效期至` 不能映射为 `publish_date`。

---

## 9. C4：policy_doc.policy_measures / target_audience / application_conditions

### 9.1 当前问题

这些字段不是简单表头字段，常埋在段落、小标题、条款列表中。Phase G 中：

```text
policy_measures gap_count = 7
target_audience gap_count = 6
application_conditions gap_count = 11
```

### 9.2 候选抽取策略

#### policy_measures 高置信标题

```text
政策措施
支持措施
扶持措施
主要措施
具体措施
奖励措施
补贴标准
支持内容
保障措施
工作措施
```

抽取策略：

- 命中标题 block 后，抽取其子段落/列表直到下一个同级标题。
- 保留列表结构。
- 如果内容过长，生成摘要候选但 canonical 中应保留原文或结构化片段。

#### target_audience 高置信标题/模式

```text
适用对象
服务对象
支持对象
申报对象
扶持对象
受益对象
面向对象
适用范围
```

正文模式：

```regex
适用于(?P<value>[^。；]+)
面向(?P<value>[^。；]+)
支持(?P<value>[^。；]+?)(企业|机构|单位|个人)
```

#### application_conditions 高置信标题

```text
申请条件
申报条件
办理条件
准入条件
适用条件
认定条件
基本条件
```

注意与 `application_materials`、`process_steps` 分离。

### 9.3 输出要求

这些字段可以是文本段落，也可以是列表。必须保留 source anchors 和 `rule_id`。

---

## 10. C5：meeting_doc 候选抽取

### 10.1 优先字段

```text
meeting_number
topics
organizer
attendees
meeting_date
decisions
action_items
```

### 10.2 meeting_number

高置信 label：

```text
会议编号
会议纪要编号
纪要编号
会议届次
会议期次
第X次会议
```

模式：

```regex
第[一二三四五六七八九十百\d]+次会议
第[一二三四五六七八九十百\d]+期
会议纪要(?:\s*)\d{4}[-第]?\d+号
```

### 10.3 topics

标题：

```text
会议议题
议题
主要议题
审议事项
讨论事项
会议内容
```

抽取规则：

- 命中标题后抽取同级子列表。
- 如果标题中含“关于……的议题/事项”，也抽取。

### 10.4 organizer

高置信 label：

```text
主办单位
组织单位
召集单位
会议组织方
承办单位（会议场景可作为 organizer，不是 policy issuer）
```

注意：`承办单位` 在 policy_doc 不能自动 issuer，但在 meeting_doc 可以作为 organizer 候选。

### 10.5 attendees

高置信 label：

```text
参会人员
与会人员
出席人员
列席人员
参加人员
参会单位
```

禁止：

```text
主持人 -> attendees 自动 accepted
联系人 -> attendees 自动 accepted
```

主持人可进入 `chair` 或 review，但不能扩展为 attendees。

### 10.6 decisions/action_items

标题：

```text
会议决定
决议事项
形成决议
决定事项
工作安排
后续行动
任务分工
责任分工
待办事项
```

---

## 11. C6：general_doc 候选抽取与 ranking

### 11.1 优先字段

```text
application_conditions
contact
service_object
process_steps
application_materials
```

### 11.2 application_conditions

标题：

```text
申请条件
办理条件
受理条件
申报条件
准入条件
资格条件
```

ranking 需要避免误把材料、流程、依据当条件。

负面标题：

```text
申请材料
办理材料
所需材料
办理流程
办理步骤
法律依据
收费标准
办理地点
联系方式
```

### 11.3 contact

标签：

```text
联系人
联系电话
咨询电话
联系方式
服务热线
办公电话
电子邮箱
```

如果只提取到电话但没有联系人，也可以作为 contact 候选，但要标记 value shape。

### 11.4 service_object

标签：

```text
服务对象
受理对象
适用对象
办理对象
面向对象
申请主体
```

已有 knowledge 示例 `service_object: 受理` 可以保留，但要避免把泛化的“受理”在所有上下文中无限扩散。建议限制为标题/label 场景：

```text
受理对象
受理范围
受理条件（更可能是 application_conditions）
```

---

## 12. 工作流 D：Evidence ranking 增强

### 12.1 目标

解决 `candidate_extracted_but_not_ranked`，尤其是：

```text
general_doc.application_conditions
meeting_doc.attendees
policy_doc.effective_date
```

### 12.2 Ranking score 设计

建议对每个 candidate 计算：

```text
score = label_score
      + heading_score
      + proximity_score
      + value_shape_score
      + doc_type_context_score
      + source_anchor_score
      - negative_label_penalty
      - forbidden_pair_penalty
      - ambiguity_penalty
```

### 12.3 各项说明

| Score | 说明 |
|---|---|
| `label_score` | source label 与目标字段 alias 的强匹配 |
| `heading_score` | 标题/小标题命中目标字段语义 |
| `proximity_score` | label 与 value 距离近、同 block 或相邻 block |
| `value_shape_score` | 日期/机构名/电话/列表/金额等形状符合字段类型 |
| `doc_type_context_score` | 同一 label 在不同 doc_type 中含义不同，如 `承办单位` |
| `source_anchor_score` | 有稳定 source anchor 加分 |
| `negative_label_penalty` | 命中材料/流程/联系人等负面标题扣分 |
| `forbidden_pair_penalty` | forbidden pair 直接 blocked 或强扣分 |
| `ambiguity_penalty` | 同值可映射多个字段时降低 auto-accept |

### 12.4 自动 accepted 条件

必须同时满足：

```text
score >= high_confidence_threshold
no forbidden pair
source_anchor_present = true
not llm_only
not source_not_present
not medium_or_low_confidence_fuzzy
not conflicting_with_required_field_role
```

否则进入 review-required。

---

## 13. 工作流 E：Strict validation 修复

### 13.1 当前失败类别

```text
date_format_invalid = 12
missing_required = 18
semantic_review_required = 22
```

### 13.2 日期格式修复

新增统一 date normalizer 单元测试。所有映射到 date 类型字段的值必须在 transform 前规范化：

```text
YYYY-MM-DD
```

不确定日期：

```text
2026年7月 -> review_required: partial_date
2026年 -> review_required: partial_date
即日起 -> review_required: relative_date_without_anchor
长期 -> valid_until 可为空或 special token，但需 schema 支持；否则 review_required
```

### 13.3 Required missing 修复

优先修 required field：

```text
policy_doc.issuer
policy_doc.publish_date
meeting_doc.meeting_date
```

不允许通过删除 required 字段或降低 schema requirement 来提高 strict pass。

### 13.4 Semantic review 修复

对低风险、source-backed、强 label 的 review-required 做规则化提升；对以下仍必须 review：

```text
LLM-only suggestion
forbidden-pair-adjacent mapping
source-untraceable mapping
partial date
ambiguous organization role
contact/chair/person list ambiguity
```

---

## 14. 工作流 F：Simulated Human Review + DeepSeek 审查闭环

用户允许使用“子智能体模拟人工审查项目情况，review 并通过 DeepSeek 的输出”。必须安全实现：DeepSeek 可以提出候选，子智能体/规则可以模拟人工审查并批准 evidence-backed 候选，但系统指标里仍应记录为 `simulated_human_approved` 或 `review_approved`，不能记录为 `llm_auto_accepted`。

### 14.1 总原则

```text
DeepSeek proposes.
Deterministic filters screen.
Review subagents judge.
Safety reviewer vetoes.
Only approved candidates enter draft knowledge pack.
Impact preview and regression gates must pass.
Activation affects future tasks only.
```

### 14.2 新增脚本

建议新增：

```text
scripts/run_phase_h_review_subagents.py
scripts/apply_phase_h_review_approvals_safe.py
scripts/eval_phase_h_deepseek_review_loop.py
```

### 14.3 Review 子智能体角色

#### 1. Evidence Reviewer

职责：只看 UIR source blocks、mapping report、candidate evidence，判断候选是否有源依据。

Approve 条件：

- source text 明确包含候选值。
- source anchor 存在。
- source label 与目标字段语义一致。
- 非 LLM-only。

Reject 条件：

- 没有 source anchor。
- 仅凭模型猜测。
- value 在 UIR 中找不到。

#### 2. Domain Reviewer

职责：按 doc_type 判断字段语义。

重点：

- policy_doc：issuer/publish_date/effective_date/valid_until 角色区分。
- meeting_doc：主持人、联系人、参会人、组织方边界。
- general_doc：申请条件、材料、流程、服务对象边界。

#### 3. Safety Reviewer

职责：一票否决高风险候选。

Veto 条件：

- 命中 forbidden pair。
- medium/low-confidence fuzzy。
- LLM-only。
- source-untraceable。
- secret-like content。
- 会修改历史 snapshot。

#### 4. Consistency Reviewer

职责：检查候选是否与 schema 类型、已有 mapping、required field、badcase registry 一致。

### 14.4 Review 输入格式

```json
{
  "task_id": "...",
  "doc_id": "...",
  "doc_type": "policy_doc",
  "target_field": "publish_date",
  "candidate": {
    "value": "2026-07-07",
    "source_text": "发布日期：2026年7月7日",
    "source_label": "发布日期",
    "source_anchor": {...},
    "rule_id": "policy.publish_date.label_date.v1",
    "confidence": 0.92,
    "origin": "deterministic|deepseek|review_knowledge"
  },
  "risk_flags": [],
  "badcase_filter": {
    "blocked": false,
    "reason": null
  }
}
```

### 14.5 Review 输出格式

```json
{
  "decision": "approve|reject|needs_human",
  "approved_by": ["evidence_reviewer", "domain_reviewer", "safety_reviewer", "consistency_reviewer"],
  "confidence": "high|medium|low",
  "reason": "source label 发布日期 explicitly supports publish_date",
  "must_not_count_as_llm_auto_accept": true,
  "candidate_origin": "deepseek",
  "final_status": "simulated_human_approved"
}
```

### 14.6 DeepSeek 接入方式

DeepSeek 只允许生成候选，不允许直接写入 accepted mapping。建议 prompt 输出严格 JSON：

```text
You are proposing mapping candidates only. Do not decide final acceptance.
Given UIR blocks and schema fields, return candidate target fields with source evidence.
Each candidate must include source_text copied from UIR, source_anchor if available, and uncertainty.
Return [] if evidence is insufficient.
```

DeepSeek 输出必须经过：

```text
JSON schema validation
source text existence check
source anchor check
forbidden pair check
secret redaction check
review subagent approval
impact preview
regression gates
```

### 14.7 DeepSeek 候选安全落库字段

```json
{
  "origin": "deepseek",
  "status": "review_required",
  "llm_auto_accepted": false,
  "simulated_human_review_status": "pending|approved|rejected",
  "evidence_linked": true,
  "source_anchor_present": true
}
```

### 14.8 不得出现的状态

```json
{
  "origin": "deepseek",
  "status": "accepted",
  "llm_auto_accepted": true
}
```

这应被 secret/safety audit 或 regression gate 直接 fail。

### 14.9 DeepSeek / Review loop 评测报告

输出：

```text
reports/phase_h_deepseek_review_loop_report.json
reports/phase_h_deepseek_review_loop_report.md
```

指标：

```json
{
  "deepseek_configured": true,
  "deepseek_requests": 0,
  "deepseek_candidates": 0,
  "evidence_linked_candidates": 0,
  "subagent_reviewed": 0,
  "subagent_approved": 0,
  "subagent_rejected": 0,
  "needs_human": 0,
  "applied_to_draft_pack": 0,
  "activated_after_gates": 0,
  "badcase_violations": 0,
  "llm_auto_accepted_count": 0,
  "secret_leaks": 0,
  "snapshot_mutations": 0,
  "measurable_recall_delta": 0.0,
  "strict_pass_delta": 0
}
```

---

## 15. 工作流 G：Review → Knowledge Pack 安全激活

### 15.1 目标

把 Review 子智能体批准的安全 alias/pattern 沉淀到 draft knowledge pack，经 impact preview、badcase check、snapshot invariant 后再激活。

### 15.2 执行步骤

1. 从 approved review decisions 生成 knowledge candidates。
2. 每个 candidate 必须带：

```text
doc_type
template_id
target_field
source_label or pattern
source evidence example
risk flags
approval trail
```

3. 创建 draft pack。
4. 跑 impact preview。
5. 跑 badcase activation check。
6. 跑 old snapshot invariant。
7. 如果 gates 全过，才 activate。
8. activate 后只影响 future tasks。

### 15.3 不允许激活的候选

```text
forbidden pair
LLM-only
source-untraceable
medium/low confidence fuzzy
single-document overfit without label/pattern generality
conflicts with rejected controls
would change old snapshot
```

### 15.4 新增报告

```text
reports/phase_h_review_knowledge_growth_report.json
reports/phase_h_review_knowledge_growth_report.md
```

必须包含：

```text
old snapshot unchanged = true
badcase violations = 0
rejected candidates activated = 0
llm auto accepted = 0
secret leaks = 0
before/after recall
before/after strict pass
before/after review-required
activated aliases/patterns
rejected controls
```

---

## 16. 工作流 H：UIR Quality Gate 改善

### 16.1 当前情况

当前 UIR Quality Gate 是 60 total、12 pass、48 review、0 reject、0 unsupported。它不是导入失败，而是自动接受边界很保守。

### 16.2 原则

不能通过降低 gate threshold 提高通过率。只能通过真实质量提升让更多 UIR 满足自动接受条件。

### 16.3 改善项

1. 对每个 review UIR 输出 review reason：

```text
schema_route_low_confidence
required_field_missing
mapping_review_required
date_format_invalid
unsupported_structure
quality_score_low
```

2. 新增 quality gate drilldown：

```text
reports/phase_h_uir_quality_gate_drilldown.json
reports/phase_h_uir_quality_gate_drilldown.md
```

3. 对已经通过 strict mapping 的样本，允许 quality gate 自动 pass，但必须满足：

```text
badcase violations = 0
required missing = 0
critical review-required = 0
schema route confidence >= threshold
package verification passed
lineage warnings not critical
```

4. 保留 `allow-auto-accept` 与 `pass` 的区别。

---

## 17. 工作流 I：Production blind/shadow corpus scaffold

### 17.1 目标

补齐 0.85 声明前置条件，但不要伪造数据。

### 17.2 新增目录

```text
examples/production_shadow/
  manifest.json
  uir/
    .gitkeep
  gold/
    mapping_gold.jsonl
    badcases.jsonl
  README.md
```

### 17.3 manifest schema

```json
{
  "dataset_id": "production_shadow_v1",
  "split": "blind",
  "frozen_at": null,
  "docs": [],
  "dedupe_against": ["examples/real_world"],
  "gold_policy": {
    "requires_two_pass_labeling": true,
    "allows_runtime_use": false,
    "used_only_for_evaluation": true
  }
}
```

### 17.4 Blocker 行为

如果 docs 或 gold 为空，报告必须继续：

```text
status = blocked
can_claim_0_85 = false
```

---

## 18. Phase H 验证命令

### 18.1 仓库级验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

### 18.2 重新跑核心评测

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py `
  --base-url http://127.0.0.1:8000 --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py `
  --base-url http://127.0.0.1:8000 --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_h_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_h_non_procurement_mapping_eval_report.md
```

### 18.3 跑新增报告

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_phase_h_mapping_gaps.py `
  --reports-root reports `
  --out reports\phase_h_mapping_gap_drilldown.json `
  --markdown reports\phase_h_mapping_gap_drilldown.md

backend\.venv\Scripts\python.exe scripts\run_phase_h_review_subagents.py `
  --base-url http://127.0.0.1:8000 `
  --out reports\phase_h_review_subagent_report.json `
  --markdown reports\phase_h_review_subagent_report.md

backend\.venv\Scripts\python.exe scripts\eval_phase_h_deepseek_review_loop.py `
  --out reports\phase_h_deepseek_review_loop_report.json `
  --markdown reports\phase_h_deepseek_review_loop_report.md

backend\.venv\Scripts\python.exe scripts\build_phase_h_report_consistency.py `
  --reports-root reports `
  --out reports\phase_h_report_consistency.json `
  --markdown reports\phase_h_report_consistency.md
```

### 18.4 安全审计

```powershell
backend\.venv\Scripts\python.exe scripts\eval_uir_quality_gate.py `
  --out reports\phase_h_uir_quality_gate_eval_report.json `
  --markdown reports\phase_h_uir_quality_gate_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_deepseek_smoke.py `
  --out reports\phase_h_deepseek_smoke_report.json `
  --markdown reports\phase_h_deepseek_smoke_report.md

backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

---

## 19. Codex 分批执行建议

### Batch 1：只做分析与报告口径，不改 mapping 行为

交付：

```text
scripts/analyze_phase_h_mapping_gaps.py
scripts/build_phase_h_report_consistency.py
reports/phase_h_mapping_gap_drilldown.*
reports/phase_h_report_consistency.*
```

验证：

```powershell
backend\.venv\Scripts\python.exe scripts\build_phase_h_report_consistency.py ...
```

### Batch 2：policy_doc 日期与 issuer

交付：

```text
policy.publish_date extraction
policy.issuer extraction
policy.effective_date / valid_until role classifier
date normalizer tests
badcase tests
```

验收：

```text
publish_date candidate_not_extracted 明显下降
issuer required_missing 明显下降
date_format_invalid 明显下降
badcase violations = 0
```

### Batch 3：policy_doc 长尾字段

交付：

```text
policy_measures
target_audience
application_conditions
application_materials
process_steps
```

验收：

```text
policy_doc recall >= 0.78，stretch >= 0.82
```

### Batch 4：meeting_doc 字段

交付：

```text
meeting_number
topics
organizer
attendees
meeting_date
decisions
action_items
```

验收：

```text
meeting_doc recall >= 0.82
strict pass 保持 15/15 或不下降
```

### Batch 5：general_doc ranking

交付：

```text
application_conditions ranking
contact extraction
service_object constrained alias
process_steps/application_materials disambiguation
```

验收：

```text
general_doc recall >= 0.86
review-required 下降
```

### Batch 6：DeepSeek + Review subagents 安全闭环

交付：

```text
run_phase_h_review_subagents.py
eval_phase_h_deepseek_review_loop.py
apply_phase_h_review_approvals_safe.py
phase_h_deepseek_review_loop_report.*
phase_h_review_knowledge_growth_report.*
```

验收：

```text
llm_auto_accepted_count = 0
subagent_approved > 0 或明确 no-op reason
badcase violations = 0
secret leaks = 0
old snapshot unchanged = true
```

### Batch 7：总体验收

交付：

```text
phase_h_non_procurement_mapping_eval_report.*
phase_h_semantic_mapping_quality_report.*
phase_h_strict_validation_failure_analysis.*
phase_h_report_consistency.*
phase_h_acceptance_report.md
```

验收：

```text
average_recall >= 0.85 或明确剩余差距
strict_pass >= 43/50
required_missing <= 1
review_required <= 12
badcase violations = 0
llm_auto_accepted_count = 0
secret leaks = 0
package verification = 50/50
```

---

## 20. 最终验收报告模板

Codex 最后生成：

```text
reports/phase_h_acceptance_report.md
```

模板：

```markdown
# Phase H Acceptance Report

## Baseline

| Metric | Phase G | Phase H | Delta |
|---|---:|---:|---:|
| non_procurement_average_recall | 0.7426031746 | TBD | TBD |
| semantic_quality_average_recall | 0.7184920635 | TBD | TBD |
| strict_pass | 39/50 | TBD | TBD |
| required_missing_doc_count | TBD | TBD | TBD |
| required_missing_field_count | TBD | TBD | TBD |
| review_required_doc_count | TBD | TBD | TBD |
| review_required_field_count | TBD | TBD | TBD |
| badcase_violations | 0 | 0 | 0 |
| llm_auto_accepted_count | 0 | 0 | 0 |
| secret_leaks | 0 | 0 | 0 |
| package_verification | 50/50 | 50/50 | 0 |

## What changed

- Candidate extraction rules added:
- Evidence ranking changes:
- Date normalization changes:
- Review/Knowledge changes:
- DeepSeek review loop changes:

## Safety checks

- Badcase filters:
- LLM auto acceptance:
- Secret redaction:
- Snapshot invariants:
- Report consistency:

## Remaining gaps

- Field-level remaining gaps:
- Doc-level remaining gaps:
- Blind/shadow status:

## Claim boundary

This report may claim local Phase H evaluator results only.
It must not claim production blind 0.85 unless production_shadow blind corpus and gold labels exist and pass.
```

---

## 21. Definition of Done

Phase H 执行完成必须满足：

1. 仓库级验证通过。
2. Frontend tests 通过。
3. 新增/修改的 evaluator 报告可复现。
4. 50-sample non-procurement package verification 仍为 50/50。
5. badcase violations 仍为 0。
6. LLM auto accepted 仍为 0。
7. secret leaks 仍为 0。
8. strict validation 与 semantic mapping 指标不回退。
9. 如果未达到 0.85，报告必须列出剩余 top gaps，不能强行宣称达标。
10. 如果达到本地 0.85，报告必须明确：这是 local evaluator，不是 production blind claim。
