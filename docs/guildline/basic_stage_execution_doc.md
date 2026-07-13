# 课题 5 基本阶段执行文档：完整覆盖主体要求并形成可复现证据

> 交付对象：Codex / 项目推进人员  
> 适用仓库：`Yiliiiiiiii/NEU-Practical-training-Task-5`  
> 建议起点分支：`codex/mapping-085-source-backed`  
> 阶段目标：在不追求“严格生产级独立 shadow/blind”完全体的前提下，先完成课题 5 主体能力闭环，使项目具备课程验收层面的完整覆盖、可复现证据、诚实指标口径和可演示流程。  
> 当前已知状态：`required_missing = 0`、`badcase_violations = 0`、`package_pass = 50/50`、`strict_pass = 48/50`，但 `overall assisted recall ≈ 0.8097`，`dev/test assisted recall` 尚未达到 0.85。  

---

## 0. 基本阶段的定位

本阶段不是“一周生产级终局”，而是“先把课题 5 主体要求完整打通并留下可复现证据”。后续强化阶段再做更严格的 production shadow / independent blind corpus、生产级门禁、长期回归和更大规模评测。

本阶段完成后，答辩口径应为：

```text
项目已完整覆盖课题 5 的主体链路：UIR/External UIR 输入、Schema/Template 驱动字段映射、字段转换、Schema 校验、分段/摘要/标签/关键词、JSON + Markdown 双形态成果包、manifest/checksum、下游消费契约、Review/Knowledge、Lineage、DeepSeek suggestion 和 Codex review subagent 的可控人机协同。所有关键能力均有可复现脚本与 evidence report。

字段映射指标以 auto recall、assisted recall、review-required rate 分开报告；若最终 quality gate 未完全通过，不能宣称 0.85 已达成，只能说明当前差距、下一阶段计划和安全边界。
```

---

## 1. 阶段目标与退出标准

### 1.1 P0 必达目标

P0 是必须完成的内容。没有完成 P0，不建议进入最终答辩材料收口。

| 编号 | 目标 | 必须达到的结果 |
|---|---|---|
| P0-1 | 文档证据可打开 | README、acceptance_report、requirement_mapping、project_status 中引用的 evidence 文件全部存在于仓库可访问路径。 |
| P0-2 | 指标口径统一 | 全仓库对 mapping 指标统一使用 `auto_mapping_recall`、`assisted_mapping_recall`、`review_required_rate`，旧 `average_recall` 必须标注为 legacy assisted recall。 |
| P0-3 | 字段映射继续冲刺 | 以 `general_doc`、`meeting_doc` 为主，尽量将 dev/test/blind assisted recall 全部推进到 `>=0.85`；如未达成，必须保留真实 quality gate failure report，不得虚报。 |
| P0-4 | required missing 保持清零 | `required_missing_count = 0`。 |
| P0-5 | badcase safety 保持 | `badcase_violations = 0`，`high_risk_auto_accepted = 0`。 |
| P0-6 | Package 与下游契约 | package verification 100%，下游 contract 继续通过。 |
| P0-7 | DeepSeek 能力验证 | 新增 DeepSeek mapping suggestion evaluation，证明大模型能提供疑难映射候选、理由、置信度和风险标记，但默认不自动接受。 |
| P0-8 | Codex 子智能体 review | 新增 review subagent dry-run 报告，模拟人工视角审核 review-required / low-confidence candidates，默认不写生产规则。 |
| P0-9 | 内容组织指标补证据 | 新增 tag / summary faithfulness 抽样评测报告，覆盖内容标签、管理标签、摘要忠实度。 |
| P0-10 | 一键复现 | 提供 `scripts/run_basic_stage_verification.ps1` 或等效命令清单，一次性跑核心评测并生成 evidence pack。 |

### 1.2 P1 加分目标

P1 是建议完成的加分项，能显著提高答辩说服力，但如果时间紧张，不能影响 P0。

| 编号 | 加分项 | 价值 |
|---|---|---|
| P1-1 | LLM ablation 对照 | 展示 deterministic only、DeepSeek suggestion、review-assisted 三种模式差异。 |
| P1-2 | Review impact preview | 子智能体 review 不直接生效，但输出“如果应用将提升哪些字段”的 impact preview。 |
| P1-3 | UI / API 证据页 | 在 workbench 或 docs 中展示 Evaluation / Review / Evidence 面板截图或调用路径。 |
| P1-4 | 新增 5～10 个 blind-like 样例 | 不追求生产级，但能增强泛化说明。 |
| P1-5 | 过拟合扫描增强 | 从 `doc_id` / gold leakage 扩展到真实标题、地名、会议编号、正文长片段硬编码。 |
| P1-6 | 最终答辩 demo 脚本 | 形成 5～8 分钟完整演示脚本，覆盖输入、映射、review、package、downstream、evidence。 |

---

## 2. 当前差距判断

当前分支已经完成了一轮重要增强：

```text
Dataset size: 50
Overall auto recall: 0.7774798927613941
Overall assisted recall: 0.8096514745308311
Review-required rate: 0.043583535108958835
Review-required count: 18
Required missing: 0
Badcase violations: 0
Package pass rate: 1.000
Strict pass: 48/50
Quality gate: failed
Failure: dev assisted recall 0.807 < 0.850; test assisted recall 0.794 < 0.850
```

剩余短板按优先级排序：

1. `general_doc` assisted recall 最低，需要优先优化。
2. `meeting_doc` 仍有 source-name exact recall 和 evidence alignment 缺口。
3. `policy_doc` 已接近达标，不宜大幅放宽规则，只做低风险 alignment。
4. DeepSeek 已接入但缺少“量化证明其能力”的报告。
5. Codex 子智能体 review 需要形成可复现报告，而不只是概念说明。
6. tag / summary / field operation / dual-format consistency 等非映射指标证据不够集中。
7. 文档里历史验证数量与指标口径仍需统一。

---

## 3. 分支与提交策略

### 3.1 建议分支

从当前阶段分支继续开新分支：

```powershell
git checkout codex/mapping-085-source-backed
git pull
git checkout -b codex/basic-topic5-complete-evidence
```

### 3.2 提交粒度

不要一个大 commit 全塞进去。建议至少分 5 类提交：

```text
commit 1: fix overfit-risk hardcoded text and doc evidence paths
commit 2: improve general/meeting mapping recall with generic source-backed candidates
commit 3: add DeepSeek mapping suggestion evaluation
commit 4: add Codex review subagent dry-run evaluation
commit 5: add content tag/summary and final basic-stage evidence pack
commit 6: update README/acceptance/requirement/project_status/final_demo_script
```

### 3.3 严禁事项

任何情况下都不要做以下事情：

```text
禁止根据 doc_id 分支。
禁止读取 mapping_gold.jsonl、expected_mappings、known_badcases 作为 runtime mapping 输入。
禁止把 DeepSeek 输出直接 auto accepted。
禁止把 Codex 子智能体 review 结果默认写入 active knowledge pack。
禁止通过大幅提高 review-required 来刷 assisted recall。
禁止删除 badcase 或降低 badcase 检查阈值。
禁止修改 quality gate 让它“假通过”。
禁止把未运行的评测写成 passed。
```

---

## 4. P0-1：证据路径与文档引用修复

### 4.1 目标

所有答辩和验收文档引用的证据必须在仓库中可打开。由于 `.gitignore` 默认忽略 `reports/*`，建议基本阶段的可提交证据统一放到：

```text
docs/交接/evidence/basic_stage/
```

### 4.2 建议目录结构

```text
docs/交接/evidence/basic_stage/
  mapping/
    mapping_metric_snapshot.md
    mapping_splits_summary.md
    mapping_quality_gate_result.md
    mapping_gap_analysis.md
    mapping_overfit_risk_report.md
  llm/
    deepseek_mapping_suggestion_eval_report.json
    deepseek_mapping_suggestion_eval_report.md
    llm_ablation_report.md                         # P1 可选
  review/
    codex_review_subagent_report.json
    codex_review_subagent_report.md
    review_impact_preview.md                       # P1 可选
  content/
    content_tag_summary_quality_report.json
    content_tag_summary_quality_report.md
  package/
    package_consistency_report.json
    package_consistency_report.md
    downstream_contract_eval_report.md
  final/
    basic_stage_acceptance_matrix.md
    basic_stage_reproducibility_commands.md
    basic_stage_final_gate_result.md
```

### 4.3 操作步骤

1. 运行现有 mapping、split、gap、overfit、quality gate 脚本。
2. 将核心结果复制到 `docs/交接/evidence/basic_stage/mapping/`。
3. 后续新增 LLM、review、content、package 评测也输出到该目录。
4. 更新 README 与交接文档链接，禁止继续链接未提交的临时 `reports/*` sprint 文件，除非该文件已明确被 `.gitignore` 放行。

### 4.4 验收检查

运行：

```powershell
python scripts/check_doc_links.py docs\交接 README.md
```

如果项目没有 `check_doc_links.py`，则新增一个轻量脚本，至少检查 Markdown 中的相对链接是否存在。

---

## 5. P0-2：删除或泛化样本文本级硬编码

### 5.1 背景

当前代码中已发现类似真实样本文本片段的判断，例如具体地名、届次、会议编号组合。即使不是 `doc_id` 特例，也会被评审认为有隐性过拟合风险。

### 5.2 必做修改

在 `backend/app/services/candidate_service.py` 等 runtime mapping / candidate extraction 代码中搜索：

```powershell
Select-String -Path backend\app\services\*.py -Pattern "汨罗|长宁|沙县|张家港|昆都仑|乌鲁木齐|第13届|第47次|real_policy_|real_general_|real_meeting_|doc_id"
```

将具体文本特例改成通用模式。例如：

错误方式：

```python
elif "汨罗市第13届人民政府第47次" in compact_text:
    source_name = "meeting sentence"
```

正确方式：

```python
elif re.search(r"第\s*\d+\s*届.*?第\s*\d+\s*次.*?会议", compact_text):
    source_name = "meeting sentence"
```

或更稳妥：

```python
elif self._looks_like_government_meeting_opening(compact_text):
    source_name = "meeting sentence"
```

并实现：

```python
def _looks_like_government_meeting_opening(self, text: str) -> bool:
    return bool(
        re.search(r"第\s*\d+\s*届.*?第\s*\d+\s*次", text)
        and "会议" in text
        and any(marker in text for marker in ("召开", "主持", "研究", "审议", "听取"))
    )
```

### 5.3 增强 overfit scanner

修改 `scripts/check_mapping_overfit_risk.py`，新增扫描模式：

```text
1. 真实地名 + 会议届次 + 次数完整组合
2. `real_*` 样例标题原文长片段
3. 真实政策样例标题中的 8 字以上连续片段
4. 具体 source_path 指向 examples/real_world/uir 的硬编码
5. 具体机构名 + 具体样例字段组合硬编码
```

输出新增字段：

```json
{
  "sample_text_snippet_findings": 0,
  "source_path_specific_findings": 0,
  "real_title_snippet_findings": 0
}
```

### 5.4 验收标准

```text
doc_id_specific_rules_found = 0
gold_leakage_found = 0
sample_text_snippet_findings = 0
source_path_specific_findings = 0
risk_level = low
```

---

## 6. P0-3：字段映射最后一轮基本冲刺

### 6.1 总原则

这轮不是靠硬调单例，而是做通用 source-backed candidate extraction：

```text
优先用 source_name / label / heading / section / metadata 的可解释证据。
低风险字段可以 accepted。
中高风险字段进入 review-required。
宁可保留 review，也不要产生 badcase violation。
review_required_rate 目标 <= 0.08。
```

### 6.2 目标指标

理想目标：

```text
overall assisted_mapping_recall >= 0.85
dev assisted_mapping_recall >= 0.85
test assisted_mapping_recall >= 0.85
blind assisted_mapping_recall >= 0.85
auto_mapping_recall >= 0.80
review_required_rate <= 0.08
required_missing_count = 0
badcase_violations = 0
package_pass_rate = 1.0
```

最低可提交线：

```text
overall assisted_mapping_recall >= 0.83
required_missing_count = 0
badcase_violations = 0
package_pass_rate = 1.0
所有未达 0.85 的 split 必须在 quality gate report 中如实展示
不能写“已达到 0.85”
```

### 6.3 general_doc 优先优化

当前 `general_doc` 是最大短板。优先字段：

```text
service_object
application_conditions
application_materials
process_steps
contact
deadline
source/title/content 的 source-name exact alignment
```

#### 6.3.1 service_object

新增或增强 label：

```text
服务对象
适用对象
适用范围
申请对象
办理对象
面向对象
申报主体
可申请主体
支持对象
受理对象
服务群体
面向群体
适用主体
项目单位
申报单位
申请人范围
```

安全规则：

```text
若 label 明确为服务对象/适用对象/申报主体，可 accepted。
若仅从长段落中推断，例如“本指南适用于……”但无明确 label，confidence 降低，可 review-required。
禁止把联系方式、办理窗口、主管部门映射为 service_object。
```

#### 6.3.2 application_conditions

新增或增强 label：

```text
申请条件
受理条件
办理条件
申报条件
申报要求
资格条件
基本条件
准入条件
申请资格
申报资格
应当符合以下条件
需满足以下条件
```

安全规则：

```text
标题/heading 后紧跟列表或段落，可以作为 section candidate。
如果段落同时出现材料、流程、联系方式，不能整段 accepted，应 review-required。
```

#### 6.3.3 application_materials

新增或增强 label：

```text
申请材料
申报材料
办理材料
提交材料
所需材料
材料清单
申请材料目录
附件材料
需提交以下材料
```

安全规则：

```text
列表块、表格行、heading+list 可信度高。
若只有“附件1/附件2”且无材料语义，不能自动 accepted。
```

#### 6.3.4 process_steps

新增或增强 label：

```text
办理流程
申请流程
申报流程
办理步骤
流程步骤
办理程序
申报方式
办理方式
在线办理
窗口办理
```

安全规则：

```text
流程类 heading + 编号列表可 accepted。
包含“电话/联系人/地址”的段落不能被 process_steps 吞掉。
```

#### 6.3.5 contact

新增或增强 label：

```text
联系电话
咨询电话
联系方式
服务电话
办理窗口电话
联系人
咨询方式
邮箱
电子邮箱
联系地址
```

正则建议：

```text
手机号：1[3-9]\d{9}
座机：0\d{2,3}[-\s]?\d{7,8}
邮箱：[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
```

安全规则：

```text
电话号码/邮箱可作为 contact accepted。
联系人姓名单独出现时 review-required。
不要把主管部门/发布单位映射为 contact。
```

#### 6.3.6 deadline

新增或增强 label / 句式：

```text
截止时间
申报截止时间
申请截止时间
受理截止时间
提交截止时间
办理期限
受理时间
申报时间
于 X 前提交
请于 X 前完成
截至 X
```

安全规则：

```text
明确 deadline label 可 accepted。
“发布日期/公开日期/成文日期”不能映射 deadline。
“办理时限 5 个工作日”可进入 deadline 或 processing_time；若 schema 无 processing_time，则 review-required。
```

### 6.4 meeting_doc 次优先优化

优先字段：

```text
meeting_date
meeting_number
meeting_title
topics
decisions
action_items
chairperson / attendees 边界
```

#### 6.4.1 meeting_date

通用来源：

```text
会议日期：XXXX年X月X日
会议时间：XXXX年X月X日
召开日期：XXXX年X月X日
XXXX年X月X日，XXX主持召开会议
第X届人民政府第Y次会议于XXXX年X月X日召开
```

禁止来源：

```text
发布日期
发布时间
成文日期
网页抓取时间
retrieved_at
```

### 6.4.2 meeting_number

新增或增强模式：

```text
第 X 次会议
第 X 届人民政府第 Y 次会议
常务会议第 X 次会议
专题会议第 X 次会议
会议纪要第 X 期
```

安全规则：

```text
会议编号必须包含“会议/纪要/届/次”等会议语义。
文件编号、政策文号不能映射为 meeting_number。
```

#### 6.4.3 topics

新增来源：

```text
会议议题
议题
会议研究事项
会议听取
会议审议
研究了以下事项
审议通过了
传达学习了
安排部署了
```

边界规则：

```text
不要把参会人员、主持人、时间地点映射为 topics。
如果段落同时包含多个事项，用列表或换行保留。
```

#### 6.4.4 decisions

新增来源：

```text
会议决定
会议原则同意
会议审议通过
会议要求
会议强调
同意
原则通过
决定
```

边界规则：

```text
“听取汇报”本身不是 decision，除非后面有决定/通过/同意。
```

#### 6.4.5 action_items

新增来源：

```text
由 X 负责
责成 X
要求 X 于 X 前完成
明确 X 牵头
下一步
工作安排
任务分工
```

安全规则：

```text
必须包含责任主体或动作要求。
纯会议议题不能自动映射 action_items。
```

### 6.5 policy_doc 低风险补齐

`policy_doc` 已接近 0.85，不建议大幅放宽。只做：

```text
source-name exact recall 修正
irregular heading alignment
policy_005 等剩余样例的通用规则抽象
不要扩大 source_site -> issuer 自动接受
不要把 附件1 / 页面栏目 / 来源网站 自动作为 issuer
```

优先字段：

```text
policy_measures
target_audience
responsible_departments
document_number
effective_date/publish_date 的 source-name alignment
```

---

## 7. P0-4：DeepSeek 基本能力验证

### 7.1 目标

证明 DeepSeek 在本项目中不是“摆设”，而是以安全受控方式参与疑难字段映射：

```text
规则先行。
DeepSeek 只处理低置信度或未命中的疑难项。
DeepSeek 输出 suggestion、confidence、rationale、risk_flags。
默认 report-only，不自动 accepted。
```

### 7.2 新增脚本

建议新增：

```text
scripts/eval_deepseek_mapping_suggestions.py
```

输入：

```text
--gold examples/real_world/gold/mapping_gold.jsonl
--report reports/non_procurement_mapping_eval_report.json
--uir-dir examples/real_world/uir
--mode report-only
--out-json docs/交接/evidence/basic_stage/llm/deepseek_mapping_suggestion_eval_report.json
--out-md docs/交接/evidence/basic_stage/llm/deepseek_mapping_suggestion_eval_report.md
```

### 7.3 触发范围

DeepSeek 不需要处理所有字段，只处理以下候选：

```text
1. deterministic missing 的 expected target
2. low-confidence fuzzy candidate
3. review-required candidate
4. source-name exact recall 未命中的长尾字段
```

每个文档最多发送：

```text
max_llm_requests_per_doc = 3
max_context_chars = 4000
```

避免成本失控和 prompt 污染。

### 7.4 Prompt 要求

DeepSeek prompt 必须要求输出结构化 JSON，不允许自由文本作为唯一结果：

```json
{
  "target_field": "service_object",
  "suggested_source_name": "服务对象",
  "suggested_source_path": "$.blocks.xxx.text",
  "value_sample": "...",
  "confidence": 0.82,
  "rationale": "原文标题为服务对象，后续段落列出适用主体",
  "risk_flags": [],
  "decision": "suggest_review"
}
```

允许的 decision：

```text
suggest_review
suggest_reject
insufficient_evidence
```

禁止 decision：

```text
auto_accept
activate_rule
write_template
```

### 7.5 报告指标

输出：

| 指标 | 含义 | 目标 |
|---|---|---:|
| llm_request_count | 请求次数 | 可控 |
| suggestion_count | 建议数 | > 0 |
| top1_hit_rate | top1 是否命中 gold | 尽量 > 0.60 |
| top3_hit_rate | top3 是否命中 gold | 尽量 > 0.75 |
| unsafe_suggestion_count | 违反 badcase 或高风险建议 | 0 |
| secret_leak_count | prompt/response 泄漏密钥 | 0 |
| llm_auto_accepted_count | 自动接受数 | 0 |
| deterministic_gap_covered | LLM 覆盖了多少 deterministic gap | 记录即可 |

### 7.6 验收口径

如果 DeepSeek 对主指标贡献有限，也要诚实写：

```text
DeepSeek 在基本阶段用于 report-only 疑难映射建议，未自动改变生产结果。其价值体现在候选解释、置信度、风险标记和人工复核辅助；生产规则仍由 deterministic mapping 与人工确认控制。
```

---

## 8. P0-5：Codex 子智能体模拟人工 Review

### 8.1 目标

用 Codex 子智能体充当“人工审核员”视角，审核 review-required、low-confidence、LLM suggested candidates，补齐“人机协同 + 可追溯 review”证据。

### 8.2 新增脚本

建议新增：

```text
scripts/eval_codex_review_subagent.py
```

输入：

```text
--mapping-report reports/non_procurement_mapping_eval_report.json
--llm-report docs/交接/evidence/basic_stage/llm/deepseek_mapping_suggestion_eval_report.json
--gold examples/real_world/gold/mapping_gold.jsonl
--mode dry-run
--out-json docs/交接/evidence/basic_stage/review/codex_review_subagent_report.json
--out-md docs/交接/evidence/basic_stage/review/codex_review_subagent_report.md
```

### 8.3 Review 对象

只审核：

```text
review-required candidates
low-confidence candidates
DeepSeek suggestions
potential badcase-risk candidates
```

不要让子智能体重新审全部字段，避免时间失控。

### 8.4 Review 输出结构

每条审核结果：

```json
{
  "doc_id": "real_general_xxx",
  "target_field": "service_object",
  "candidate_source_name": "服务对象",
  "candidate_source_path": "$.blocks.xxx.text",
  "decision": "approve | reject | uncertain",
  "confidence": 0.86,
  "reason": "标题为服务对象，内容列出适用主体，证据充分",
  "risk_flags": [],
  "would_apply": false
}
```

### 8.5 安全规则

```text
默认 dry-run。
would_apply 可以为 true，但实际 applied_count 必须为 0。
如果后续要 apply-safe，必须单独命令、单独报告、单独解释。
子智能体不能修改 mapping template。
子智能体不能直接写 active knowledge pack。
```

### 8.6 报告指标

| 指标 | 目标 |
|---|---:|
| reviewed_items | > 0 |
| approve_count | 记录 |
| reject_count | 记录 |
| uncertain_count | 记录 |
| agreement_with_gold | 尽量 > 0.80 |
| unsafe_approve_count | 0 |
| applied_count | 0 |
| potential_recall_gain | 记录 |

### 8.7 答辩口径

```text
Codex review subagent 模拟人工复核视角，只做 dry-run 审核与 impact preview，不直接改变生产结果。这样既展示人机协同，又避免 AI 自审 AI 造成不可控风险。
```

---

## 9. P0-6：内容标签与摘要忠实度评测

### 9.1 目标

补齐课题 5 中“分段、摘要、关键词、标签”的指标证据。

课题 5 不只看字段映射，还要求：

```text
分段准确
内容标签准确
管理标签按规则生成
摘要忠实，不引入原文没有的信息
关键词可用于下游检索或训练
```

### 9.2 新增脚本

```text
scripts/eval_content_tag_summary_quality.py
```

输入：

```text
--packages-root reports/real_world_packages
--sample-size 30
--out-json docs/交接/evidence/basic_stage/content/content_tag_summary_quality_report.json
--out-md docs/交接/evidence/basic_stage/content/content_tag_summary_quality_report.md
```

如果 `reports/real_world_packages` 不可用，则使用当前 non-procurement 50 个包或 task reports。

### 9.3 评测项

| 指标 | 目标 |
|---|---:|
| chunk_parse_pass_rate | 1.0 |
| source_link_coverage | >= 0.95 |
| content_tag_accuracy | >= 0.85 |
| management_tag_rule_pass_rate | 1.0 |
| quality_tag_rule_pass_rate | >= 0.95 |
| summary_faithfulness_pass_rate | >= 0.95 |
| summary_hallucination_count | 0 |
| keyword_non_empty_rate | >= 0.95 |

### 9.4 判断方式

基本阶段可采用混合评测：

```text
管理标签、quality tag、source links 用规则评测。
摘要忠实度、content tag 用抽样 + DeepSeek judge 或 Codex judge。
LLM judge 必须输出理由和引用原文 evidence。
```

### 9.5 输出报告模板

```markdown
# Content Tag and Summary Quality Report

## Summary
- sample_size:
- chunk_parse_pass_rate:
- source_link_coverage:
- content_tag_accuracy:
- management_tag_rule_pass_rate:
- summary_faithfulness_pass_rate:
- summary_hallucination_count:

## Failed Samples
| doc_id | chunk_id | issue | evidence | decision |

## Safety Notes
- LLM judge used only for evaluation.
- No production content was changed by LLM judge.
```

---

## 10. P0-7：字段操作、Schema 校验和错误定位证据

### 10.1 目标

课题 5 包含字段重命名、合并、拆分、校验等操作；统一要求也强调可评测。需要集中证明这些能力。

### 10.2 新增或整理报告

```text
docs/交接/evidence/basic_stage/final/field_operation_validation_report.md
```

### 10.3 必测项

| 项目 | 目标 |
|---|---:|
| rename operation accuracy | >= 0.95 |
| merge operation accuracy | >= 0.95 |
| split operation accuracy | >= 0.95 |
| type normalization accuracy | >= 0.95 |
| required field validation locating | 1.0 |
| schema error path locating | 1.0 |
| validation report parseable | 1.0 |

### 10.4 实现方式

如果已有测试，整理报告即可；如果没有，新增最小测试集：

```text
examples/operation_eval_cases/
  rename_cases.jsonl
  merge_cases.jsonl
  split_cases.jsonl
  validation_error_cases.jsonl
```

新增脚本：

```text
scripts/eval_field_operations_and_validation.py
```

输出：

```text
docs/交接/evidence/basic_stage/final/field_operation_validation_report.json
docs/交接/evidence/basic_stage/final/field_operation_validation_report.md
```

---

## 11. P0-8：双形态成果包一致性与下游消费证据

### 11.1 目标

证明 JSON / Markdown 双形态一致，manifest / checksum 正确，下游 RAG / training / CSV consumer 能读取。

### 11.2 建议脚本

如果已有 package verifier 和 downstream contract，新增一个汇总脚本：

```text
scripts/eval_basic_stage_package_consistency.py
```

输出：

```text
docs/交接/evidence/basic_stage/package/package_consistency_report.json
docs/交接/evidence/basic_stage/package/package_consistency_report.md
```

### 11.3 检查项

| 项目 | 目标 |
|---|---:|
| package_verify_pass_rate | 1.0 |
| manifest_exists_rate | 1.0 |
| checksum_pass_rate | 1.0 |
| json_parse_pass_rate | 1.0 |
| markdown_exists_rate | 1.0 |
| json_markdown_core_field_consistency | 1.0 |
| field_to_source_link_coverage | >= 0.95 |
| chunk_to_source_link_coverage | >= 0.95 |
| downstream_rag_jsonl_parse_pass | 1.0 |
| downstream_training_jsonl_parse_pass | 1.0 |
| downstream_csv_parse_pass | 1.0 |

### 11.4 注意事项

Package verification 本身不能代表字段语义正确。文档中必须保留说明：

```text
Package verification 证明结构、hash、required artifacts、parseability 和 traceability，不等同于每个字段语义完全正确。字段语义质量由 mapping evaluator 和 review/badcase reports 证明。
```

---

## 12. P0-9：一键复现脚本

### 12.1 目标

最终交给评审或自己演示时，不能只说“我跑过”。必须有一套可复现命令。

### 12.2 新增脚本

建议新增：

```text
scripts/run_basic_stage_verification.ps1
```

内容示例：

```powershell
$ErrorActionPreference = "Stop"

Write-Host "[1/9] Verify backend, ruff, frontend build, openapi"
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Write-Host "[2/9] Frontend tests"
Push-Location frontend
npm.cmd test
Pop-Location

Write-Host "[3/9] Non-procurement mapping eval"
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md

Write-Host "[4/9] Split evaluator"
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir docs\交接\evidence\basic_stage\mapping\splits

Write-Host "[5/9] Gap analysis and overfit scan"
backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-json docs\交接\evidence\basic_stage\mapping\mapping_gap_analysis.json `
  --out-md docs\交接\evidence\basic_stage\mapping\mapping_gap_analysis.md

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-json docs\交接\evidence\basic_stage\mapping\mapping_overfit_risk_report.json `
  --out-md docs\交接\evidence\basic_stage\mapping\mapping_overfit_risk_report.md

Write-Host "[6/9] Mapping quality gate"
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report docs\交接\evidence\basic_stage\mapping\splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05 `
  *> docs\交接\evidence\basic_stage\mapping\mapping_quality_gate_result.md

Write-Host "[7/9] DeepSeek suggestion eval"
backend\.venv\Scripts\python.exe scripts\eval_deepseek_mapping_suggestions.py `
  --mode report-only `
  --out-json docs\交接\evidence\basic_stage\llm\deepseek_mapping_suggestion_eval_report.json `
  --out-md docs\交接\evidence\basic_stage\llm\deepseek_mapping_suggestion_eval_report.md

Write-Host "[8/9] Codex review subagent eval and content quality eval"
backend\.venv\Scripts\python.exe scripts\eval_codex_review_subagent.py `
  --mode dry-run `
  --out-json docs\交接\evidence\basic_stage\review\codex_review_subagent_report.json `
  --out-md docs\交接\evidence\basic_stage\review\codex_review_subagent_report.md

backend\.venv\Scripts\python.exe scripts\eval_content_tag_summary_quality.py `
  --out-json docs\交接\evidence\basic_stage\content\content_tag_summary_quality_report.json `
  --out-md docs\交接\evidence\basic_stage\content\content_tag_summary_quality_report.md

Write-Host "[9/9] Package consistency and final matrix"
backend\.venv\Scripts\python.exe scripts\eval_basic_stage_package_consistency.py `
  --out-json docs\交接\evidence\basic_stage\package\package_consistency_report.json `
  --out-md docs\交接\evidence\basic_stage\package\package_consistency_report.md

backend\.venv\Scripts\python.exe scripts\build_basic_stage_acceptance_matrix.py `
  --out docs\交接\evidence\basic_stage\final\basic_stage_acceptance_matrix.md
```

### 12.3 注意

如果 quality gate 未通过，脚本可能中断。为了保留失败证据，可以在脚本中捕获 gate 失败但继续生成最终矩阵：

```powershell
try {
  backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py ... *> docs\...\mapping_quality_gate_result.md
} catch {
  Write-Host "Mapping quality gate failed; failure is recorded and the script continues for evidence packaging."
}
```

---

## 13. P0-10：最终验收矩阵

新增：

```text
scripts/build_basic_stage_acceptance_matrix.py
docs/交接/evidence/basic_stage/final/basic_stage_acceptance_matrix.md
```

矩阵必须覆盖课题 5 主体要求和统一要求。

### 13.1 课题 5 主体要求矩阵

| 要求 | 证据 | 状态口径 |
|---|---|---|
| 输入 UIR / External UIR | external adapter eval、CLI/API demo | passed |
| Schema 驱动字段映射 | mapping eval、split eval | pass / partial |
| 规则 + 大模型疑难映射 | deterministic + DeepSeek suggestion eval | passed if report exists |
| 置信度与人工复核 | mapping report、review subagent report | passed |
| 字段重命名/合并/拆分/校验 | field operation validation report | passed if >=0.95 |
| Schema 校验错误定位 | validation report | passed if locating=1.0 |
| 分段、摘要、关键词 | content quality report | passed if thresholds met |
| 内容标签/管理标签 | content quality report | passed if thresholds met |
| JSON + Markdown 双形态 | package consistency report | passed if consistency=1.0 |
| manifest/checksum | package verifier | passed |
| RAG/training/CSV 下游读取 | downstream contract | passed |
| 可追溯/可回放 | lineage + task snapshots | passed |
| 私有化部署 | deployment docs + docker/local | passed |
| LLM 可关闭/替换 | ablation / config docs | passed if documented |

### 13.2 统一要求矩阵

| 统一要求 | 证据 | 状态 |
|---|---|---|
| 服务化 API | OpenAPI 63 paths、API examples | passed |
| CLI / SDK 可集成 | CLI、Python SDK | passed |
| 可评测 | evaluation scripts | passed |
| 可复现 | run_basic_stage_verification.ps1 | passed |
| 可追溯 | lineage reports | passed |
| 可回放 | task snapshots, reports, package | passed |
| 可私有化部署 | docker/local docs | passed |
| 大模型可关闭 | DeepSeek report-only / disabled default | passed |
| 安全与审计 | badcase, secret redaction, review governance | passed |

### 13.3 状态枚举

只能使用以下状态：

```text
passed
partial
not_run
not_in_scope
failed
```

禁止使用：

```text
basically passed
almost done
probably passed
should be fine
```

---

## 14. 文档收口任务

必须更新以下文档：

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
docs/交接/mapping_recall_085_guarded_sprint.md
```

### 14.1 README 更新要点

README 只保留最新基本阶段指标：

```text
Dataset size
Auto mapping recall
Assisted mapping recall
Review-required rate
Dev/test/blind assisted recall
Required missing
Badcase violations
Package verification
Quality gate result
DeepSeek suggestion eval result
Codex review subagent dry-run result
Content tag/summary quality result
```

历史 Phase C/D/I 指标可以保留，但必须放到“Historical records”，不能与当前结果混用。

### 14.2 acceptance_report 更新要点

修正验证数量口径，例如：

```text
backend pytest: 使用本次 verify_all 实际输出，不要保留 662/713/730 混乱口径。
frontend tests: 使用本次 npm test 实际输出。
OpenAPI paths: 使用本次输出。
```

### 14.3 requirement_mapping 更新要点

增加三条：

```text
DeepSeek suggestion evaluation: report-only, no auto accept.
Codex review subagent: dry-run human-like review, no production write.
Content tag / summary faithfulness evaluation: sampled and reproducible.
```

### 14.4 final_demo_script 更新要点

演示顺序建议：

```text
1. 展示 UIR 输入。
2. 创建 task 并执行。
3. 展示 mapping report：confidence、review-required、evidence、badcase safety。
4. 展示 DeepSeek suggestion report：疑难项建议但不自动接受。
5. 展示 Codex review subagent：模拟人工审核、dry-run。
6. 展示 package：JSON + Markdown + manifest + checksum。
7. 展示 downstream contract：RAG/training/CSV 可读取。
8. 展示 basic_stage_acceptance_matrix：哪些 passed，哪些 partial。
```

---

## 15. 加分项执行建议

以下加分项在 P0 完成后做。

### 15.1 P1-1：LLM ablation

新增：

```text
scripts/eval_llm_ablation.py
```

对比：

```text
deterministic_only
llm_suggestion_report_only
llm_review_assisted_dry_run
```

输出：

```text
docs/交接/evidence/basic_stage/llm/llm_ablation_report.md
```

### 15.2 P1-2：Review impact preview

输出：

```text
docs/交接/evidence/basic_stage/review/review_impact_preview.md
```

包含：

```text
如果人工采纳这些 approve 建议，哪些字段 recall 可能提升。
哪些建议因风险被 reject。
哪些建议 uncertain，不能使用。
```

### 15.3 P1-3：新增 blind-like 样例

新增 5～10 个文档级 UIR，不参与当前规则调试。用于答辩时说明泛化意识。

目录建议：

```text
examples/real_world/blind_like_basic_stage/uir/
examples/real_world/blind_like_basic_stage/gold/
```

如果时间不够，可以只建 inventory 与 manual note，不强求全量 gold。

### 15.4 P1-4：过拟合扫描增强

在 P0 删除硬编码后，继续加强 scanner：

```text
扫描真实文档标题片段。
扫描地名 + 届次 + 会议编号组合。
扫描 source_path 精确指向样例路径。
扫描 if/elif 中包含真实样例专有名称。
```

### 15.5 P1-5：答辩演示材料

新增：

```text
docs/交接/basic_stage_demo_script.md
```

以 5～8 分钟为目标，每一步给出命令、页面、报告和解释口径。

---

## 16. 建议时间安排

假设基本阶段用 3 天完成：

### Day 1：收口安全与映射指标

```text
上午：修 evidence 路径、文档链接、删除样本文本硬编码。
下午：优化 general_doc / meeting_doc source-backed candidates。
晚上：跑 mapping eval、split eval、quality gate、overfit scan。
```

### Day 2：补 DeepSeek 与 Review 子智能体证据

```text
上午：实现 DeepSeek mapping suggestion evaluation。
下午：实现 Codex review subagent dry-run evaluation。
晚上：跑 LLM/report/review 评测，检查 unsafe count 和 applied count。
```

### Day 3：补非映射指标与文档收口

```text
上午：实现 content tag / summary quality、field operation / validation、package consistency 报告。
下午：写 basic_stage_acceptance_matrix，更新 README/acceptance/requirement/project_status/demo。
晚上：跑 run_basic_stage_verification.ps1，提交最终 evidence pack。
```

如果只有 1～2 天：

```text
优先顺序：
1. 删除硬编码 + overfit scan pass
2. mapping dev/test 尽量冲到 0.85
3. DeepSeek suggestion eval
4. Codex review subagent dry-run
5. 文档口径统一
6. content tag/summary 抽样报告
```

---

## 17. 最终质量门禁

基本阶段最终执行：

```powershell
.\scripts\run_basic_stage_verification.ps1
```

或手动执行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
Pop-Location

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py --report reports\non_procurement_mapping_eval_report.json --out-dir docs\交接\evidence\basic_stage\mapping\splits

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py --out-json docs\交接\evidence\basic_stage\mapping\mapping_overfit_risk_report.json --out-md docs\交接\evidence\basic_stage\mapping\mapping_overfit_risk_report.md

backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py --report docs\交接\evidence\basic_stage\mapping\splits\summary.json --min-assisted-recall 0.85 --max-badcase-violations 0 --max-required-missing 0 --max-dev-test-gap 0.05 --max-test-blind-gap 0.05

backend\.venv\Scripts\python.exe scripts\eval_deepseek_mapping_suggestions.py --mode report-only --out-json docs\交接\evidence\basic_stage\llm\deepseek_mapping_suggestion_eval_report.json --out-md docs\交接\evidence\basic_stage\llm\deepseek_mapping_suggestion_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_codex_review_subagent.py --mode dry-run --out-json docs\交接\evidence\basic_stage\review\codex_review_subagent_report.json --out-md docs\交接\evidence\basic_stage\review\codex_review_subagent_report.md

backend\.venv\Scripts\python.exe scripts\eval_content_tag_summary_quality.py --out-json docs\交接\evidence\basic_stage\content\content_tag_summary_quality_report.json --out-md docs\交接\evidence\basic_stage\content\content_tag_summary_quality_report.md

backend\.venv\Scripts\python.exe scripts\eval_basic_stage_package_consistency.py --out-json docs\交接\evidence\basic_stage\package\package_consistency_report.json --out-md docs\交接\evidence\basic_stage\package\package_consistency_report.md

backend\.venv\Scripts\python.exe scripts\build_basic_stage_acceptance_matrix.py --out docs\交接\evidence\basic_stage\final\basic_stage_acceptance_matrix.md
```

---

## 18. 最终提交前检查清单

### 18.1 指标检查

```text
[ ] overall assisted recall 已记录。
[ ] auto recall 已记录。
[ ] dev/test/blind assisted recall 已记录。
[ ] required_missing = 0。
[ ] badcase_violations = 0。
[ ] package pass = 100%。
[ ] review_required_rate 已记录，且未异常膨胀。
[ ] quality gate passed 或 failure 被如实记录。
```

### 18.2 DeepSeek 检查

```text
[ ] DeepSeek suggestion report 存在。
[ ] suggestion_count > 0。
[ ] unsafe_suggestion_count = 0。
[ ] secret_leak_count = 0。
[ ] llm_auto_accepted_count = 0。
[ ] 文档明确 DeepSeek report-only，不自动写规则。
```

### 18.3 Codex review 子智能体检查

```text
[ ] review subagent report 存在。
[ ] reviewed_items > 0。
[ ] unsafe_approve_count = 0。
[ ] applied_count = 0，除非有单独 safe apply 说明。
[ ] review decisions 有理由和 evidence。
```

### 18.4 内容组织检查

```text
[ ] content tag / summary quality report 存在。
[ ] summary_hallucination_count = 0 或失败样例已列出。
[ ] source_link_coverage 已记录。
[ ] management_tag_rule_pass_rate 已记录。
```

### 18.5 文档检查

```text
[ ] README 指标为最新基本阶段指标。
[ ] acceptance_report 不再混用旧 pytest 数量。
[ ] requirement_mapping 增加 DeepSeek 和 Codex review 证据。
[ ] project_status 说明当前 passed/partial/not_run。
[ ] final_demo_script 可按步骤演示。
[ ] 所有 Markdown 链接可打开。
```

---

## 19. 给 Codex 的直接执行提示词

可以直接把下面内容交给 Codex：

```text
你现在在仓库 Yiliiiiiiii/NEU-Practical-training-Task-5 中工作。请基于 codex/mapping-085-source-backed 分支创建 codex/basic-topic5-complete-evidence 分支，完成“课题 5 基本阶段”的执行目标：让项目完整覆盖课题 5 主体要求，并形成可复现证据。

请严格遵守：
1. 不得根据 doc_id、真实样例标题、具体地名+会议届次+会议编号写特例规则。
2. 不得让 runtime mapping 读取 gold labels、expected_mappings、known_badcases。
3. DeepSeek 只能 report-only 或 review suggestion，不得 auto accepted，不得激活 schema/template，不得写 production rules。
4. Codex review subagent 只能 dry-run 模拟人工审核，默认 applied_count=0。
5. 不得降低 badcase、required_missing、quality gate 阈值。
6. 如果 quality gate 未通过，必须如实保留 failure report，不能宣称 0.85 已达成。

P0 必做：
1. 修复 evidence 路径，统一放入 docs/交接/evidence/basic_stage/。
2. 删除或泛化 runtime 中的样本文本级硬编码，并增强 overfit scanner。
3. 优先提升 general_doc，其次 meeting_doc 的 source-backed candidate extraction，目标 dev/test/blind assisted recall >=0.85；保持 required_missing=0、badcase=0、review_required_rate<=0.08、package=100%。
4. 新增 DeepSeek mapping suggestion evaluation，输出 suggestion/confidence/rationale/risk_flags，llm_auto_accepted_count 必须为 0。
5. 新增 Codex review subagent dry-run evaluation，输出 approve/reject/uncertain/agreement_with_gold/unsafe_approve_count/applied_count，applied_count 默认 0。
6. 新增 content tag / summary faithfulness 抽样评测。
7. 新增或整理 field operation / schema validation / package consistency 报告。
8. 新增 run_basic_stage_verification.ps1 和 basic_stage_acceptance_matrix.md。
9. 更新 README、acceptance_report、requirement_mapping、project_status、final_demo_script，统一最新指标和证据链接。
10. 运行 verify_all、frontend tests、mapping eval、split eval、overfit scan、quality gate、DeepSeek eval、review subagent eval、content quality eval、package consistency eval，并提交所有可复现 evidence。

最终请提交分阶段 commit，并在最后输出：
- 当前指标表；
- 是否通过 quality gate；
- 未通过时的真实失败原因；
- evidence 文件列表；
- 下一阶段强化建议。
```

---

## 20. 基本阶段完成后的推荐答辩口径

如果 quality gate 通过：

```text
基本阶段已完整覆盖课题 5 主体要求。字段映射评测中 auto recall、assisted recall、review-required rate 分开统计；dev/test/blind assisted recall 达到 0.85 门槛，required missing 和 badcase violations 均为 0。DeepSeek 以 report-only 方式提供疑难映射建议，Codex review subagent 模拟人工复核并默认 dry-run，不污染生产规则。成果包可通过 JSON/Markdown 双形态、manifest/checksum、Lineage 和下游 RAG/training/CSV contract 复现验证。
```

如果 quality gate 未通过但其他证据完整：

```text
基本阶段已完整覆盖课题 5 主体链路与可复现证据，但字段映射 0.85 总门禁仍为 partial。当前已清零 required missing，badcase violations 为 0，package verification 为 100%，DeepSeek suggestion 与 Codex review subagent 已形成可复现报告。剩余差距集中在 general_doc / meeting_doc 的 source-name exact recall 和 evidence alignment，已在 gap analysis 中列明，将进入强化阶段继续冲刺。
```

