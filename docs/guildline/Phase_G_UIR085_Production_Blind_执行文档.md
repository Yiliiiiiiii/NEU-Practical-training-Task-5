# Phase G：UIR 0.85+ 生产泛化能力达标执行文档

> 交付对象：Codex  
> 项目：SchemaPack Agent / 课题 5 数据格式标准化转换智能体  
> 文档目标：把下一步拆成可执行、可验证、可回归的任务，最终证明系统对“通过 UIR Quality Gate 的生产 UIR、已支持 schema family、source evidence 可追溯”的输入，达到字段语义映射能力 `0.85+`。

---

## 0. 当前基线与结论

### 0.1 当前 Phase D 基线

```text
dataset_size = 50
average_recall = 0.742603
strict_pass = 39/50
required_missing = 2
review_required = 21
badcase_violations = 0
llm_auto_accepted = 0
package_verification = 50/50
secret_leaks = 0
```

按文档类型：

```text
general_doc recall = 0.824206
meeting_doc recall = 0.763704
policy_doc recall = 0.665575
```

已达成：

```text
strict_pass >= 38/50
meeting_doc recall >= 0.76
required_missing <= 2
badcase violations = 0
package verification = 50/50
DeepSeek provider smoke passed
Review Judge dry-run/apply-safe 安全验证完成
secret redaction audit passed
```

未达成：

```text
average_recall >= 0.78
policy_doc recall >= 0.75
general_doc recall >= 0.85
review_required <= 18
DeepSeek 对主 mapping evaluator 的 measurable contribution > 0
Review Judge 实际消化 scoped review
production blind-set average_recall >= 0.85
```

### 0.2 0.85 声明边界

不能声称：

```text
任意质量、任意领域、任意结构的 UIR 都能无条件 0.85+
```

应证明：

```text
对通过 UIR Quality Gate、属于已支持 schema family、source evidence 可追溯、目标字段在 schema 内的生产 UIR：
blind-set average_recall >= 0.85
auto_accepted_precision >= 0.95
mapped_or_review_recall >= 0.90
badcase violations = 0
llm_auto_accepted = 0
package verification = 100%
secret leaks = 0
```

---

## 1. 总体里程碑

### Phase G1：评测口径和 Review Scope 修正

目标：Review Judge 只处理当前 eval run / dataset split / doc_type scope 内的 review，不再使用全库历史 pending_total 作为本轮指标。

验收：

```text
reports/phase_g_review_scope_report.json/.md
current_run_pending_count 与 mapping evaluator review_required 可解释一致
历史 pending、采购 pending、不相关 task 不进入本轮统计
```

### Phase G2：Policy Doc 专项硬化

目标：

```text
policy_doc recall: 0.665575 -> >= 0.78
policy_doc strict_pass: 11/20 -> >= 16/20
policy_doc required_missing: 2 -> <= 1
```

优先字段：

```text
issuer
publish_date
effective_date
policy_measures
target_audience
document_number
valid_until
summary
```

### Phase G3：General Doc 补齐到 0.85+

目标：

```text
general_doc recall: 0.824206 -> >= 0.87
general_doc strict_pass: 13/15 -> >= 14/15
```

### Phase G4：DeepSeek Candidate Ablation

目标：DeepSeek 不再只是 smoke test，必须产生 source-backed candidates，并计算对 recall / review_required / required_missing 的真实 delta。

### Phase G5：Review Judge Scoped Apply + Knowledge Draft

目标：Review Judge 针对当前 run 的 review items 做 dry-run 与 apply-guarded，只允许 deterministic safe apply，并把高质量确认项沉淀为 scoped knowledge candidates。

### Phase G6：Production Shadow + Blind Set

目标：建立独立 production_shadow 数据集和 gold labels。warmup 可调参，blind 禁止调参。用 blind set 判断是否可以声明 0.85。

### Phase G7：0.85 终验

目标：

```text
blind-set average_recall >= 0.85
auto_accepted_precision >= 0.95
mapped_or_review_recall >= 0.90
required_missing_rate <= 0.02~0.05
review_required_rate <= 0.10~0.15
badcase violations = 0
llm_auto_accepted = 0
package verification = 100%
secret_leaks = 0
```
---

## 2. 分支、环境与前置检查

### 2.1 新建分支

```powershell
git status --short
git checkout -b codex/phase-g-uir085-production-blind
```

若有用户未提交内容，不得覆盖。

### 2.2 基线验证

启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

运行全量验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

运行当前 50 样本基线：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_g_baseline_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_g_baseline_non_procurement_mapping_eval_report.md
```

### 2.3 DeepSeek Key 安全

如果需要 DeepSeek：

```powershell
$env:DEEPSEEK_API_KEY = "<USER_PROVIDED_KEY>"
```

禁止：

```text
不得写入 git tracked 文件
不得写入 reports/docs/fixtures/logs/audit/task options
不得在终端打印完整 key
不得把 key 放入 task snapshot
```

执行 secret audit：

```powershell
backend\.venv\Scripts\python.exe scripts\audit_secret_redaction.py `
  --out reports\phase_g_secret_redaction_audit_report.json `
  --markdown reports\phase_g_secret_redaction_audit_report.md
```

---

## 3. Phase G1：Review Scope 修正

### 3.1 当前问题

Phase D 中 Review Judge 读取到：

```text
pending_total = 979
```

但当前 50 样本 mapping evaluator 的：

```text
review_required = 21
```

这说明 Review Judge 当前大概率读取了全库历史 pending、采购任务或不相关任务。该统计不能用于本轮质量评价。

### 3.2 修改目标

Review Judge 必须支持以下过滤维度：

```text
run_id
dataset_id
dataset_split
task_batch_id
doc_ids
doc_type
schema_id
created_after
created_before
include_historical = false
```

默认行为：

```text
include_historical = false
scope = latest_eval_run or explicit dataset_id
```

如果无法定位 run_id，脚本必须失败或要求显式 `--doc-ids` / `--dataset-id`，不能默认全库。

### 3.3 需要修改的文件

优先搜索并修改：

```text
scripts/run_review_judge_subagent.py
scripts/codex_review_apply.py
backend/app/services/review_service.py
backend/app/api/routes/reviews.py
backend/app/models/review.py
```

若项目已有 review list API 参数，则复用；若没有，新增只读查询过滤。

### 3.4 CLI 设计

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --dataset-id real_world_non_procurement_50 `
  --doc-type non_procurement `
  --include-historical false `
  --out reports\phase_g_review_judge_scoped_report.json `
  --markdown reports\phase_g_review_judge_scoped_report.md
```

或：

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --doc-ids-file reports\phase_g_current_eval_doc_ids.txt `
  --include-historical false `
  --out reports\phase_g_review_judge_scoped_report.json `
  --markdown reports\phase_g_review_judge_scoped_report.md
```

### 3.5 报告字段

```json
{
  "scope": {
    "dataset_id": "real_world_non_procurement_50",
    "include_historical": false,
    "doc_count": 50,
    "doc_types": ["general_doc", "meeting_doc", "policy_doc"]
  },
  "mapping_evaluator_review_required": 21,
  "review_items_found": 21,
  "out_of_scope_skipped": 958,
  "suggest_approve": 0,
  "suggest_reject": 0,
  "suggest_keep_pending": 21,
  "applied_approve": 0,
  "applied_reject": 0,
  "kept_pending": 21,
  "errors": 0
}
```

若 `review_items_found` 与主 evaluator `review_required` 不一致，必须解释：字段级统计、candidate 级统计、run scope 或 review queue persistence 的差异。

### 3.6 测试

新增：

```text
backend/tests/test_review_scope_filtering.py
```

测试项：

```text
默认不返回历史 review
dataset_id filter 生效
doc_ids filter 生效
doc_type filter 生效
include_historical=true 时才允许读取历史
procurement review 不进入 non_procurement scope
```
---

## 4. Phase G2：Policy Doc 专项硬化

### 4.1 目标

当前 policy_doc：

```text
recall = 0.665575
strict_pass = 11/20
required_missing = 2
```

本阶段目标：

```text
policy_doc recall >= 0.78
policy_doc strict_pass >= 16/20
policy_doc required_missing <= 1
```

最终冲 0.85 时目标：

```text
policy_doc recall >= 0.85 on blind set
```

### 4.2 文件结构

如果尚未建立字段级 extractor registry，新增：

```text
backend/app/services/field_extractors/
  __init__.py
  base.py
  policy_extractors.py
  meeting_extractors.py
  general_extractors.py
```

基础接口：

```python
class FieldExtractor(Protocol):
    doc_type: str
    target_fields: set[str]

    def extract(self, uir: UIRDocument, context: ExtractionContext) -> list[FieldCandidate]:
        ...
```

CandidateService 调用顺序：

```text
1. metadata candidates
2. block/section candidates
3. table candidates
4. doc_type-specific field extractors
5. DeepSeek assisted candidates, report-only/review_required
6. deduplicate
7. risk annotation
8. evidence ranking
```

### 4.3 policy_doc.publish_date

可自动接受 evidence：

```text
source_metadata.published_at
source_metadata.publish_date
页面明确“发布时间”
页面明确“发布日期”
正文头部“发布日期”
manifest 明确 publication_date
```

高风险或禁止 evidence：

```text
成文日期
签发日期
施行日期
有效期至
检索时间 retrieved_at
生成日期
附件日期
法规通过日期
```

规则：

```text
若 source label 是 “发布时间/发布日期” 且 section 位于页面 metadata 或正文头部，可生成低风险 candidate。
若 “成文日期/施行日期/有效期” 同时出现，不得直接 auto accepted，需 date_role_classifier 判断。
若只有 retrieved_at，不生成 publish_date candidate。
```

必须覆盖样例：

```text
real_policy_011_battery_recycling_rules: publish_date required missing
real_policy_007_one_thing_list: 多日期混杂
real_policy_001_training_platform_rules: 成文日期/生成日期/发布时间混杂
real_policy_016_caac_civil_aviation_law: 生效日期与发布日期区分
```

### 4.4 policy_doc.issuer

可接受 evidence：

```text
发文机关
发布机关
印发机关
联合发布机构
文件头部主发文单位
正文末尾落款机构
source_metadata.issuer
```

高风险或禁止 evidence：

```text
承办单位
解读机构
联系人单位
网站主办单位
栏目名称
责任编辑
来源网站
平台名称
```

规则：

```text
issuer exact / alias 仍是 high-risk field。
如果 issuer 来自 “工业和信息化部等部门” 一类联合发文，要保留多机构结构或规范字符串。
如果来源是正文落款，需 block position 接近文末或 section label 为落款/发布机关。
若来源只是网页 header 或站点主办单位，必须 review_required。
```

必须覆盖样例：

```text
real_policy_005_ai_industry_guide: issuer missing
real_policy_006_technology_incubator_rules: issuer regex_missing
real_policy_013_minor_platform_rules: issuer alias_missing
real_policy_016_caac_civil_aviation_law: issuer schema required gap
```

### 4.5 policy_doc.effective_date

可接受 evidence：

```text
自 X 起施行
自 X 起执行
自 X 起生效
施行日期
实施时间
有效期自 X 起
```

禁止 evidence：

```text
发布日期
成文日期
检索时间
生成日期
附件日期
```

规则：

```text
如果句式包含 “自发布之日起施行/生效”，可以生成 effective_date role candidate。
若 publish_date 未确定，则 effective_date 需要依赖 publish_date 或 review。
不能把 publish_date 自动复制为 effective_date，除非文本明确说 “自发布之日起” 且 publish_date source 确认。
```

### 4.6 policy_doc.policy_measures

抽取来源：

```text
支持措施
政策措施
主要措施
重点任务
支持内容及标准
补贴范围和标准
奖励标准
扶持条款
主要内容
修订条款
活动内容
```

规则：

```text
只抽相关 section，不抽全文。
多条措施保留列表结构。
若 section 过长，提取 chunk-level summary 作为候选，但必须 source-backed。
DeepSeek 可辅助拆分措施条款，但不得直接 accepted。
```

### 4.7 policy_doc.target_audience

抽取来源：

```text
适用对象
支持对象
服务对象
面向对象
申报主体
实施对象
受益群体
老年群体
中小企业
在京个人消费者
各有关单位
```

风险：

```text
“各有关单位”可能是通知对象，不一定是政策适用对象。
“各地主管部门”可能是执行部门，不一定是 target_audience。
```

规则：

```text
如果 label 是 “适用对象/支持对象/补贴对象”，低风险。
如果来自通知抬头 “各单位/各部门”，默认 review_required。
```

### 4.8 policy_doc.document_number / valid_until

文号匹配：

```text
国办函〔2025〕3号
新政发〔2026〕1号
公告2026年第10号
工信部联规〔2026〕X号
```

valid_until 匹配：

```text
有效期至 X
执行至 X
实施至 X
截至 X
```

风险：

```text
申报截止日期、材料提交截止日期不是 valid_until。
```

### 4.9 测试

新增：

```text
backend/tests/test_policy_publish_date_extractor.py
backend/tests/test_policy_issuer_extractor.py
backend/tests/test_policy_effective_date_extractor.py
backend/tests/test_policy_measures_extractor.py
backend/tests/test_policy_target_audience_extractor.py
backend/tests/test_policy_date_role_classifier.py
```

运行：

```powershell
backend\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_policy_publish_date_extractor.py `
  backend\tests\test_policy_issuer_extractor.py `
  backend\tests\test_policy_effective_date_extractor.py `
  backend\tests\test_policy_measures_extractor.py `
  backend\tests\test_policy_target_audience_extractor.py `
  backend\tests\test_policy_date_role_classifier.py -q
```
---

## 5. Phase G3：General Doc 补齐到 0.85+

### 5.1 当前状态

```text
general_doc recall = 0.824206
strict_pass = 13/15
review_required = 11
required_missing = 0
```

问题集中在：

```text
real_general_011_shanghai_branch_registration
real_general_013_zhongshan_import_export_guide
contact
service_object
application_conditions
process_steps
summary
```

### 5.2 contact extractor

匹配：

```text
咨询电话
联系电话
咨询方式
办理窗口电话
服务热线
电话：
```

处理：

```text
支持固定电话、手机号、短号、带区号、多个电话。
乱码或 “????” 不自动 accepted。
如果电话出现在投诉/监督电话，而目标是业务咨询 contact，需 review_required。
```

### 5.3 service_object extractor

匹配：

```text
服务对象
适用对象
申请对象
办理对象
面向对象
申请人为
可申请主体
```

风险：

```text
FAQ 错误示例里的“申请人为公司”不得自动替代 service_object。
错误案例、反例、问答纠错段落应降低分。
```

### 5.4 application_conditions ranking

当前部分是 candidate_extracted_but_not_ranked。改 ranking：

加分：

```text
label = 申请条件 / 受理条件 / 办理条件 / 申报条件 / 资格条件
section_path 包含 条件 / 要求
value 是列表或条款
```

扣分：

```text
材料清单
申请表
身份证
一次性告知补齐材料
流程步骤
```

### 5.5 process_steps extractor

匹配：

```text
办理流程
申请→受理→办结
网上申请
受理
审核
办结
结果送达
```

### 5.6 测试

新增：

```text
backend/tests/test_general_contact_extractor.py
backend/tests/test_general_service_object_extractor.py
backend/tests/test_general_application_conditions_ranking.py
backend/tests/test_general_process_steps_extractor.py
```
---

## 6. Phase G4：DeepSeek Candidate Ablation

### 6.1 当前问题

DeepSeek 已经：

```text
provider smoke passed
suggestion_count = 2
secret leak = false
```

但：

```text
measurable contribution = 0.0
```

下一步必须把 DeepSeek 接入 candidate generation 和 review support 的可测路径。

### 6.2 DeepSeek 使用边界

允许：

```text
生成字段候选
从复杂段落拆政策措施
解释 date role
辅助判断 issuer/source evidence
给 review item 生成建议
总结为什么 keep_pending
发现 alias/regex/badcase candidate
```

禁止：

```text
直接 accepted mapping
自动 approve review
自动 activate knowledge pack
无 evidence 补字段
覆盖 badcase filter
```

### 6.3 DeepSeek Candidate Schema

新增：

```text
backend/app/schemas/llm_candidate.py
```

建议字段：

```json
{
  "doc_id": "...",
  "target_field": "...",
  "candidate_value": "...",
  "source_block_ids": [],
  "evidence_quote": "...",
  "reason": "...",
  "confidence": "high|medium|low",
  "risk_flags": [],
  "needs_review": true,
  "provider": "deepseek",
  "model": "...",
  "auto_accept_allowed": false
}
```

### 6.4 DeepSeek Prompt

```text
You are assisting a deterministic schema mapping system.
You must only propose candidates that are supported by the provided UIR source blocks.
Do not invent values.
Do not use retrieved_at as publish_date or effective_date.
Do not use authored date as publish_date unless the evidence explicitly says publication date.
Do not use website owner, interpreting agency, contractor, or contact department as issuer.
Return JSON only.

Target fields:
{target_fields}

Schema field definitions:
{field_definitions}

UIR source blocks:
{source_blocks}

Known forbidden pairs:
{forbidden_pairs}

Return:
[
  {
    "target_field": "...",
    "candidate_value": "...",
    "source_block_ids": ["..."],
    "evidence_quote": "...",
    "reason": "...",
    "confidence": "high|medium|low",
    "risk_flags": [],
    "needs_review": true
  }
]
```

### 6.5 Ablation 组

必须跑四组：

```text
A deterministic_only
B deterministic + DeepSeek candidates as review_required
C deterministic + DeepSeek candidates + Review Judge dry-run
D deterministic + DeepSeek candidates + Review Judge scoped apply-guarded
```

如果有 Knowledge draft，再跑：

```text
E deterministic + scoped knowledge draft impact preview
```

### 6.6 新增脚本

```text
scripts/eval_deepseek_candidate_ablation.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_deepseek_candidate_ablation.py `
  --base-url http://127.0.0.1:8000 `
  --dataset examples\real_world `
  --focus-doc-type policy_doc `
  --focus-fields issuer,publish_date,effective_date,policy_measures,target_audience,document_number `
  --out reports\phase_g_deepseek_candidate_ablation_report.json `
  --markdown reports\phase_g_deepseek_candidate_ablation_report.md
```

### 6.7 报告字段

```json
{
  "deterministic_only": {
    "average_recall": 0.742603,
    "policy_recall": 0.665575,
    "required_missing": 2,
    "review_required": 21
  },
  "deepseek_candidates": {
    "requests": 0,
    "success": 0,
    "parse_success_rate": 0.0,
    "candidates": 0,
    "evidence_linked_candidates": 0,
    "candidate_fields": {}
  },
  "judge_supported": {
    "supported_candidates": 0,
    "rejected_candidates": 0,
    "keep_pending_candidates": 0
  },
  "delta": {
    "average_recall_delta": 0.0,
    "policy_recall_delta": 0.0,
    "required_missing_delta": 0,
    "review_required_delta": 0
  },
  "safety": {
    "badcase_violations": 0,
    "llm_auto_accepted_count": 0,
    "secret_leaks": 0
  }
}
```

### 6.8 DeepSeek 有效性判断

DeepSeek 被认为有效，至少满足一项：

```text
policy_doc recall 提升 >= 0.02
required_missing 减少 >= 1
review_required 减少 >= 2 且 no unsafe apply
发现可沉淀的 scoped alias/regex/badcase >= 3
evidence-linked candidates >= 10 且 Review Judge 支持率 >= 50%
```

如果不满足，报告必须写：

```text
DeepSeek reachable but no measurable contribution in this round.
```
---

## 7. Phase G5：Review Judge Scoped Apply 与 Knowledge Draft

### 7.1 决策原则

Review Judge 是 AI 模拟审核员，不是真人。所有记录必须写：

```text
reviewer_type = ai_review_subagent
reviewer_id = codex_review_judge_v2
```

禁止写：

```text
reviewer_type = human
manual_approved = true
```

### 7.2 apply-guarded 条件

允许 approve 的必要条件：

```text
scope == current_eval_run
suggestion == approve
safe_to_apply == true
source_block_ids not empty
not LLM-only
badcase_hit == false
forbidden_pair_hit == false
confidence == high
field-specific rule says auto approval allowed
```

允许 reject 的必要条件：

```text
explicit forbidden pair
badcase hit
source evidence contradicts target field
```

其他全部：

```text
keep_pending
```

### 7.3 运行命令

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --dataset-id real_world_non_procurement_50 `
  --include-historical false `
  --use-deepseek `
  --out reports\phase_g_review_judge_scoped_report.json `
  --markdown reports\phase_g_review_judge_scoped_report.md
```

确认 dry-run 后再运行：

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode apply-guarded `
  --dataset-id real_world_non_procurement_50 `
  --include-historical false `
  --use-deepseek `
  --out reports\phase_g_ai_review_apply_report.json `
  --markdown reports\phase_g_ai_review_apply_report.md
```

### 7.4 Knowledge Candidate

只有以下情况生成：

```text
apply-guarded approve 成功
或真实人工确认
且 source evidence 完整
且不属于 forbidden/high-risk unresolved
```

Knowledge candidate scope 必须是：

```text
schema_id
template_id
doc_type
source_system
field
source_label
section_path
value_pattern
reviewer_type
decision_id
```

不得默认 global。

### 7.5 Impact Preview

新增或运行：

```powershell
backend\.venv\Scripts\python.exe scripts\preview_knowledge_pack_impact.py `
  --base-url http://127.0.0.1:8000 `
  --pack-scope phase_g `
  --dataset examples\real_world `
  --out reports\phase_g_knowledge_pack_impact_preview.json `
  --markdown reports\phase_g_knowledge_pack_impact_preview.md
```

必须验证：

```text
badcase violations = 0
old snapshots unchanged
review_required delta 可解释
no global unintended impact
```

默认不 activate pack。只有用户明确要求且 preview passed，才允许 active。
---

## 8. Phase G6：Production Shadow + Blind Set

### 8.1 为什么必须做

当前 blind set 状态是：

```text
not_run
can claim 0.85 = false
reason = no independent production shadow/blind UIR corpus with gold labels
```

所以没有独立 blind set 前，不能声称任意生产 UIR 0.85+。

### 8.2 数据结构

建立：

```text
examples/production_shadow/
  manifest.json
  warmup/
    general/
    meeting/
    policy/
    procurement/
    unknown/
  blind/
    general/
    meeting/
    policy/
    procurement/
    unknown/
  gold/
    mapping_gold.jsonl
    badcases.jsonl
    field_definitions.json
```

### 8.3 manifest.json

格式：

```json
{
  "dataset_id": "production_shadow_v1",
  "created_at": "...",
  "source": "production_shadow",
  "splits": {
    "warmup": [],
    "blind": []
  },
  "documents": [
    {
      "doc_id": "...",
      "path": "...",
      "split": "blind",
      "doc_type": "policy_doc",
      "source_system": "...",
      "schema_id": "...",
      "template_id": "...",
      "quality_gate_expected": "pass|review|unsupported",
      "gold_path": "gold/mapping_gold.jsonl"
    }
  ]
}
```

### 8.4 样本数量建议

最低可执行版：

```text
warmup = 60
blind = 60
```

正式证明版：

```text
warmup = 150~300
blind = 100~200
```

blind 最低结构：

```text
general_doc >= 15
meeting_doc >= 15
policy_doc >= 25
procurement_doc >= 5
unknown/other >= 0~5
```

如果暂时只有非采购，也要写清楚：

```text
0.85 claim is for non-procurement supported UIR only.
```

### 8.5 Gold Label 规范

`mapping_gold.jsonl` 每行：

```json
{
  "doc_id": "...",
  "doc_type": "policy_doc",
  "schema_id": "...",
  "target_field": "publish_date",
  "expected_value": "2026-02-06",
  "source_block_ids": ["b12"],
  "source_quote": "发布时间：2026年2月6日",
  "required": true,
  "accept_review_required": false,
  "notes": "publication date, not authored date"
}
```

对于允许 review 的字段：

```json
{
  "doc_id": "...",
  "target_field": "issuer",
  "expected_value": "工业和信息化部等部门",
  "accept_review_required": true,
  "risk": "joint issuer"
}
```

Badcase gold：

```json
{
  "doc_id": "...",
  "source_text": "成文日期：2026年2月2日",
  "target_field": "publish_date",
  "forbidden": true,
  "reason": "authored date is not publication date"
}
```

### 8.6 Gold Coverage Report

新增脚本：

```text
scripts/check_production_shadow_gold_coverage.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\check_production_shadow_gold_coverage.py `
  --manifest examples\production_shadow\manifest.json `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --out reports\production_shadow_gold_coverage_report.json `
  --markdown reports\production_shadow_gold_coverage_report.md
```

检查：

```text
每个 blind doc 至少有 required fields gold
每个 target schema required field 有 gold 或明确 not_applicable
policy_doc 日期角色有 gold
issuer 有 source quote
badcase 覆盖 forbidden pairs
```

### 8.7 Blind Eval

新增或完善：

```text
scripts/eval_production_shadow_mapping.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_shadow_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --manifest examples\production_shadow\manifest.json `
  --split blind `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --badcases examples\production_shadow\gold\badcases.jsonl `
  --out reports\phase_g_blind_set_eval_report.json `
  --markdown reports\phase_g_blind_set_eval_report.md
```

### 8.8 Blind Set 禁止事项

```text
不得用 blind gold 调规则
不得把 blind samples 加入 template warmup
不得在看到 blind failure 后直接修同一个 blind doc 再重报
不得只报告 warmup 成绩
```

如果需要修复 blind 暴露的问题：

```text
冻结 blind v1 结果
把失败类型转入下一版 warmup
创建 blind v2
重新验证
```
---

## 9. 0.85 指标定义与最终门槛

### 9.1 必须报告的指标

```text
average_recall
auto_accepted_precision
auto_accepted_recall
mapped_or_review_recall
strict_pass_rate
required_missing_rate
review_required_rate
badcase_violations
llm_auto_accepted_count
package_verification_rate
quality_gate_pass_rate
```

### 9.2 正式声明 0.85 的最低条件

```text
blind_set_average_recall >= 0.85
auto_accepted_precision >= 0.95
mapped_or_review_recall >= 0.90
required_missing_rate <= 0.05，最好 <= 0.02
review_required_rate <= 0.15
badcase_violations = 0
llm_auto_accepted_count = 0
package_verification_rate = 1.0
secret_leaks = 0
report_consistency_passed = true
```

### 9.3 分类型门槛

```text
general_doc recall >= 0.90
meeting_doc recall >= 0.85
policy_doc recall >= 0.85
procurement_doc recall >= 0.85, if included
```

如果某类型不足 0.85，不得说整体“任意 UIR 0.85+”，只能说：

```text
overall average >= 0.85, but policy_doc remains below threshold.
```

---

## 10. 评测报告一致性

### 10.1 必须生成

```text
reports/phase_g_report_consistency.json
reports/phase_g_report_consistency.md
```

对比：

```text
mapping evaluator
semantic quality report
strict validation analysis
blind set evaluator
review judge report
```

字段：

```text
dataset_size
average_recall
strict_pass_count
required_missing_count
review_required_count
badcase_violations
llm_auto_accepted_count
package_verify_pass_count
```

### 10.2 不一致处理

任何不一致都必须解释：

```text
different diagnostic scope
different split
field-level vs candidate-level
current run vs historical queue
warmup vs blind
```

没有解释不得标记 Passed。

---

## 11. 最终命令清单

### 11.1 单元测试

```powershell
backend\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_review_scope_filtering.py `
  backend\tests\test_policy_publish_date_extractor.py `
  backend\tests\test_policy_issuer_extractor.py `
  backend\tests\test_policy_effective_date_extractor.py `
  backend\tests\test_policy_measures_extractor.py `
  backend\tests\test_policy_target_audience_extractor.py `
  backend\tests\test_general_contact_extractor.py `
  backend\tests\test_general_service_object_extractor.py `
  backend\tests\test_general_application_conditions_ranking.py `
  backend\tests\test_deepseek_candidate_ablation.py `
  backend\tests\test_production_shadow_gold_coverage.py -q
```

### 11.2 Phase G 50 样本评测

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_g_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_g_non_procurement_mapping_eval_report.md
```

### 11.3 Gap Analysis

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\phase_g_non_procurement_gap_analysis.json `
  --markdown reports\phase_g_non_procurement_gap_analysis.md
```

### 11.4 DeepSeek Candidate Ablation

```powershell
backend\.venv\Scripts\python.exe scripts\eval_deepseek_candidate_ablation.py `
  --base-url http://127.0.0.1:8000 `
  --dataset examples\real_world `
  --focus-doc-type policy_doc `
  --focus-fields issuer,publish_date,effective_date,policy_measures,target_audience,document_number `
  --out reports\phase_g_deepseek_candidate_ablation_report.json `
  --markdown reports\phase_g_deepseek_candidate_ablation_report.md
```

### 11.5 Review Judge Scoped

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --dataset-id real_world_non_procurement_50 `
  --include-historical false `
  --use-deepseek `
  --out reports\phase_g_review_judge_scoped_report.json `
  --markdown reports\phase_g_review_judge_scoped_report.md
```

### 11.6 Production Blind

```powershell
backend\.venv\Scripts\python.exe scripts\check_production_shadow_gold_coverage.py `
  --manifest examples\production_shadow\manifest.json `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --out reports\production_shadow_gold_coverage_report.json `
  --markdown reports\production_shadow_gold_coverage_report.md

backend\.venv\Scripts\python.exe scripts\eval_production_shadow_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --manifest examples\production_shadow\manifest.json `
  --split blind `
  --gold examples\production_shadow\gold\mapping_gold.jsonl `
  --badcases examples\production_shadow\gold\badcases.jsonl `
  --out reports\phase_g_blind_set_eval_report.json `
  --markdown reports\phase_g_blind_set_eval_report.md
```

### 11.7 最终验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```
---

## 12. 禁止事项

```text
不得把 DeepSeek output 直接 accepted
不得把 Review Judge 标记为 human reviewer
不得读取全库历史 pending 作为当前 run 的 review 指标
不得在 blind set 上调参
不得删除 required fields 提升 strict pass
不得放宽 schema strict validation 刷分
不得关闭 badcase filter
不得让 LLM suggestion 自动 accepted
不得激活 global knowledge pack，除非用户明确确认
不得把 API key 写入 tracked 文件、报告、日志、fixtures、task snapshots
不得用 package verification 代替 semantic validation
```

Forbidden pairs 必须保持：

```text
成文日期 -> publish_date
发布日期 -> effective_date
retrieved_at -> effective_date
主持人 -> attendees
联系人 -> attendees
承办单位 -> issuer
解读机构 -> issuer
预算金额 -> award_amount
控制价 -> award_amount
```

---

## 13. 最终交付物

Codex 必须提交：

```text
reports/phase_g_baseline_non_procurement_mapping_eval_report.json/.md
reports/phase_g_non_procurement_mapping_eval_report.json/.md
reports/phase_g_non_procurement_gap_analysis.json/.md
reports/phase_g_semantic_mapping_quality_report.json/.md
reports/phase_g_strict_validation_failure_analysis.json/.md
reports/phase_g_report_consistency.json/.md

reports/phase_g_review_judge_scoped_report.json/.md
reports/phase_g_ai_review_apply_report.json/.md
reports/phase_g_deepseek_candidate_ablation_report.json/.md
reports/phase_g_knowledge_pack_impact_preview.json/.md

reports/production_shadow_gold_coverage_report.json/.md
reports/phase_g_blind_set_eval_report.json/.md
reports/phase_g_secret_redaction_audit_report.json/.md

docs/phase_g_uir085_handoff.md
```

如果 production blind corpus 仍不存在，必须提交：

```text
reports/production_shadow_dataset_blocker_report.md
```

并写明：

```text
Cannot claim 0.85 because independent production blind UIR corpus with gold labels is missing.
```

---

## 14. 交接文档模板

`docs/phase_g_uir085_handoff.md`：

```markdown
# Phase G UIR 0.85 Handoff

## Summary

- Current 50-sample average recall:
- Current strict pass:
- Policy recall:
- Meeting recall:
- General recall:
- Required missing:
- Review required:
- Badcase violations:
- LLM auto accepted:
- Package verification:
- Secret leaks:

## Review Scope Fix

- current evaluator review_required:
- scoped review items found:
- historical skipped:
- procurement skipped:
- consistency:

## Policy Hardening

- policy recall before:
- policy recall after:
- strict pass before:
- strict pass after:
- remaining policy gaps:

## General Hardening

- general recall before:
- general recall after:
- remaining general gaps:

## DeepSeek Ablation

- provider configured:
- candidate count:
- evidence-linked candidate count:
- judge-supported count:
- recall delta:
- required_missing delta:
- review_required delta:
- safety result:

## Review Judge

- dry-run:
- apply-guarded:
- applied approve:
- applied reject:
- kept pending:
- unsafe skipped:

## Knowledge Pack

- draft created:
- impact preview:
- activated:
- scope:
- badcase result:

## Production Shadow / Blind

- production shadow exists:
- blind doc count:
- gold coverage:
- blind average recall:
- auto precision:
- mapped_or_review recall:
- can claim 0.85:
- if false, why:

## Final Claim

Choose one:

1. Can claim:
   The system reaches 0.85+ semantic mapping quality on production blind UIR that pass the UIR Quality Gate and belong to supported schema families.

2. Cannot claim:
   The system improves over Phase D but cannot honestly claim 0.85+ because ...

## Commands

...
```

---

## 15. 最终判定规则

### 15.1 可以声明 UIR 0.85+

必须同时满足：

```text
phase_g_blind_set_eval_report.status = passed
blind_average_recall >= 0.85
auto_accepted_precision >= 0.95
mapped_or_review_recall >= 0.90
required_missing_rate <= 0.05
badcase_violations = 0
llm_auto_accepted_count = 0
package_verification_rate = 1.0
secret_leaks = 0
report_consistency_passed = true
```

### 15.2 不可以声明 UIR 0.85+

任一条件成立则不可声明：

```text
没有 independent blind set
blind set not_run
blind average_recall < 0.85
policy_doc blind recall < 0.85 且未声明 unsupported
badcase violations > 0
llm_auto_accepted_count > 0
secret leaks > 0
package verification < 100%
report consistency failed 且无解释
```

### 15.3 若只在 50 本地样本达到 0.85

只能写：

```text
The local 50-document benchmark reached 0.85, but production UIR 0.85 is not yet proven without blind-set validation.
```

不得写：

```text
任意生产 UIR 已达到 0.85。
```

---

## 16. 最终一句话给 Codex

本轮的成败不取决于 DeepSeek 有没有“看起来聪明”，而取决于：

```text
是否修正 Review scope；
是否显著提升 policy_doc；
是否让 DeepSeek 产生 source-backed、可审计、可量化贡献；
是否建立 independent production blind set；
是否在 blind set 上达到 0.85，同时保持 badcase=0、LLM auto accepted=0、package=100%、secret=0。
```
