# 课题 5 强化阶段执行文档

> 适用项目：`Yiliiiiiiii/NEU-Practical-training-Task-5`  
> 建议起点分支：`codex/basic-topic5-complete-evidence`  
> 建议新建分支：`codex/strengthen-topic5-final-gate`  
> 阶段目标：在基本阶段主体覆盖的基础上，完成强化验收闭环，使项目尽量达到课题 5 指标要求，并形成可以答辩、复现、解释、审计的最终证据包。

---

## 0. 当前基线与问题判断

基本阶段已经完成主体覆盖和证据补齐：

- UIR / External UIR 到标准成果包的主链路已完成；
- Package、checksum、RAG/training/CSV 下游解析均为 1.000；
- Required missing = 0；
- Badcase violations = 0；
- Overfit scan = pass；
- DeepSeek report-only 证据已存在；
- Codex review subagent dry-run 证据已存在；
- 一键复现脚本 `scripts/run_basic_stage_verification.ps1` 已存在。

但基本阶段仍存在以下未通过项：

| 问题 | 当前表现 | 强化阶段处理方向 |
| --- | --- | --- |
| 字段映射 0.85 门禁未通过 | overall assisted recall 约 0.807，dev/test 低于 0.85 | 继续优化 general_doc / meeting_doc / policy_doc 长尾字段，目标 dev/test/blind 均 ≥0.85 |
| DeepSeek 证据偏弱 | 目前主要是 report-only packaging，不是真实模型贡献评测 | 增加真实 DeepSeek 调用或明确 live-disabled；输出 top1/top3 命中、unsafe、cost、latency |
| Codex review subagent 偏弱 | 当前是规则 dry-run，不是实际“人的视角”判断 | 让 Codex 子智能体阅读 evidence，输出 approve/reject/uncertain 与理由；默认不写生产规则 |
| 内容标签质量未完全达标 | content tag 尚可，management/quality tag F1 偏低 | 优化标签生成或评测规则，目标各类标签准确率或 F1 ≥0.85 |
| 摘要忠实度未完全达标 | summary pass rate 约 0.90 | 修复 missing / forbidden 失败样例，目标 ≥0.95，幻觉数 0 |
| 文档口径仍有残留 | 不同文档中 blind、review-required、assisted recall 数值不完全一致 | 最终统一 README / acceptance_report / requirement_mapping / project_status / demo_script |

强化阶段的核心原则：**不为了达标而牺牲可信度。宁可诚实 partial，也不要写 doc_id 特例、读取 gold、扩大 review-required 虚高 recall。**

---

## 1. 阶段总目标

强化阶段完成后，应能对外陈述：

> 项目完整覆盖课题 5 主体要求，具备 UIR / External UIR 输入、Schema 驱动字段映射、字段转换、校验、分段、摘要、关键词、标签、双形态成果包、manifest/checksum、下游消费、Lineage、Review/Knowledge、DeepSeek report-only / review-assisted 能力和一键复现证据。字段映射在当前课程规模数据集上尽量达到 0.85 门禁；若仍未完全达到，则明确列出未达标项与强化计划，不夸大生产级盲测能力。

### 1.1 强化阶段硬性退出标准

P0 退出标准如下：

| 指标 | 目标 |
| --- | ---: |
| backend pytest | pass，记录最新数量 |
| Ruff | clean |
| frontend build | pass |
| frontend tests | pass |
| OpenAPI export/check | pass，记录 paths 数 |
| package verification | 1.000 |
| checksum pass | 1.000 |
| RAG/training/CSV parse | 1.000 |
| required missing | 0 |
| badcase violations | 0 |
| high-risk auto accepted | 0 |
| LLM auto accepted | 0 |
| overfit scan | pass |
| overall assisted mapping recall | ≥0.85，若未达则不得宣称达标 |
| dev/test/blind assisted recall | 均 ≥0.85，若未达则 quality gate 保持 failed |
| review-required rate | ≤0.08，避免靠转人工刷分 |
| content tag quality | content / management / quality 主要指标 ≥0.85，或明确 partial |
| summary faithfulness pass rate | ≥0.95 |
| summary hallucination count | 0 |
| DeepSeek evaluation | 有 live 或明确 live-disabled 的可复现报告 |
| Codex review subagent | 有真实 review 报告，默认 dry-run，不写生产规则 |
| 文档口径 | README、acceptance_report、requirement_mapping、project_status、demo_script 数值一致 |

### 1.2 P1 加分退出标准

| 指标 | 目标 |
| --- | ---: |
| 新增 mini shadow set | ≥15 个未参与规则开发的 UIR/gold |
| shadow assisted recall | ≥0.80，优先 ≥0.85 |
| LLM suggestion top1 hit rate | 记录，不强制 |
| LLM suggestion top3 hit rate | 记录，不强制 |
| Codex review agreement_with_gold | 记录，不强制 |
| field operation eval | rename / merge / split / validate 操作准确率 ≥0.95 |
| schema error localization | 100% 定位错误字段 / 路径 |
| dual-format consistency | JSON / Markdown 互链与内容一致率 1.000 |

---

## 2. 分支与执行方式

### 2.1 新建分支

```powershell
# 从 basic 分支继续
 git checkout codex/basic-topic5-complete-evidence
 git pull
 git checkout -b codex/strengthen-topic5-final-gate
```

如果 basic 分支已经合并到 main，则从 main 新建：

```powershell
 git checkout main
 git pull
 git checkout -b codex/strengthen-topic5-final-gate
```

### 2.2 证据目录

强化阶段所有新证据放入：

```text
docs/交接/evidence/strengthen_stage/
  mapping/
  llm/
  review/
  content/
  package/
  operation/
  shadow/
  final/
```

不得只写到 `reports/` 后又被 `.gitignore` 忽略。`reports/` 可以继续作为运行时输出，但最终可提交证据必须复制或直接输出到 `docs/交接/evidence/strengthen_stage/`。

---

## 3. P0 任务一：先修文档口径与最终门禁命名

### 3.1 问题

基本阶段仍有部分文档数值残留，例如同一文档中可能同时出现：

- overall assisted recall 0.807 与 0.8096514745；
- review-required 24 与 18；
- blind assisted recall 0.826 与 0.855；
- final gate 文件名像是综合门禁，但内容只是 mapping gate failed。

### 3.2 修改要求

统一当前 basic baseline，作为强化起点：

```text
Dataset size: 50
Auto mapping recall: 0.777
Assisted mapping recall: 0.807
Review-required rate: 0.057
Review-required count: 24
Required missing: 0
Badcase violations: 0
Strict pass: 48/50
Package verification: 50/50
Split assisted recall: dev 0.798, test 0.794, blind 以最新 summary 为准
Quality gate: failed
```

需要修改：

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/mapping_recall_085_guarded_sprint.md
docs/交接/final_demo_script.md
```

### 3.3 文件命名调整

将：

```text
docs/交接/evidence/basic_stage/final/basic_stage_final_gate_result.md
```

解释或改名为：

```text
basic_stage_mapping_gate_result.md
```

强化阶段新增真正综合门禁：

```text
docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md
```

内容应综合判断：

```text
mapping_gate: pass/failed
package_gate: pass/failed
overfit_gate: pass/failed
llm_gate: pass/partial/failed
review_subagent_gate: pass/partial/failed
content_quality_gate: pass/partial/failed
doc_consistency_gate: pass/failed
final_conclusion: pass / conditional_pass / failed
```

---

## 4. P0 任务二：字段映射 0.85 冲刺

### 4.1 当前短板

按基本阶段报告，文档类型短板为：

```text
general_doc assisted recall ≈ 0.759，是最大短板
meeting_doc assisted recall ≈ 0.809，仍有提升空间
policy_doc assisted recall ≈ 0.842，接近 0.85，低风险小修即可
```

字段映射冲刺优先级：

1. general_doc：service_object、application_conditions、application_materials、process_steps、contact、source/title exact alignment。
2. meeting_doc：meeting_date、meeting_number、topics、decisions、action_items、chairperson/source-name alignment。
3. policy_doc：policy_005 irregular heading、issuer/source evidence、policy_measures、target_audience；不要再扩大弱 source_site 自动接受。

### 4.2 绝对禁止

不得出现以下情况：

```python
if doc_id == "real_general_011_shanghai_branch_registration": ...
if "上海市分公司设立登记" in text: ...
if "汨罗市第13届人民政府第47次" in text: ...
source_path == "$.blocks.real_xxx_b001" ...
读取 mapping_gold.jsonl 参与 runtime mapping
```

只能写通用规则：

```text
“申报对象 / 适用对象 / 服务对象 / 申报主体” -> service_object candidate
“申请条件 / 受理条件 / 申报条件 / 办理条件” -> application_conditions candidate
“申请材料 / 办理材料 / 申报材料 / 材料清单” -> application_materials candidate
“办理流程 / 申报流程 / 流程步骤 / 办理程序” -> process_steps candidate
“联系电话 / 咨询电话 / 联系方式 / 服务电话” -> contact candidate
“第X届...第Y次会议 / 第X次常务会议 / 会议纪要” -> meeting_number candidate
“会议研究 / 会议审议 / 会议听取 / 议定事项 / 决定事项” -> topics / decisions / action_items candidate with guards
```

### 4.3 general_doc 具体实现要求

修改重点位置：

```text
backend/app/services/candidate_service.py
examples/production_like/mapping_templates/general_doc_base_v1.json
backend/tests/test_general_doc_mapping_rules.py
backend/tests/test_candidate_service_non_procurement.py
```

#### 4.3.1 service_object

新增或增强通用候选抽取：

正向 label：

```text
服务对象
适用对象
申请对象
办理对象
面向对象
申报主体
申报单位
申报人
可申请主体
支持对象
受理对象
项目负责人要求
企业条件
```

正文句式：

```text
面向……提供
适用于……
由……申请
申报主体为……
申请人应为……
符合条件的……可申请
```

自动 accepted 条件：

- source_name 明确为上述 label；
- value 长度合理；
- 不包含“联系电话 / 申报材料 / 办理流程 / 截止时间”等其他字段强标记。

review-required 条件：

- 句式命中但上下文宽泛；
- source_name 来自 heading 或 aggregate text；
- value 同时包含多个字段。

#### 4.3.2 application_conditions

正向 label：

```text
申请条件
受理条件
办理条件
申报条件
申报要求
资格条件
准入条件
企业条件
项目条件
基本条件
```

应从 heading + 后续段落抽取完整 section，而不是只抽 heading 本身。

边界规则：遇到以下 heading 停止：

```text
申报材料
申请材料
办理流程
联系方式
截止时间
办理时限
```

#### 4.3.3 application_materials

正向 label：

```text
申请材料
申报材料
办理材料
提交材料
材料清单
所需材料
附件材料
```

支持 list block、numbered paragraph、heading + body。

负样本：

- 不得把“附件 1 / 附件下载 / 目录”单独映射为 materials；
- 不得把 contact 或 deadline 段落误入 materials。

#### 4.3.4 process_steps

正向 label：

```text
办理流程
申报流程
申请流程
办理程序
办理步骤
流程步骤
操作流程
申报方式
办理方式
```

正文句式：

```text
登录……系统
提交……材料
经……审核
公示……
完成……办理
```

自动 accepted 条件：显式 label 或清晰 step list。否则 review。

#### 4.3.5 contact

正向 label：

```text
联系电话
咨询电话
联系方式
服务电话
办理窗口电话
联系人及电话
```

支持电话正则：

```text
手机号
区号-座机
多个电话
转分机
```

负样本：不得将邮编、地址、统一社会信用代码、政策编号误判为电话。

### 4.4 meeting_doc 具体实现要求

修改重点位置：

```text
backend/app/services/candidate_service.py
examples/production_like/mapping_templates/meeting_doc_base_v1.json
backend/tests/test_meeting_doc_mapping_rules.py
```

#### 4.4.1 meeting_number

通用模式：

```text
第X届人民政府第Y次常务会议
第X次会议
第X次党组会议
第X次主任办公会议
第X号会议纪要
```

禁止真实地名硬编码，例如不能出现具体“汨罗市第13届……”文本。

#### 4.4.2 meeting_date

正向 label：

```text
会议日期
会议时间
召开日期
召开时间
时间
```

正文句式：

```text
X年X月X日，……主持召开……会议
会议于X年X月X日召开
```

负样本：

```text
发布日期
发布时间
网页抓取时间
成文日期
印发日期
retrieved_at
```

#### 4.4.3 topics / decisions / action_items

topics 正向 evidence：

```text
会议研究
会议审议
会议听取
会议传达学习
会议讨论
议题
审议事项
研究事项
```

决策类 evidence：

```text
会议原则同意
会议决定
会议要求
会议强调
会议指出
议定事项
```

action_items evidence：

```text
由……负责
牵头单位……
责任单位……
按期完成
抓好落实
推进……工作
```

负样本：

- 不得把参会人员列表当 topics；
- 不得把主持人当 topics；
- 不得把会议标题本身当 decisions；
- 不得把来源网站当 meeting_number。

### 4.5 policy_doc 低风险小修

不要大幅扩大 policy_doc 的自动接受范围。重点修：

```text
policy_005 irregular heading/source evidence
policy_measures section boundary
target_audience source-name alignment
issuer / publish_date 的 source-name exact recall
```

保持：

```text
source_site / 发布机构 / 来源网站 -> issuer 只能 review 或禁止自动 accepted
retrieved_at -> publish_date / effective_date 禁止
成文日期 -> publish_date 默认禁止自动 accepted，除非明确规则说明
附件1 -> issuer 禁止
```

### 4.6 映射冲刺门禁

每次改完运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md `
  --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir docs\交接\evidence\strengthen_stage\mapping\splits

backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report docs\交接\evidence\strengthen_stage\mapping\splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05
```

目标：

```text
overall assisted >= 0.85
dev assisted >= 0.85
test assisted >= 0.85
blind assisted >= 0.85
required_missing = 0
badcase_violations = 0
review_required_rate <= 0.08
package_pass_rate = 1.0
```

---

## 5. P0 任务三：DeepSeek 真实能力验证

### 5.1 当前问题

基本阶段的 `eval_deepseek_mapping_suggestions.py` 只是从 mapping report 的 review_evidence 中打包 20 条 suggestion，并没有真正调用 DeepSeek，也没有 top1/top3 hit rate。强化阶段必须补强。

### 5.2 目标

新增真实 DeepSeek report-only 评测：

```text
deterministic_only baseline
DeepSeek suggestion top1 / top3 hit rate
unsafe suggestion count
secret leak count
LLM auto accepted count = 0
activate_rule_count = 0
write_template_count = 0
cost / latency / request count
```

如果环境没有 `DEEPSEEK_API_KEY`，脚本必须明确输出：

```text
provider_configured = false
evaluation_scope = offline_packaging_only
can_claim_live_model_capability = false
```

不能在没有真实调用时写“DeepSeek 能力已验证”。

### 5.3 输入样本

从 `reports/non_procurement_mapping_eval_report.json` 中选取：

- review_required items；
- missing 或 low-confidence candidates；
- known badcase 附近候选；
- general_doc / meeting_doc / policy_doc 各不少于 5 条。

建议输出 case 文件：

```text
docs/交接/evidence/strengthen_stage/llm/deepseek_eval_cases.jsonl
```

每条 case 包含：

```json
{
  "case_id": "...",
  "doc_id": "...",
  "doc_type": "general_doc",
  "target_field": "service_object",
  "candidate_sources": [ ... ],
  "source_evidence": [ ... ],
  "gold_expected_target": "只在 evaluator 使用，不放入 prompt",
  "known_badcases": [ ... ]
}
```

注意：gold 不得进入 prompt，只能在评测阶段使用。

### 5.4 Prompt 要求

DeepSeek prompt 必须要求输出 JSON：

```json
{
  "target_field": "...",
  "suggested_source_path": "...",
  "suggested_source_name": "...",
  "confidence": 0.0,
  "rationale": "...",
  "risk_flags": [],
  "decision": "suggest_accept|suggest_review|suggest_reject"
}
```

模型不得输出生产规则，不得修改 schema/template，不得创建 task。

### 5.5 安全策略

- DeepSeek 输出永远不直接进入 accepted mappings；
- 所有 suggest_accept 也只能进入 review report；
- 若命中 badcase，计入 unsafe_suggestion_count；
- 输出中若包含 API key、token、secret pattern，计入 secret_leak_count；
- prompt、response、latency、cost 进入 trace；
- 支持 `--dry-run` 和 `--max-cases`。

### 5.6 输出文件

```text
docs/交接/evidence/strengthen_stage/llm/deepseek_mapping_live_eval_report.json
docs/交接/evidence/strengthen_stage/llm/deepseek_mapping_live_eval_report.md
```

Markdown 至少包含：

```text
provider_configured
live_request_count
case_count
top1_hit_rate
top3_hit_rate
unsafe_suggestion_count
secret_leak_count
llm_auto_accepted_count
avg_latency_ms
estimated_cost
honesty_note
```

---

## 6. P0 任务四：Codex 子智能体真实 review

### 6.1 当前问题

基本阶段 `eval_codex_review_subagent.py` 是规则 dry-run，不是真正子智能体以人的视角判断。强化阶段需要让 Codex 子智能体实际阅读 mapping evidence，然后输出结构化 review 决策。

### 6.2 目标

新增 review cases：

```text
docs/交接/evidence/strengthen_stage/review/review_cases.jsonl
```

每条 case 包含：

```json
{
  "case_id": "...",
  "doc_id": "...",
  "doc_type": "...",
  "target_field": "...",
  "candidate": {
    "source_name": "...",
    "source_path": "...",
    "value_sample": "...",
    "confidence": 0.0,
    "risk_flags": []
  },
  "source_context": ["..."],
  "badcase_hints": ["不能将 retrieved_at 映射为 publish_date"],
  "review_question": "该候选是否适合映射到 target_field？"
}
```

Codex 子智能体输出：

```json
{
  "case_id": "...",
  "decision": "approve|reject|uncertain",
  "confidence": 0.0,
  "reason": "...",
  "required_human_check": true,
  "unsafe_approve": false
}
```

### 6.3 评测指标

```text
reviewed_items
approve_count
reject_count
uncertain_count
agreement_with_gold
unsafe_approve_count
applied_count
production_write_count
```

强化阶段仍然默认：

```text
applied_count = 0
production_write_count = 0
```

如果要 safe apply，必须单独出报告，不得混入默认 dry-run。

### 6.4 输出文件

```text
docs/交接/evidence/strengthen_stage/review/codex_review_subagent_live_report.json
docs/交接/evidence/strengthen_stage/review/codex_review_subagent_live_report.md
```

### 6.5 通过标准

| 指标 | 目标 |
| --- | ---: |
| reviewed_items | ≥20 |
| unsafe_approve_count | 0 |
| applied_count | 0 |
| production_write_count | 0 |
| decision reason coverage | 1.000 |
| agreement_with_gold | 记录，建议 ≥0.80 |

---

## 7. P0 任务五：内容标签与摘要忠实度提升

### 7.1 当前问题

基本阶段内容质量评测：

```text
content tag F1 ≈ 0.9000
management tag F1 ≈ 0.5474
quality tag F1 ≈ 0.5607
summary faithfulness pass rate ≈ 0.9000
```

management / quality 标签明显不足，摘要忠实度仍有失败样例。

### 7.2 标签质量修复方向

检查内容组织代码与标签生成逻辑，重点解决：

1. 过度打 management / quality 标签；
2. 标签含义不稳定；
3. heading_aware 策略下管理类标签和质量类标签边界不清；
4. 评价脚本是否把 recall=1.0、precision 偏低的情况正确视为质量问题。

标签建议分层：

```text
content tags：主题内容，如 policy, meeting, application, contact, deadline, material
management tags：结构/流程，如 heading, section, list, table, appendix, metadata
quality tags：质量状态，如 low_confidence, needs_review, incomplete, source_linked, protected_structure
```

自动打 management tag 时必须有结构证据：

```text
heading -> heading
list block -> list
table block -> table
appendix heading -> appendix
metadata source -> metadata
```

不要把所有 chunk 都打多个 management tag。

### 7.3 摘要忠实度修复方向

修复已知失败：

- must-include 信息缺失；
- 摘要未覆盖关键申报对象 / 支付方式；
- 会议纪要摘要缺少核心议题或结论。

摘要规则：

```text
摘要只能来自 source blocks；
不能新增原文没有的日期、金额、机构；
对 general_doc，必须优先覆盖 service_object、deadline、materials、process；
对 meeting_doc，必须优先覆盖 date、number、topics、decisions/action_items；
对 policy_doc，必须优先覆盖 issuer、publish_date、target_audience、measures。
```

### 7.4 输出文件

```text
docs/交接/evidence/strengthen_stage/content/content_tag_quality_detail.json
docs/交接/evidence/strengthen_stage/content/content_tag_quality_detail.md
docs/交接/evidence/strengthen_stage/content/summary_faithfulness_detail.json
docs/交接/evidence/strengthen_stage/content/summary_faithfulness_detail.md
docs/交接/evidence/strengthen_stage/content/content_tag_summary_quality_report.json
docs/交接/evidence/strengthen_stage/content/content_tag_summary_quality_report.md
```

### 7.5 通过标准

| 指标 | 目标 |
| --- | ---: |
| content tag F1 | ≥0.85 |
| management tag F1 | ≥0.85 |
| quality tag F1 | ≥0.85 |
| unknown tag count | 0 |
| tag coverage | ≥0.95 |
| summary faithfulness pass rate | ≥0.95 |
| new date violations | 0 |
| new amount violations | 0 |
| new organization violations | 0 |
| summary hallucination count | 0 |

如果确实无法在一周内让 management / quality F1 ≥0.85，则 final gate 必须标记 content_quality_gate = partial，不得标 passed。

---

## 8. P0 任务六：Package、字段操作与 Schema 校验补证据

### 8.1 Package 一致性

基本阶段 package consistency 已经很好，强化阶段继续保持：

```text
Package verify pass rate = 1.000
Checksum pass rate = 1.000
RAG parse pass = 1.000
training parse pass = 1.000
CSV parse pass = 1.000
```

输出到：

```text
docs/交接/evidence/strengthen_stage/package/package_consistency_report.md
```

### 8.2 字段操作准确率

课题 5 还涉及字段重命名、合并、拆分、校验。新增评测：

```text
scripts/eval_field_operations_quality.py
```

测试操作：

```text
rename: source field -> canonical target field
merge: multiple source fields -> one target field
split: one source field -> multiple target fields
validate: type/format/required/enum/range check
```

输出：

```text
docs/交接/evidence/strengthen_stage/operation/field_operation_quality_report.json
docs/交接/evidence/strengthen_stage/operation/field_operation_quality_report.md
```

目标：

```text
field_operation_accuracy >= 0.95
unsafe_operation_count = 0
```

### 8.3 Schema 校验错误定位

新增或增强：

```text
scripts/eval_schema_validation_localization.py
```

构造 bad samples：

```text
missing required field
wrong date format
wrong enum
wrong type
bad nested path
invalid package artifact
```

输出：

```text
docs/交接/evidence/strengthen_stage/operation/schema_validation_localization_report.json
docs/交接/evidence/strengthen_stage/operation/schema_validation_localization_report.md
```

目标：

```text
localization_rate = 1.000
```

---

## 9. P1 加分：mini shadow set

如果时间允许，补一个小型独立 shadow set，增强“严格生产级”可信度。

### 9.1 数据要求

新增：

```text
examples/real_world_shadow/uir/*.json
examples/real_world_shadow/gold/mapping_gold_shadow.jsonl
examples/real_world_shadow/manifest.json
```

建议数量：

```text
general_doc: 6
meeting_doc: 5
policy_doc: 6
合计 17 个左右
```

要求：

- 不使用当前 dev/test/blind 的 doc_id；
- 不从已有样例复制标题；
- gold 人工标注；
- 不针对 shadow 写规则；
- 只在最后运行评测。

### 9.2 输出报告

```text
docs/交接/evidence/strengthen_stage/shadow/shadow_mapping_eval_report.json
docs/交接/evidence/strengthen_stage/shadow/shadow_mapping_eval_report.md
```

通过口径：

```text
shadow assisted recall >= 0.80: 可说具备初步泛化证据
shadow assisted recall >= 0.85: 可说课程规模 shadow set 达标
```

不能说“生产级盲测达标”，除非 shadow 数据独立、数量足够、gold 冻结且未参与开发。

---

## 10. 一键强化验证脚本

新增：

```text
scripts/run_strengthen_stage_verification.ps1
```

流程：

```powershell
$ErrorActionPreference = "Stop"
$EvidenceRoot = "docs\交接\evidence\strengthen_stage"

# 1. verify_all
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

# 2. frontend tests
Push-Location frontend
npm.cmd test
Pop-Location

# 3. mapping eval
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md `
  --timeout 60

# 4. split eval
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir "$EvidenceRoot\mapping\splits"

# 5. gap + overfit
backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-json "$EvidenceRoot\mapping\mapping_gap_analysis.json" `
  --out-md "$EvidenceRoot\mapping\mapping_gap_analysis.md"

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-json "$EvidenceRoot\mapping\mapping_overfit_risk_report.json" `
  --out-md "$EvidenceRoot\mapping\mapping_overfit_risk_report.md"

# 6. mapping gate，失败也记录，但 final gate 要读取结果
try {
  backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
    --report "$EvidenceRoot\mapping\splits\summary.json" `
    --min-assisted-recall 0.85 `
    --max-badcase-violations 0 `
    --max-required-missing 0 `
    --max-dev-test-gap 0.05 `
    --max-test-blind-gap 0.05 `
    *> "$EvidenceRoot\mapping\mapping_quality_gate_result.md"
} catch {
  Write-Host "Mapping gate failed; recorded."
}

# 7. DeepSeek live / report-only eval
backend\.venv\Scripts\python.exe scripts\eval_deepseek_mapping_suggestions.py `
  --mode report-only `
  --out-json "$EvidenceRoot\llm\deepseek_mapping_live_eval_report.json" `
  --out-md "$EvidenceRoot\llm\deepseek_mapping_live_eval_report.md"

# 8. Codex review subagent
backend\.venv\Scripts\python.exe scripts\eval_codex_review_subagent.py `
  --mode dry-run `
  --out-json "$EvidenceRoot\review\codex_review_subagent_live_report.json" `
  --out-md "$EvidenceRoot\review\codex_review_subagent_live_report.md"

# 9. content quality
backend\.venv\Scripts\python.exe scripts\eval_content_tag_summary_quality.py `
  --out-json "$EvidenceRoot\content\content_tag_summary_quality_report.json" `
  --out-md "$EvidenceRoot\content\content_tag_summary_quality_report.md"

# 10. package consistency
backend\.venv\Scripts\python.exe scripts\eval_basic_stage_package_consistency.py `
  --out-json "$EvidenceRoot\package\package_consistency_report.json" `
  --out-md "$EvidenceRoot\package\package_consistency_report.md"

# 11. field operation + schema localization
backend\.venv\Scripts\python.exe scripts\eval_field_operations_quality.py `
  --out-json "$EvidenceRoot\operation\field_operation_quality_report.json" `
  --out-md "$EvidenceRoot\operation\field_operation_quality_report.md"

backend\.venv\Scripts\python.exe scripts\eval_schema_validation_localization.py `
  --out-json "$EvidenceRoot\operation\schema_validation_localization_report.json" `
  --out-md "$EvidenceRoot\operation\schema_validation_localization_report.md"

# 12. final gate
backend\.venv\Scripts\python.exe scripts\build_strengthen_stage_final_gate.py `
  --evidence-root "$EvidenceRoot" `
  --out "$EvidenceRoot\final\strengthen_stage_final_gate_result.md"
```

---

## 11. 最终综合门禁脚本

新增：

```text
scripts/build_strengthen_stage_final_gate.py
```

读取：

```text
mapping/splits/summary.json
mapping/mapping_quality_gate_result.md
mapping/mapping_overfit_risk_report.json
llm/deepseek_mapping_live_eval_report.json
review/codex_review_subagent_live_report.json
content/content_tag_summary_quality_report.json
package/package_consistency_report.json
operation/field_operation_quality_report.json
operation/schema_validation_localization_report.json
```

输出：

```text
docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md
```

### 11.1 final conclusion 规则

```text
pass:
  mapping gate pass
  package gate pass
  overfit gate pass
  content quality gate pass
  LLM gate pass or honest report-only pass
  review subagent gate pass
  operation/schema gates pass

conditional_pass:
  主链路、package、安全、复现通过
  mapping gate 或 content quality 有 partial
  文档中诚实说明未达项

failed:
  badcase > 0
  required_missing > 0
  package pass < 1.0
  overfit scan fail
  文档夸大达标
```

---

## 12. 文档最终更新要求

强化阶段完成后，统一更新：

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
docs/交接/mapping_recall_085_guarded_sprint.md
```

### 12.1 必须统一的数值

```text
backend pytest 数量
frontend tests 数量
OpenAPI paths
Dataset size
Auto mapping recall
Assisted mapping recall
Review-required count/rate
dev/test/blind recall
Required missing
Badcase violations
Strict pass
Package verification
Content tag metrics
Summary faithfulness metrics
DeepSeek eval mode / request_count / auto_accepted
Codex review reviewed_items / applied_count
Final gate conclusion
```

### 12.2 禁止表述

除非最终真的通过，否则不得写：

```text
字段映射准确率已达到 0.85
生产盲测 recall 已达 0.85
DeepSeek 已自动提升生产映射准确率
Codex 子智能体已代替人工审批并写入生产规则
标签准确率全面达标
```

### 12.3 推荐表述

如果强化阶段完全达标：

```text
当前 50-sample 课程规模 non-procurement split 中，dev/test/blind assisted mapping recall 均达到 0.85 以上，required missing 和 badcase violations 均为 0，package verification 与下游解析为 100%。DeepSeek 与 Codex review subagent 均以 report-only/dry-run 形式参与疑难映射建议和复核，不自动写入生产规则。
```

如果仍未完全达标：

```text
项目已完整覆盖课题 5 主体链路并形成可复现证据，Package/downstream/Lineage/safety 已通过；字段映射质量继续提升但 0.85 quality gate 尚未完全通过，当前结果按报告诚实标记为 conditional pass。
```

---

## 13. 建议时间安排

### Day 1：收口基本阶段 + 映射差距定位

- 新建强化分支；
- 统一 basic 阶段文档数值；
- 修 final gate 命名；
- 重新跑 mapping eval / split / gap；
- 确定 general_doc 与 meeting_doc 具体失败字段。

### Day 2-3：字段映射冲刺

- 优先 general_doc；
- 再 meeting_doc；
- policy_doc 只小修；
- 每次改动都跑 mapping split gate、badcase、overfit scan；
- 不写 doc_id / 标题 / 真实文本片段特例。

### Day 4：DeepSeek 与 Codex review

- 实现或增强 DeepSeek live/report-only eval；
- 生成 DeepSeek suggestion report；
- 生成 Codex review cases；
- 让 Codex 子智能体输出 review decisions；
- 保持 applied_count = 0。

### Day 5：内容标签 / 摘要 / 字段操作 / Schema 定位

- 修 management / quality tag；
- 修 summary faithfulness 失败样例；
- 增加 field operation eval；
- 增加 schema validation localization eval。

### Day 6：完整复现与 final gate

- 运行 `run_strengthen_stage_verification.ps1`；
- 生成 final gate；
- 修失败项；
- 再跑一次。

### Day 7：文档与答辩材料收口

- 更新 README / acceptance_report / requirement_mapping / project_status / final_demo_script；
- 准备最终演示口径；
- 保留 honest limitation；
- 若未过 0.85，明确 conditional pass，不夸大。

---

## 14. 交给 Codex 的完整执行提示词

```text
你现在接手 NEU-Practical-training-Task-5 项目的强化阶段开发。请从 codex/basic-topic5-complete-evidence 分支或已合并后的 main 新建 codex/strengthen-topic5-final-gate 分支。

阶段目标：在基本阶段已覆盖课题 5 主体链路的基础上，补齐强化验收闭环。重点不是继续堆文档，而是让字段映射、DeepSeek 大模型能力、Codex review subagent、内容标签/摘要质量、字段操作、Schema 校验、Package 一致性和最终证据包形成可复现闭环。

P0 必做：
1. 统一 basic 阶段所有文档口径，修正 README、acceptance_report、requirement_mapping、project_status、mapping_recall_085_guarded_sprint 中残留的不一致数值。当前 basic 起点口径为：dataset_size=50，auto_mapping_recall≈0.777，assisted_mapping_recall≈0.807，review_required_rate≈0.057，review_required_count=24，required_missing=0，badcase=0，strict_pass=48/50，package=50/50，quality gate failed。
2. 将 basic_stage_final_gate_result.md 改为 mapping gate 或新增真正综合 final gate，避免文件名误导。
3. 继续提升字段映射质量，目标 overall/dev/test/blind assisted recall 均 >=0.85，同时保持 required_missing=0，badcase=0，review_required_rate<=0.08，package=1.0。
4. 优先优化 general_doc 的 service_object、application_conditions、application_materials、process_steps、contact；其次优化 meeting_doc 的 meeting_date、meeting_number、topics、decisions、action_items；policy_doc 只做低风险 evidence alignment。
5. 严禁 doc_id 特例、真实标题特例、具体地名/会议编号特例、source_path 特例、gold label 泄漏。
6. 强化 check_mapping_overfit_risk.py，使其继续扫描 doc_id、gold leakage、sample text snippet、source_path-specific、real title snippet 等风险。
7. 增强 DeepSeek mapping suggestion evaluation。如果 DEEPSEEK_API_KEY 存在，应进行真实 report-only 调用，并输出 top1/top3 hit rate、unsafe_suggestion_count、secret_leak_count、latency、request_count、cost；如果没有 key，必须明确 can_claim_live_model_capability=false，不能宣称真实模型能力。
8. 增强 Codex review subagent evaluation。生成 review_cases.jsonl，让 Codex 子智能体以人的视角阅读 evidence 并输出 approve/reject/uncertain、reason、confidence、unsafe_approve。默认 dry-run，applied_count=0，production_write_count=0。
9. 提升 content tag / summary faithfulness。目标 content、management、quality 标签主要指标 >=0.85；summary faithfulness pass rate >=0.95；new date/amount/organization violations=0；hallucination_count=0。如果未达，final gate 标 partial。
10. 增加 field operation eval 和 schema validation localization eval。目标字段操作准确率 >=0.95，schema 错误定位率 1.0。
11. 新增 scripts/run_strengthen_stage_verification.ps1，一键生成 docs/交接/evidence/strengthen_stage/ 下所有证据。
12. 新增 scripts/build_strengthen_stage_final_gate.py，输出综合 final gate：mapping、package、overfit、llm、review、content、operation、schema、doc consistency 的 pass/partial/failed 状态与最终结论。
13. 最后更新 README、acceptance_report、requirement_mapping、project_status、final_demo_script，所有数值必须一致，未达项必须诚实标 partial 或 failed。

P1 加分：
1. 新增 mini shadow set，至少 15 个独立 UIR/gold，最后一次运行，不参与规则开发。
2. 输出 shadow_mapping_eval_report，记录 shadow assisted recall。
3. 如果 shadow 未达 0.85，不得宣称生产级盲测达标。

最终验收口径：
- 如果 mapping/content/llm/review/package/overfit/operation/schema 全部通过，final conclusion = pass。
- 如果主链路、package、安全、复现通过，但 mapping 0.85 或 content quality 仍未完全达标，final conclusion = conditional_pass。
- 如果 badcase>0、required_missing>0、package<1.0、overfit fail 或文档夸大指标，final conclusion = failed。
```

---

## 15. 强化阶段最终提交清单

最终 PR 或分支必须包含：

```text
scripts/run_strengthen_stage_verification.ps1
scripts/build_strengthen_stage_final_gate.py
scripts/eval_deepseek_mapping_suggestions.py         # 增强真实/诚实 LLM eval
scripts/eval_codex_review_subagent.py                # 增强子智能体 review eval
scripts/eval_content_tag_summary_quality.py          # 增强内容质量 eval
scripts/eval_field_operations_quality.py             # 新增
scripts/eval_schema_validation_localization.py       # 新增
backend/app/services/candidate_service.py            # 字段候选增强
backend/tests/test_*mapping*_rules.py                # 对应测试
backend/tests/test_mapping_overfit_risk_script.py    # 过拟合扫描测试

docs/交接/evidence/strengthen_stage/mapping/*
docs/交接/evidence/strengthen_stage/llm/*
docs/交接/evidence/strengthen_stage/review/*
docs/交接/evidence/strengthen_stage/content/*
docs/交接/evidence/strengthen_stage/package/*
docs/交接/evidence/strengthen_stage/operation/*
docs/交接/evidence/strengthen_stage/final/*

README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
docs/交接/mapping_recall_085_guarded_sprint.md
```

---

## 16. 最终提醒

强化阶段不是只追一个数字，而是让项目经得起老师追问：

1. 为什么说你是智能体，而不是普通脚本？  
   答：DeepSeek suggestion、Codex review subagent、Review/Knowledge、置信度、风险标记和可追溯决策。

2. 为什么说你符合课题 5？  
   答：字段映射、转换、校验、分段、标签、摘要、关键词、双形态成果包、manifest/checksum、下游消费均有可复现证据。

3. 为什么说你没有过拟合？  
   答：dev/test/blind split、overfit scan、禁止 doc_id/gold/source_path/title snippet 特例、badcase=0、review rate 受控。

4. 为什么说你可产品化？  
   答：API/CLI/SDK、Package 1.1、OpenAPI、Docker/local deployment、可关闭 LLM、可替换模型、audit/lineage。

5. 如果 0.85 仍未过怎么办？  
   答：诚实写 conditional pass，说明主链路和证据完整，但字段映射 quality gate 尚未完全通过，剩余是 general/meeting 长尾 source-name exact recall 与内容质量指标。
