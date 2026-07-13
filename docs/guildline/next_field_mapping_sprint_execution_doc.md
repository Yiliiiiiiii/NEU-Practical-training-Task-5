# SchemaPack Agent 字段映射 0.85 冲刺执行文档（加速版）

> 适用仓库：`Yiliiiiiiii/NEU-Practical-training-Task-5`  
> 目标：在截止日期临近的情况下，优先提升课题 5 字段映射指标，同时保留防过拟合、badcase safety、可复现证据链。  
> 执行对象：Codex / 项目开发者  
> 执行原则：**快，但不能靠 doc_id 特例、gold 泄漏、review 膨胀或牺牲 badcase 来刷指标。**

---

## 0. 当前状态判断

当前仓库已经完成了 0.85 guarded sprint 的第一轮“评测治理框架建设”，但字段映射能力本身尚未达标。

### 0.1 已完成的正确方向

当前已经具备：

1. `auto_mapping_recall`、`assisted_mapping_recall`、`review_required_rate` 等指标拆分。
2. dev / test / blind 文档级划分。
3. split evaluator。
4. gap analysis。
5. overfit risk scan。
6. quality gate。
7. badcase safety 继续保持 0 violation。
8. package verification 继续保持 100%。

这说明项目已经从“单一 recall 数字”转向“可解释、可审计、可防过拟合”的验收体系。

### 0.2 当前尚未达标的事实

当前 sprint 文档记录的 baseline：

| Metric | Value |
| --- | ---: |
| dataset_size | 35 |
| legacy average / assisted recall | 0.6096598639455783 |
| auto_mapping_recall | 0.6095617529880478 |
| assisted_mapping_recall | 0.6095617529880478 |
| review_required_rate | 0.22264150943396227 |
| review_required_count | 59 |
| required_missing_count | 4 |
| badcase_violations | 0 |
| package_verification_pass | 35 |

split 结果：

| Split | Docs | Auto Recall | Assisted Recall | Review Rate | Required Missing | Badcase Violations | Package Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 18 | 0.579 | 0.579 | 0.223 | 2 | 0 | 1.000 |
| test | 9 | 0.676 | 0.676 | 0.291 | 0 | 0 | 1.000 |
| blind | 8 | 0.594 | 0.594 | 0.125 | 2 | 0 | 1.000 |

最终 0.85 质量门禁当前未通过，原因包括：

1. dev assisted recall 低于 0.85。
2. test assisted recall 低于 0.85。
3. blind assisted recall 低于 0.85。
4. dev / blind 仍有 required missing。
5. test / blind generalization gap 超过 0.05。

因此，当前对外表述必须是：

> 已建立 0.85 冲刺的防过拟合评测框架，但字段映射指标尚未达到 0.85。下一步重点进入 source-backed candidate extraction 和高收益字段规则增强。

---

## 1. 本轮冲刺总目标

### 1.1 最终绿色目标

本轮最终目标是让以下门禁全部通过：

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report docs\交接\evidence\mapping_splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05
```

绿色达标条件：

| Gate | Required |
| --- | ---: |
| dev assisted recall | >= 0.85 |
| test assisted recall | >= 0.85 |
| blind assisted recall | >= 0.85 |
| badcase violations | 0 |
| required missing | 0 |
| package pass rate | 100% |
| dev/test assisted recall gap | <= 0.05 |
| test/blind assisted recall gap | <= 0.05 |
| overfit scan | Pass |
| verify_all | Pass |

### 1.2 加速但保底目标

考虑截止日期临近，如果无法在所有 split 都达到 0.85，不允许伪造或模糊表达。保底目标为：

1. `required_missing_count` 必须降到 0。
2. `badcase_violations` 必须保持 0。
3. `package_pass_rate` 必须保持 100%。
4. `overfit risk scan` 必须通过。
5. 文档中必须如实说明当前 recall 值和未达标原因。
6. 至少显著提升 dev/test/blind 的 assisted recall，并提供 gap analysis 证明下一步路径。

最终答辩表述可分为两种：

**若 0.85 gate 通过：**

> 字段映射在 dev/test/blind 三个文档级 split 上均达到 assisted recall 0.85 以上，badcase violations 为 0，required missing 为 0，package verification 100%，且未发现 doc_id 特例或 gold 泄漏。

**若 0.85 gate 未通过但明显提升：**

> 已完成防过拟合评测体系和高优先级字段增强，required missing 已降至 0，badcase violations 维持 0，package verification 100%。当前 assisted recall 已从基线提升到 X，尚未完全达到 0.85，剩余问题集中在 Y/Z 字段，已给出可复现 gap report。

---

## 2. 严格禁止事项

为了避免过拟合和验收风险，以下做法一律禁止：

1. 禁止根据 `doc_id` 写特例规则。
   - 禁止：`if doc_id == "real_policy_005_ai_industry_guide"`
   - 禁止：`if doc_id.startswith("real_policy_") and "005" in doc_id`
2. 禁止 runtime mapping 读取 gold label 文件。
   - 禁止读取：`mapping_gold.jsonl`
   - 禁止读取：`expected_mappings`
   - 禁止读取：`known_badcases` 作为正向映射依据
3. 禁止为了提高 recall 大幅增加 review-required。
4. 禁止把 `retrieved_at`、来源网站、联系人、责任编辑等弱信息自动映射为关键字段。
5. 禁止为了通过质量门禁降低阈值。
6. 禁止只改文档不改能力，却宣称指标提升。
7. 禁止 LLM suggestion 自动 accepted。
8. 禁止牺牲 badcase safety 换 recall。

所有能力增强必须是**字段通用规则**或**source-backed extraction**，而不是样例特化。

---

## 3. 分支与提交策略

### 3.1 建议分支

```bash
git checkout main
git pull
git checkout -b sprint/mapping-085-source-backed
```

### 3.2 建议提交粒度

不要把所有内容放进一个巨大 commit。建议分为 5 个 commit：

1. `docs: fix mapping sprint evidence links and metric wording`
2. `eval: persist mapping sprint evidence snapshots`
3. `mapping: add source-backed policy issuer and publish date candidates`
4. `mapping: improve meeting topics and general deadline extraction`
5. `test: add mapping regression, badcase, and overfit gate coverage`

每个 commit 后至少运行相关单测。最终合并前运行完整验证。

---

## 4. 第一阶段：证据链与文档一致性修复（0.5 天内完成）

这一阶段不直接提升 recall，但必须先做。原因是当前 README 引用了部分 `reports/*` 文件，而 `.gitignore` 默认忽略 `reports/*`，导致某些报告链接可能无法在 GitHub 中打开。

### 4.1 修复证据文件提交路径

推荐不要大量放开 `reports/*`，而是把可提交证据统一复制到：

```text
docs/交接/evidence/
```

建议目录结构：

```text
docs/交接/evidence/
  mapping_metric_baseline_snapshot.md
  mapping_metric_baseline_snapshot.json        # 可选
  mapping_splits/
    summary.md
    summary.json
    dev_mapping_eval_report.md
    test_mapping_eval_report.md
    blind_mapping_eval_report.md
  mapping_gap_analysis.md
  mapping_gap_analysis.json
  mapping_overfit_risk_report.md
  mapping_quality_gate_result.md
  final_validation_commands.md
```

如果脚本支持 `--out` / `--out-dir`，直接输出到该目录；否则先生成到 `reports/`，再复制到 `docs/交接/evidence/`。

### 4.2 需要更新的文档

更新以下文档中的指标口径和链接：

1. `README.md`
2. `docs/交接/requirement_mapping.md`
3. `docs/交接/mapping_recall_085_guarded_sprint.md`
4. `docs/交接/project_status.md`
5. `docs/交接/acceptance_report.md`（如果存在对应最新状态）

统一表述：

```text
历史 average_recall / mapping_recall 是 assisted recall 兼容口径。
当前 0.85 sprint 以 auto_mapping_recall、assisted_mapping_recall、review_required_rate、dev/test/blind summary 为准。
```

### 4.3 统一测试数量口径

当前文档中可能同时出现 `662 tests`、`713 passed`、`718 passed`。本轮结束后只保留最后一次完整验证结果。

更新格式：

```text
最近一次完整验证：YYYY-MM-DD HH:mm
- backend pytest：N passed
- backend ruff：passed
- frontend build：passed
- frontend tests：N passed / N files
- OpenAPI export：63 paths
```

如果本轮没有重新跑前端测试，不要写“passed”；应写“本轮未重跑”。

### 4.4 本阶段验收

完成后执行：

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-md docs\交接\evidence\mapping_overfit_risk_report.md
```

并确认 README 中所有新链接在 GitHub 页面可打开。

---

## 5. 第二阶段：required missing 清零（最高优先级，1 天内完成）

当前 required missing 主要集中在 `policy_doc.issuer` 和 `policy_doc.publish_date`。这是必须先修的硬门禁，因为 required missing > 0 会直接导致 quality gate 失败。

### 5.1 优先字段

| Priority | Doc Type | Field | 当前问题 |
| ---: | --- | --- | --- |
| P0 | policy_doc | issuer | required missing |
| P0 | policy_doc | publish_date | required missing |

### 5.2 实现方向：source-backed candidate extraction

不要只继续堆 alias。下一步必须从 UIR 的结构化内容中提取强证据候选。

候选应包含：

```json
{
  "source_name": "发布单位",
  "source_path": "$.blocks.xxx.rows.1",
  "value_sample": "工业和信息化部",
  "target_field_id": "issuer",
  "method": "source_backed_label",
  "confidence": 0.92,
  "evidence_text": ["label 发布单位 matched issuer candidate"],
  "risk_flags": [],
  "need_review": false
}
```

弱证据候选应进入 review：

```json
{
  "source_name": "来源",
  "target_field_id": "issuer",
  "confidence": 0.60,
  "risk_flags": ["weak_source_site"],
  "need_review": true
}
```

高风险候选应直接 blocked，不进入自动 accepted。

---

### 5.3 `policy_doc.issuer` 规则设计

#### 5.3.1 强证据 label

以下 label 命中时，可以生成 issuer 候选：

```text
发布单位
发文机关
制定机关
印发机关
颁布机关
主管部门
牵头部门
发布机构
制定单位
印发单位
主办单位
联合发布单位
```

如果 value 中包含机构后缀，置信度可以较高：

```text
部
委
局
厅
办
署
司
中心
委员会
人民政府
办公厅
管理局
监督管理局
发展改革委
教育部
工业和信息化部
财政部
海关总署
民航局
```

推荐置信度：

| Evidence | Confidence | Action |
| --- | ---: | --- |
| 显式 label + 机构后缀 | 0.92 | auto accepted |
| 标题下方署名机构 + 附近有日期 | 0.86 | auto accepted 或 high confidence review，视现有阈值 |
| 文末署名机构 + 下一行日期 | 0.84 | review 或 accepted，优先 review 防误伤 |
| 来源网站 / 信息来源 | 0.55 | review only |
| 联系人 / 咨询电话 | blocked | no mapping |

#### 5.3.2 署名段抽取

政策文档常见结构：

```text
……通知
工业和信息化部
2026年1月10日
```

抽取逻辑：

1. 在文档前 20% 和后 20% 的 block 中查找“机构行 + 日期行”。
2. 机构行长度不宜过长，通常 4~40 字。
3. 机构行不能包含 `联系人`、`电话`、`邮箱`、`网址`、`来源`、`编辑`。
4. 日期行必须紧邻机构行上下 2 行范围。
5. 如果同一位置同时能抽到 `issuer` 和 `publish_date`，二者互相增强 evidence。

#### 5.3.3 负样本规则

以下字段不得自动映射为 issuer：

```text
来源
文章来源
信息来源
转载来源
网站来源
发布日期页面来源
联系人
咨询人
联系电话
咨询电话
责任编辑
编辑
审核
校对
承办人
```

处理方式：

1. 来源网站可以作为 `source`。
2. 联系人可以作为 `contact`。
3. 不允许自动作为 `issuer`。
4. 如果 fuzzy 误匹配到 `issuer`，必须 review 或 blocked。

---

### 5.4 `policy_doc.publish_date` 规则设计

#### 5.4.1 强证据 label

以下 label 可以作为 publish_date 候选：

```text
发布日期
公布日期
发布时间
发布于
印发日期
发文日期
公开日期
```

注意：`成文日期` 不建议直接自动作为 publish_date。可以映射到 `created_date`，或者作为 review 候选。

#### 5.4.2 日期格式识别

支持以下格式：

```text
2026年1月10日
2026 年 01 月 10 日
2026-01-10
2026/01/10
2026.01.10
二〇二六年一月十日
```

日期规范化应输出 ISO 格式或项目当前 canonical date 格式，保持与现有 transform 一致。

#### 5.4.3 署名日期抽取

如果文末出现：

```text
工业和信息化部
2026年1月10日
```

则日期可以作为 `publish_date` 的候选，但需要满足：

1. 上一行是强 issuer 候选。
2. 该日期不在“实施日期/施行日期/有效期”上下文中。
3. 不是 `retrieved_at`。
4. 不是网页抓取时间。

推荐置信度：

| Evidence | Confidence | Action |
| --- | ---: | --- |
| 显式 发布日期 / 公布日期 / 发布时间 | 0.93 | auto accepted |
| 印发日期 / 发文日期 | 0.88 | auto accepted 或 review |
| 文末署名日期 + issuer 伴随 | 0.84 | review 优先 |
| 成文日期 | 0.72 | review 或 map created_date，不自动 publish_date |
| retrieved_at | blocked | no mapping |
| 施行日期 / 实施日期 | blocked for publish_date | should map effective_date |

#### 5.4.4 publish_date 与 effective_date 的互斥保护

必须继续保持以下 badcase safety：

| Source | Forbidden Target |
| --- | --- |
| retrieved_at | publish_date / effective_date |
| 发布日期 | effective_date |
| 施行日期 | publish_date |
| 实施日期 | publish_date |
| 有效期至 | publish_date |
| 来源网站 | issuer |
| 联系人 | issuer |

---

### 5.5 需要新增或更新的测试

建议新增 / 修改：

```text
backend/tests/test_policy_doc_mapping_rules.py
backend/tests/test_candidate_mapping_services.py
backend/tests/test_mapping_service_evidence_ranking.py
```

测试用例必须覆盖：

1. 显式 `发布单位 -> issuer`。
2. 显式 `发文机关 -> issuer`。
3. 文末 `机构 + 日期` 抽取 issuer / publish_date 候选。
4. `来源网站` 不自动映射 issuer。
5. `联系人` 不自动映射 issuer。
6. `retrieved_at` 不自动映射 publish_date / effective_date。
7. `施行日期` 不自动映射 publish_date。
8. `成文日期` 不自动映射 publish_date，除非进入 review。

测试名称示例：

```python
def test_policy_issuer_from_explicit_issuing_authority_label(): ...

def test_policy_publish_date_from_explicit_publish_label(): ...

def test_policy_signature_block_candidates_are_source_backed(): ...

def test_source_site_is_not_auto_accepted_as_issuer(): ...

def test_effective_date_label_is_blocked_for_publish_date(): ...
```

---

## 6. 第三阶段：高收益字段 recall 提升（1～1.5 天内完成）

required missing 清零后，进入 recall 提升。不要平均优化所有字段，按 gap analysis 优先级处理。

当前排名前十：

1. `meeting_doc.topics`
2. `policy_doc.issuer`
3. `policy_doc.publish_date`
4. `general_doc.deadline`
5. `policy_doc.target_audience`
6. `general_doc.application_conditions`
7. `general_doc.service_object`
8. `policy_doc.policy_measures`
9. `meeting_doc.action_items`
10. `meeting_doc.decisions`

其中 `policy_doc.issuer` 和 `policy_doc.publish_date` 已在第二阶段处理。本阶段重点处理：

1. `meeting_doc.topics`
2. `general_doc.deadline`
3. `policy_doc.target_audience`
4. `policy_doc.policy_measures`
5. `meeting_doc.action_items`
6. `meeting_doc.decisions`

---

### 6.1 `meeting_doc.topics`

#### 6.1.1 常见证据模式

会议纪要中的议题通常来自：

```text
会议听取了……汇报
会议研究了……事项
会议审议了……方案
会议传达学习了……精神
会议原则同意……
会议决定……
会议强调……
会议要求……
一、关于……
二、研究……
三、审议……
```

#### 6.1.2 抽取策略

从 meeting document 的正文块中抽取 topic 候选：

1. 标题块：如果标题含“会议纪要 / 常务会议 / 专题会议”，标题可以辅助 meeting_title，不直接当 topics。
2. 小标题块：`一、`、`二、`、`（一）`、`1.` 开头的短标题，优先作为 topic。
3. 动词句：包含 `研究`、`审议`、`听取`、`传达学习`、`部署`、`原则同意` 的句子，抽取宾语短语作为 topic。
4. 不要把参会人员、主持人、地点、时间映射成 topics。

#### 6.1.3 置信度建议

| Evidence | Confidence | Action |
| --- | ---: | --- |
| 明确“议题/研究事项/审议事项”列表 | 0.90 | auto accepted |
| 小标题结构 | 0.86 | auto accepted |
| 动词句抽取 | 0.78 | review 或 accepted，取决于现有阈值 |
| 长段落摘要式 topic | 0.65 | review |

#### 6.1.4 测试

新增测试：

```python
def test_meeting_topics_from_numbered_agenda_headings(): ...

def test_meeting_topics_from_research_and_review_sentences(): ...

def test_meeting_attendees_are_not_topics(): ...
```

---

### 6.2 `general_doc.deadline` / `deadlines`

#### 6.2.1 常见 label

```text
申报截止时间
报名截止时间
提交截止时间
受理截止时间
截止日期
办理期限
受理时间
申报时间
申请时间
材料提交时间
```

#### 6.2.2 抽取策略

1. 显式 label + 日期 / 时间范围，生成 deadline 候选。
2. 句式中出现 `于 X 前提交`、`截至 X`、`X 前完成申报`，生成 deadline 候选。
3. `办理期限：X 个工作日` 可以作为 `deadline` 或 `deadlines`，视 schema 当前字段定义。
4. `发布日期`、`created_date` 不得作为 deadline。

#### 6.2.3 置信度建议

| Evidence | Confidence | Action |
| --- | ---: | --- |
| 显式 截止时间 / 截止日期 | 0.92 | auto accepted |
| 受理时间范围 | 0.86 | auto accepted 或 review |
| 办理期限 | 0.82 | review 或 accepted |
| 普通日期无 deadline 上下文 | blocked | no mapping |

#### 6.2.4 测试

```python
def test_general_deadline_from_explicit_deadline_label(): ...

def test_general_deadline_from_before_date_sentence(): ...

def test_publish_date_is_not_deadline(): ...
```

---

### 6.3 `policy_doc.target_audience`

#### 6.3.1 常见 label / 句式

```text
适用对象
支持对象
服务对象
面向对象
目标群体
适用范围
申报主体
企业范围
```

句式：

```text
适用于……
面向……
支持……企业
鼓励……单位
对……给予支持
```

#### 6.3.2 抽取策略

1. label block 优先。
2. 若无 label，从摘要 / 第一部分 / 总则中找 `适用于`、`面向`、`支持` 句式。
3. 候选值不宜超过 120 字，过长则进入 review。
4. 不要把 `issuer`、`contact`、`source` 当作 target_audience。

---

### 6.4 `policy_doc.policy_measures`

#### 6.4.1 常见标题

```text
政策措施
支持措施
主要措施
重点任务
保障措施
工作要求
扶持政策
补贴标准
奖励措施
```

#### 6.4.2 抽取策略

1. 标题命中上述模式时，将其下属段落聚合为 policy_measures。
2. 如果段落以 `（一）`、`1.`、`一是`、`二是` 开头，保留列表结构。
3. 如果段落过长，允许生成 summary 型候选，但必须带 source blocks。
4. 不要把全文 content 直接塞入 policy_measures。

---

### 6.5 `meeting_doc.decisions` 与 `meeting_doc.action_items`

#### 6.5.1 decisions

常见触发词：

```text
会议决定
会议原则同意
会议审议通过
会议明确
会议指出
会议要求
```

#### 6.5.2 action_items

常见触发词：

```text
由……负责
请……牵头
责成……
各部门要……
下一步……
按时完成……
加快推进……
```

#### 6.5.3 区分规则

| 内容 | Target |
| --- | --- |
| 通过、同意、决定、明确 | decisions |
| 由谁负责、何时完成、下一步行动 | action_items |
| 会议背景、出席人员、主持人 | 不映射 decisions/action_items |

---

## 7. 第四阶段：评测、门禁与防过拟合验证（每轮修改后必须执行）

每完成一个字段组修改，必须运行以下命令。

### 7.1 快速局部测试

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_policy_doc_mapping_rules.py -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_candidate_mapping_services.py -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_mapping_service_evidence_ranking.py -q
```

如果新增了 meeting/general 相关测试，也运行对应测试文件。

### 7.2 重新生成 mapping 评测

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md
```

### 7.3 生成 split summary

```powershell
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir docs\交接\evidence\mapping_splits
```

### 7.4 生成 gap analysis

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-json docs\交接\evidence\mapping_gap_analysis.json `
  --out-md docs\交接\evidence\mapping_gap_analysis.md
```

### 7.5 运行 overfit risk scan

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-json docs\交接\evidence\mapping_overfit_risk_report.json `
  --out-md docs\交接\evidence\mapping_overfit_risk_report.md
```

必须通过。若失败，不能继续冲指标，先清除 doc_id 特例或 gold leakage。

### 7.6 运行质量门禁

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report docs\交接\evidence\mapping_splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05
```

如果未通过，把输出失败原因复制到：

```text
docs/交接/evidence/mapping_quality_gate_result.md
```

并继续按 gap analysis 修复。

---

## 8. 第五阶段：扩大 blind / test 证据（有余力时执行）

当前 blind 只有 8 个，作为课程项目可以用，但防过拟合说服力不足。若时间允许，建议增加到至少 20 个。

### 8.1 添加原则

1. 新增 UIR 必须来自未参与调参的文档。
2. 新增文档按 doc_id 整体进入某一个 split。
3. 不允许同一 source_path 出现在多个 split。
4. 新增 blind gold 标注完成前，不得针对其单例调规则。
5. 若时间不足，至少补充 5～10 个 blind-like 文档，并在文档中说明样本规模限制。

### 8.2 更新文件

```text
examples/real_world/splits/mapping_split_manifest.json
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/uir/*.json
```

新增后运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir docs\交接\evidence\mapping_splits
```

---

## 9. 第六阶段：最终验收与文档收口（0.5 天）

### 9.1 完整验证命令

最终提交前执行：

```powershell
backend\.venv\Scripts\python.exe scripts\build_mapping_metric_baseline_snapshot.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out docs\交接\evidence\mapping_metric_baseline_snapshot.md

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir docs\交接\evidence\mapping_splits

backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-json docs\交接\evidence\mapping_gap_analysis.json `
  --out-md docs\交接\evidence\mapping_gap_analysis.md

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-json docs\交接\evidence\mapping_overfit_risk_report.json `
  --out-md docs\交接\evidence\mapping_overfit_risk_report.md

backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report docs\交接\evidence\mapping_splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05

backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
Pop-Location
```

如果前端测试耗时或环境不稳定，至少运行 backend 完整验证，并在文档中如实说明前端本轮未重跑。

### 9.2 最终文档必须更新

更新：

1. `README.md`
2. `docs/交接/mapping_recall_085_guarded_sprint.md`
3. `docs/交接/requirement_mapping.md`
4. `docs/交接/acceptance_report.md`
5. `docs/交接/project_status.md`

每个文档必须统一以下信息：

```text
- 当前最终评测日期
- dataset size
- dev/test/blind split 数量
- auto_mapping_recall
- assisted_mapping_recall
- review_required_rate
- required_missing_count
- badcase violations
- package verification
- overfit scan result
- quality gate result
- verify_all result
```

### 9.3 最终 sprint 文档模板

在 `docs/交接/mapping_recall_085_guarded_sprint.md` 中追加：

```markdown
## Final Sprint Result

| Metric | Value |
| --- | ---: |
| Dataset size | X |
| Dev assisted recall | X.XXX |
| Test assisted recall | X.XXX |
| Blind assisted recall | X.XXX |
| Auto mapping recall overall | X.XXX |
| Assisted mapping recall overall | X.XXX |
| Review-required rate | X.XXX |
| Required missing | 0 |
| Badcase violations | 0 |
| Package pass rate | 1.000 |
| Overfit scan | Pass |
| Quality gate | Pass / Failed |
| verify_all | N passed |

### Conclusion

本轮是否达到 0.85：是 / 否。

若否，剩余缺口为：……
```

---

## 10. 每日冲刺安排

### Day 0 / 立即开始：证据与口径修复

目标：避免文档和证据链扣分。

任务：

1. 新建 `docs/交接/evidence/`。
2. 把 baseline/split/gap/overfit/quality gate 证据输出到该目录。
3. 修复 README 中打不开的 `reports/*` 链接。
4. 统一测试数量和 recall 口径。
5. 提交 commit：`docs: fix mapping sprint evidence and metric wording`。

验收：

1. README 链接可打开。
2. 文档不再混用 0.806 和 0.609。
3. 明确说明历史 recall 与当前 guarded sprint recall 的区别。

---

### Day 1：required missing 清零

目标：`required_missing_count = 0`。

任务：

1. 实现 `policy_doc.issuer` source-backed candidates。
2. 实现 `policy_doc.publish_date` source-backed candidates。
3. 加入负样本保护。
4. 新增单测。
5. 重跑 non-procurement mapping 和 split evaluator。

验收：

1. `issuer` missing 从 2 降到 0。
2. `publish_date` missing 从 2 降到 0。
3. badcase violations 仍为 0。
4. overfit scan pass。
5. package pass 100%。

---

### Day 2：高收益 recall 提升

目标：把 assisted recall 尽快拉高。

任务：

1. 修 `meeting_doc.topics`。
2. 修 `general_doc.deadline`。
3. 修 `policy_doc.target_audience`。
4. 修 `policy_doc.policy_measures`。
5. 修 `meeting_doc.action_items` 和 `meeting_doc.decisions`。
6. 每修完一类字段就跑 split evaluator。

验收：

1. dev/test/blind assisted recall 均明显提升。
2. review_required_rate 不应大幅上升。
3. badcase violations 仍为 0。
4. required_missing 仍为 0。

---

### Day 3：门禁、文档、收尾

目标：形成可提交版本。

任务：

1. 运行完整 quality gate。
2. 运行 overfit scan。
3. 运行 verify_all。
4. 更新 README / requirement_mapping / guarded_sprint / acceptance_report。
5. 写明最终是否达标。
6. 提交最终 commit。

验收：

1. 所有链接可打开。
2. 指标口径一致。
3. 没有虚假达标表达。
4. 即使未达 0.85，也能说明做了什么、提升了多少、剩余什么。

---

## 11. Codex 执行提示词

可以直接把下面这段交给 Codex：

```text
你正在维护 GitHub 仓库 Yiliiiiiiii/NEU-Practical-training-Task-5。当前任务是继续推进课题 5 字段映射 0.85 冲刺。请严格遵守以下要求：

1. 不允许根据 doc_id 写特例规则。
2. 不允许 runtime mapping 读取 mapping_gold.jsonl、expected_mappings、known_badcases 等 gold 信息。
3. 不允许为了提高 assisted recall 大幅增加 review-required。
4. badcase violations 必须保持 0。
5. required_missing 必须优先降到 0。
6. package verification 必须保持 100%。
7. LLM suggestion 不得自动 accepted。
8. 所有增强必须是 source-backed candidate extraction 或字段通用规则。

当前优先级：
P0：policy_doc.issuer、policy_doc.publish_date，先把 required_missing 清零。
P1：meeting_doc.topics、general_doc.deadline。
P2：policy_doc.target_audience、policy_doc.policy_measures、meeting_doc.action_items、meeting_doc.decisions。

请先修复证据链：将 baseline/split/gap/overfit/quality gate 输出到 docs/交接/evidence/，并更新 README、docs/交接/requirement_mapping.md、docs/交接/mapping_recall_085_guarded_sprint.md，避免链接指向未提交的 reports/* 文件。

然后实现 source-backed candidate extraction：
- policy_doc.issuer：支持 发布单位、发文机关、制定机关、印发机关、主管部门、发布机构、文末署名机构 等强证据；禁止 来源网站、联系人、责任编辑 自动映射 issuer。
- policy_doc.publish_date：支持 发布日期、公布日期、发布时间、印发日期、发文日期、文末署名日期；禁止 retrieved_at、施行日期、实施日期 自动映射 publish_date；成文日期不要自动作为 publish_date。
- meeting_doc.topics：从议题列表、小标题、会议研究/审议/听取/传达学习等句式抽取主题。
- general_doc.deadline：从 截止时间、申报截止、受理时间、办理期限、X 前提交 等 label/句式抽取。

每类字段都要新增或更新测试，覆盖正例与负例。

每轮修改后执行：
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py --report reports\non_procurement_mapping_eval_report.json --out-dir docs\交接\evidence\mapping_splits
backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py --report reports\non_procurement_mapping_eval_report.json --out-json docs\交接\evidence\mapping_gap_analysis.json --out-md docs\交接\evidence\mapping_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py --out-json docs\交接\evidence\mapping_overfit_risk_report.json --out-md docs\交接\evidence\mapping_overfit_risk_report.md
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py --report docs\交接\evidence\mapping_splits\summary.json --min-assisted-recall 0.85 --max-badcase-violations 0 --max-required-missing 0 --max-dev-test-gap 0.05 --max-test-blind-gap 0.05

最终运行：
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

如果 quality gate 未通过，不要声称达标；请在 docs/交接/mapping_recall_085_guarded_sprint.md 中如实记录当前指标、失败原因和下一步 gap。
```

---

## 12. 最终检查清单

提交前逐项确认：

| Check | Required |
| --- | --- |
| README 链接可打开 | 是 |
| 指标口径统一 | 是 |
| required_missing | 0 |
| badcase violations | 0 |
| package pass rate | 100% |
| overfit scan | Pass |
| 没有 doc_id 特例 | 是 |
| 没有 gold leakage | 是 |
| review_required_rate 未异常膨胀 | 是 |
| dev/test/blind summary 已生成 | 是 |
| quality gate 结果已记录 | 是 |
| verify_all 结果已记录 | 是 |
| 最终是否达 0.85 已如实说明 | 是 |

---

## 13. 最终建议

本轮时间紧，不建议继续做大范围新功能。最有效路径是：

1. **先清零 required missing**，因为这是硬门禁。
2. **再用 source-backed extraction 修高收益字段**，不要只加 alias。
3. **每一轮都跑 split evaluator + overfit scan + quality gate**。
4. **最后统一文档和证据链**，不要留下打不开的报告链接和互相矛盾的测试数量。

只要做到这一点，即使最终 0.85 没完全通过，也能证明项目是按治理级工程方式推进，而不是临时刷指标。
