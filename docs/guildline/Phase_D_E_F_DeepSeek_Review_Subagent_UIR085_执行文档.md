# Phase D/E/F：DeepSeek + Review 子智能体 + UIR 0.85 泛化达标执行文档

> 交付对象：Codex  
> 项目：SchemaPack Agent / 课题 5 数据格式标准化转换智能体  
> 当前目标：从 50 个非采购真实 UIR 样本 average recall `0.717`，推进到“通过 UIR 质量门禁的生产 UIR，在已支持 Schema family 内稳定达到字段语义映射质量 0.85+”。  
> 核心新增：在 Review 环节启动 Review Judge 子智能体，用接近人工审核员的判断方式审查 review-required 项和 DeepSeek / LLM suggestions；但所有行为必须可追溯、可审计、可复现，不能伪装成人类审核员，不能绕过 badcase 与 safety gates。

---

## 0. 核心原则

### 0.1 目标表述必须可证明

不要宣称“任何质量、任何领域、任何结构的 UIR 都无条件达到 0.85”。本轮目标应定义为：

```text
对通过 UIR Quality Gate、属于已支持 catalog family、字段定义在目标 schema 内、source evidence 可追溯的生产 UIR，
自动映射质量逐步达到 0.85+；
对不满足门禁、分布外、证据不足或高风险的 UIR，自动降级为 review_required / unsupported / schema_route_review。
```

原因：如果上游 UIR 本身缺标题、缺 block 顺序、缺 source evidence、metadata 错乱，Mapping Agent 不可能凭空恢复所有语义。

### 0.2 Review 子智能体不能伪装成人类

用户希望“子智能体以人的身份去 review”。执行时转译为：

```text
Review Judge Sub-Agent 以“模拟人工审核员”的标准进行判断，
但审计字段必须写明 reviewer_type = "ai_review_subagent" 或 "codex_review_judge"。
```

禁止写入：

```text
reviewed_by = "human"
operator_type = "human"
manual_approved = true
```

除非确实有真实人类审核员最终确认。

允许写入：

```text
reviewer_type = "ai_review_subagent"
reviewer_id = "codex_review_judge_v1"
decision_source = "ai_assisted_review"
requires_human_confirmation = false/true
```

### 0.3 DeepSeek 只能辅助，不得自动接受映射

DeepSeek 可以用于：

```text
候选字段生成
复杂段落理解
解释 source evidence
对 review item 给出判断建议
对 LLM suggestion 做二次审查
生成 review summary
发现可沉淀 alias / forbidden pair 的候选
```

DeepSeek 不可以：

```text
直接 accepted mapping
绕过 badcase filter
在无 source block evidence 时补字段
自动激活 schema/template
自动激活 Knowledge Pack
把 LLM-only suggestion 写成 accepted
把 API key 写入 task options、reports、fixtures、logs、audit、git
```

### 0.4 必须保持的安全边界

```text
badcase violations = 0
llm_auto_accepted_count = 0
package verification = 100%
review_required / badcase_blocked 状态可见
历史 task snapshots 不变
draft knowledge pack 不影响当前 task
```

---

## 1. 当前基线

### 1.1 Phase C Sprint 4 主基线

当前 50 个非采购样本：

```text
dataset_size = 50
average_recall = 0.717
strict_pass = 31/50
review_required = 22
required_missing = 4
badcase_violations = 0
package_verification = 50/50
```

按文档类型：

```text
general_doc: 15 docs, recall 0.824, strict pass 13/15
meeting_doc: 15 docs, recall 0.692, strict pass 9/15
policy_doc: 20 docs, recall 0.654, strict pass 9/20
```

结论：

```text
general_doc 已接近 0.85；
meeting_doc 与 policy_doc 是冲 0.85 的关键短板；
policy_doc 是最大短板。
```

### 1.2 当前高频缺口

来自 Phase C Sprint 4 semantic report 的 ranked fixes：

```text
policy_doc.publish_date: candidate_not_extracted, count 15
meeting_doc.meeting_number: candidate_not_extracted, count 7
meeting_doc.topics: candidate_not_extracted, count 7
policy_doc.policy_measures: candidate_not_extracted, count 7
general_doc.application_conditions: candidate_extracted_but_not_ranked, count 6
general_doc.contact: candidate_not_extracted, count 6
general_doc.service_object: candidate_not_extracted, count 6
meeting_doc.organizer: candidate_not_extracted, count 6
policy_doc.target_audience: candidate_not_extracted, count 6
general_doc.application_conditions: candidate_not_extracted, count 5
meeting_doc.attendees: candidate_not_extracted, count 5
policy_doc.effective_date: candidate_not_extracted, count 5
policy_doc.issuer: candidate_not_extracted, count 5
meeting_doc.meeting_date: candidate_not_extracted, count 4
```

---

## 2. 本轮总体路线

本轮分三个阶段：

```text
Phase D：50 样本字段语义硬化
Phase E：DeepSeek + Review 子智能体评估闭环
Phase F：Production Shadow / Blind Set 泛化验证，冲 0.85
```

### 2.1 Phase D 目标

```text
dataset_size = 50 保持不变
average_recall: 0.717 -> >= 0.78
policy_doc recall: 0.654 -> >= 0.75
meeting_doc recall: 0.692 -> >= 0.76
general_doc recall: 0.824 -> >= 0.85
strict_pass: 31/50 -> >= 38/50
required_missing: 4 -> <= 2
review_required: 22 -> <= 18
badcase_violations: 0
llm_auto_accepted_count: 0
package_verification: 50/50
```

### 2.2 Phase E 目标

```text
DeepSeek real-provider mode 能成功配置并运行
DeepSeek suggestions 全部 report-only 或 review_required
Review Judge Sub-Agent 能判断 review items 与 DeepSeek suggestions
AI-reviewed decisions 有完整 evidence、reason、risk、confidence、decision trace
LLM auto accepted = 0
badcase violations = 0
secret leaks = 0
```

### 2.3 Phase F 目标

```text
建立 production shadow dataset
建立 blind-test split，禁止在 blind-test 上调参
blind-set average recall >= 0.80 起步
最终目标 blind-set average recall >= 0.85
auto accepted precision >= 0.92 起步，最终 >= 0.95
mapped-or-review recall >= 0.90
required_missing_rate <= 2%~5%
review_required_rate <= 10%~15%
badcase violations = 0
llm_auto_accepted_count = 0
package verification = 100%
```

---

## 3. 交付物清单

Codex 最终必须生成：

```text
reports/phase_d_non_procurement_mapping_eval_report.json
reports/phase_d_non_procurement_mapping_eval_report.md
reports/phase_d_semantic_mapping_quality_report.json
reports/phase_d_semantic_mapping_quality_report.md
reports/phase_d_strict_validation_failure_analysis.json
reports/phase_d_strict_validation_failure_analysis.md
reports/phase_d_report_consistency.json
reports/phase_d_report_consistency.md

reports/deepseek_provider_smoke_report.json
reports/deepseek_provider_smoke_report.md
reports/deepseek_ablation_report.json
reports/deepseek_ablation_report.md
reports/review_judge_subagent_report.json
reports/review_judge_subagent_report.md
reports/ai_review_apply_report.json
reports/ai_review_apply_report.md
reports/secret_redaction_audit_report.json
reports/secret_redaction_audit_report.md

reports/production_shadow_dataset_manifest.json
reports/production_shadow_eval_report.json
reports/production_shadow_eval_report.md
reports/blind_set_eval_report.json
reports/blind_set_eval_report.md

docs/phase_d_e_f_deepseek_review_subagent_handoff.md
```

如果暂时没有生产 shadow 数据，Codex 必须生成：

```text
reports/production_shadow_dataset_plan.md
```

并明确说明缺少真实生产 UIR，不能声称已完成 blind 0.85 验证。

---

## 4. 分支与前置检查

### 4.1 新建分支

```powershell
git status
git checkout -b codex/phase-d-deepseek-review-judge
```

若当前已有未提交更改，先执行：

```powershell
git status --short
```

不要覆盖用户未提交内容。

### 4.2 读取项目配置

Codex 必须先检查：

```powershell
Get-Content .env.example -ErrorAction SilentlyContinue
Get-Content .env.production.example -ErrorAction SilentlyContinue
Get-Content backend\app\config.py -Encoding UTF8
Get-Content backend\app\services\llm_fallback_service.py -Encoding UTF8 -ErrorAction SilentlyContinue
Get-ChildItem backend\app\services -Filter "*llm*" -Recurse
Get-ChildItem backend\app\services -Filter "*deepseek*" -Recurse
```

目的：确认真实环境变量名称、DeepSeek provider 是否已有、LLM fallback / adapter report-only 路径、secret redaction 逻辑。

不要凭空假设变量名。若项目已定义变量，以代码为准。

### 4.3 基线验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另开终端运行当前基线：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_d_baseline_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_d_baseline_non_procurement_mapping_eval_report.md
```

---

## 5. DeepSeek 本地安全配置

### 5.1 密钥处理原则

用户会把 API key 提交给 Codex，但 Codex 必须遵守：

```text
API key 只允许存在于本地环境变量或本地未跟踪 .env.local
不得写入 git tracked 文件
不得写入 reports
不得写入 docs
不得写入 fixtures
不得写入 task options
不得写入 execution snapshots
不得写入 audit logs
不得在终端 echo 完整 key
```

### 5.2 推荐本地配置方式

优先使用当前 PowerShell session 环境变量：

```powershell
$env:LLM_FALLBACK_ENABLED = "true"
$env:LLM_MODE = "deepseek"
$env:DEEPSEEK_API_KEY = "<USER_PROVIDED_KEY>"
```

如果代码使用通用 OpenAI-compatible 变量，则按 `backend/app/config.py` 实际字段配置，例如：

```powershell
$env:LLM_FALLBACK_ENABLED = "true"
$env:LLM_MODE = "openai_compatible"
$env:LLM_API_KEY = "<USER_PROVIDED_KEY>"
$env:LLM_BASE_URL = "<DEEPSEEK_OR_PROJECT_CONFIGURED_BASE_URL>"
$env:LLM_MODEL = "<DEEPSEEK_MODEL_NAME>"
```

具体变量名与 base URL 不要硬编码，Codex 必须从项目配置和文档中确认。若项目已有 `llm_mode = "deepseek"` 路径，则优先使用该路径。

### 5.3 可选 .env.local

如果需要持久化到本地文件：

```powershell
Copy-Item .env.example .env.local
git check-ignore .env.local
```

如果 `.env.local` 没被 ignore，立即停止，不得写 key。

### 5.4 Secret redaction 检查

```powershell
git status --short
git diff -- . ':!*.lock'

Select-String -Path reports\*.json,reports\*.md,docs\*.md -Pattern "sk-|Bearer|DEEPSEEK_API_KEY|LLM_API_KEY|api_key|credential" -SimpleMatch -ErrorAction SilentlyContinue
```

生成：

```text
reports/secret_redaction_audit_report.json
reports/secret_redaction_audit_report.md
```

报告字段：

```json
{
  "secret_leaks": 0,
  "scanned_paths": [],
  "redacted_values_found": 0,
  "raw_key_found": false,
  "status": "passed"
}
```

---

## 6. DeepSeek Provider Smoke Test

### 6.1 目标

验证 DeepSeek 是否真的发挥作用，但不能改变 production mapping 结果。

Smoke test 只验证：

```text
provider 可调用
超时/失败可被捕获
返回内容可解析
返回建议有 evidence requirement
输出进入 assisted_suggestions 或 review_required
没有 auto accepted
没有 secret leak
```

### 6.2 新增或完善脚本

建议新增：

```text
scripts/eval_deepseek_provider_smoke.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_deepseek_provider_smoke.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\deepseek_provider_smoke_report.json `
  --markdown reports\deepseek_provider_smoke_report.md
```

若当前项目已有类似 LLM fallback evaluator，则在其基础上扩展，不要重复造轮子。

### 6.3 Smoke test 报告字段

```json
{
  "provider": "deepseek",
  "network_mode": "real_provider",
  "configured": true,
  "requests_attempted": 5,
  "requests_succeeded": 5,
  "requests_failed": 0,
  "timeout_count": 0,
  "parse_success_rate": 1.0,
  "assisted_suggestions_count": 0,
  "review_required_suggestions_count": 0,
  "auto_accepted_count": 0,
  "secret_leaks": 0,
  "warnings": []
}
```

若没有配置 key：

```json
{
  "configured": false,
  "status": "skipped",
  "reason": "DEEPSEEK_API_KEY or project-specific LLM credential is missing"
}
```

不能把 skipped 写成 passed。

---

## 7. Review Judge 子智能体设计

### 7.1 子智能体职责

Review Judge 子智能体是 Review 环节的“模拟人工审核员”。

输入：

```text
pending review item
mapping evidence
source blocks
source path
target schema field definition
candidate value
confidence tier
risk flags
badcase filter
review_required_reason
DeepSeek suggestion, if any
historical accepted/rejected knowledge
forbidden pairs
```

输出：

```text
approve / reject / keep_pending
confidence
reason
evidence_summary
risk assessment
whether DeepSeek suggestion is supported
whether knowledge candidate can be created
whether human confirmation is required
```

### 7.2 不得绕过的安全门

无论 Review Judge 说什么，下游 apply 仍必须检查：

```text
badcase_filter.hit == false
forbidden_pair == false
source evidence exists
source block exists
not LLM-only
not source-untraceable
not medium/low confidence fuzzy auto-accepted
not high-risk field unless field-specific safe rule exists
```

### 7.3 决策类型

```text
approve
reject
keep_pending
```

不要增加第四种会影响 apply 的状态。可以增加辅助字段：

```text
suggest_knowledge_candidate = true/false
requires_human_confirmation = true/false
deepseek_supported = true/false
```

### 7.4 输出 JSON schema

新增：

```text
backend/app/schemas/review_judge.py
```

建议 schema：

```python
class ReviewJudgeDecision(BaseModel):
    review_id: str
    task_id: str | None = None
    doc_id: str | None = None
    schema_id: str
    template_id: str | None = None
    doc_type: str
    source_label: str | None = None
    source_value: str | None = None
    target_field: str
    suggestion: Literal["approve", "reject", "keep_pending"]
    confidence: Literal["high", "medium", "low"]
    safe_to_apply: bool
    requires_human_confirmation: bool
    reason: str
    evidence_summary: str
    source_block_ids: list[str] = []
    risk_flags: list[str] = []
    badcase_hit: bool = False
    forbidden_pair_hit: bool = False
    deepseek_used: bool = False
    deepseek_supported: bool | None = None
    reviewer_type: Literal["ai_review_subagent"] = "ai_review_subagent"
    reviewer_id: str = "codex_review_judge_v1"
    created_at: datetime
```

### 7.5 子智能体 Prompt 模板

新增：

```text
backend/app/services/review_judge_prompt.py
```

Prompt：

```text
You are a SchemaPack Review Judge Sub-Agent.
You simulate a careful human reviewer, but you are not a real human.
You must not approve any mapping without source evidence.

Project rules:
- LLM suggestions must never be auto-accepted.
- Badcase or forbidden pairs must be rejected or kept pending.
- Source-untraceable mappings must not be approved.
- Medium/low-confidence fuzzy mappings must not be automatically approved.
- High-risk fields require explicit field-specific evidence.
- If unsure, keep_pending.

You must decide one of:
approve, reject, keep_pending.

Review item:
{review_item_json}

Target field definition:
{target_field_schema}

Source evidence:
{source_evidence_json}

DeepSeek suggestion:
{deepseek_suggestion_json}

Forbidden pairs:
{forbidden_pairs_json}

Return strict JSON:
{
  "suggestion": "...",
  "confidence": "...",
  "safe_to_apply": true/false,
  "requires_human_confirmation": true/false,
  "reason": "...",
  "evidence_summary": "...",
  "deepseek_supported": true/false/null,
  "risk_flags": []
}
```

### 7.6 高风险字段规则

默认高风险字段：

```text
policy_doc.issuer
policy_doc.publish_date
policy_doc.effective_date
policy_doc.valid_until
policy_doc.policy_measures
meeting_doc.attendees
meeting_doc.organizer
meeting_doc.meeting_date
meeting_doc.topics
meeting_doc.action_items
procurement_doc.award_amount
procurement_doc.budget_amount
```

这些字段即使 Review Judge 建议 approve，也要满足 field-specific evidence rule。

---

## 8. Codex Review Judge 执行脚本

### 8.1 新增脚本

```text
scripts/run_review_judge_subagent.py
```

支持模式：

```text
dry-run
apply-guarded
apply-with-human-override
```

### 8.2 dry-run

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --use-deepseek `
  --out reports\review_judge_subagent_report.json `
  --markdown reports\review_judge_subagent_report.md
```

`dry-run` 只生成建议，不修改 review。

### 8.3 apply-guarded

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode apply-guarded `
  --use-deepseek `
  --max-approve 20 `
  --max-reject 50 `
  --out reports\ai_review_apply_report.json `
  --markdown reports\ai_review_apply_report.md
```

`apply-guarded` 只能执行：

```text
suggestion = approve 且 safe_to_apply = true 且 all deterministic safety checks passed
suggestion = reject 且 forbidden_pair_hit = true 或 explicit negative evidence
```

其他全部 keep_pending。

### 8.4 apply-with-human-override

此模式只允许用户明确要求。Codex 不得默认使用。

```powershell
backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode apply-with-human-override `
  --confirmed-by "<real-human-name-or-operator-id>" `
  --out reports\ai_review_apply_report.json `
  --markdown reports\ai_review_apply_report.md
```

如果没有 `--confirmed-by`，脚本必须失败。

### 8.5 报告字段

```json
{
  "mode": "dry-run",
  "use_deepseek": true,
  "pending_total": 22,
  "suggest_approve": 0,
  "suggest_reject": 0,
  "suggest_keep_pending": 22,
  "safe_approve_count": 0,
  "unsafe_skipped": 22,
  "applied_approve": 0,
  "applied_reject": 0,
  "kept_pending": 22,
  "deepseek_suggestions_count": 0,
  "deepseek_supported_count": 0,
  "badcase_blocked_count": 0,
  "llm_auto_accepted_count": 0,
  "errors": 0,
  "decisions": []
}
```

---

## 9. DeepSeek Ablation 实验

### 9.1 目的

证明 DeepSeek 是否有实际贡献，而不是只接入 API。

### 9.2 实验组

至少跑四组：

```text
A. deterministic_only
B. deterministic + DeepSeek suggestions, no review judge
C. deterministic + DeepSeek suggestions + Review Judge dry-run
D. deterministic + DeepSeek suggestions + Review Judge apply-guarded + scoped Knowledge draft
```

若加 Knowledge Pack active，则必须另设 E 组：

```text
E. active scoped knowledge pack, future tasks only
```

### 9.3 新增脚本

```text
scripts/eval_deepseek_ablation.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_deepseek_ablation.py `
  --base-url http://127.0.0.1:8000 `
  --dataset examples\real_world `
  --out reports\deepseek_ablation_report.json `
  --markdown reports\deepseek_ablation_report.md
```

### 9.4 指标

```json
{
  "groups": {
    "deterministic_only": {
      "average_recall": 0.717,
      "strict_pass": 31,
      "review_required": 22,
      "required_missing": 4,
      "badcase_violations": 0,
      "llm_auto_accepted_count": 0
    },
    "deepseek_suggestions": {
      "suggestions_count": 0,
      "evidence_linked_suggestions_rate": 0.0,
      "parse_success_rate": 1.0,
      "secret_leaks": 0
    },
    "deepseek_plus_review_judge": {
      "judge_approve_suggestions": 0,
      "judge_reject_suggestions": 0,
      "judge_keep_pending_suggestions": 0,
      "safe_apply_count": 0
    }
  },
  "deepseek_contribution": {
    "review_required_delta": 0,
    "required_missing_delta": 0,
    "recall_delta": 0.0,
    "strict_pass_delta": 0,
    "safety_regression": false
  }
}
```

### 9.5 成功标准

DeepSeek 被认为“有作用”必须满足至少一个：

```text
1. 在 badcase=0、LLM auto accepted=0 前提下，减少 review_required；
2. 提升 mapped-or-review recall；
3. 提供 source-backed candidates，被 Review Judge 或人类确认后转化为 scoped knowledge；
4. 对 missing required 字段提供可追溯候选；
5. 帮助发现新的 conditional alias 或 forbidden pair。
```

如果只是返回自然语言、无法被 evidence-linked 或无法通过 Review Judge，则评价为：

```text
DeepSeek reachable, but no measurable mapping-quality contribution in this round.
```

---

## 10. UIR Quality Gate

### 10.1 新增服务

```text
backend/app/services/uir_quality_gate_service.py
backend/app/schemas/uir_quality_gate.py
```

### 10.2 Gate 检查项

```text
doc_id exists
blocks non-empty
block order exists or recoverable
title or heading candidate exists
source metadata exists
source_url / source path available when expected
block text non-empty ratio >= threshold
mojibake / garbled ratio below threshold
source block ids unique
anchors valid if present
tables parseable if present
schema router confidence >= threshold
doc_type supported
minimum field evidence coverage by doc_type
```

### 10.3 Gate 输出 schema

```json
{
  "doc_id": "...",
  "status": "pass | review | reject | unsupported",
  "quality_score": 0.0,
  "supported_doc_type": true,
  "schema_route_confidence": 0.0,
  "issues": [
    {
      "code": "missing_source_url",
      "severity": "warning",
      "action": "review"
    }
  ],
  "mapping_policy": {
    "allow_auto_accept": true,
    "require_review_for_high_risk_fields": true,
    "allow_llm_suggestions": true
  }
}
```

### 10.4 Gate 行为

```text
pass: 允许进入正常 mapping
review: 允许转换，但 high-risk fields 不自动 accepted
reject: 不执行任务，输出可读错误
unsupported: 进入 schema routing / adapter / schema draft 流程
```

### 10.5 Gate 验证脚本

```text
scripts/eval_uir_quality_gate.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_uir_quality_gate.py `
  --fixtures examples\real_world `
  --out reports\uir_quality_gate_eval_report.json `
  --markdown reports\uir_quality_gate_eval_report.md
```

---

## 11. 字段级专项抽取器

### 11.1 新增结构

不要在 `CandidateService` 里继续无限堆 if/else。建议新增字段级 extractor registry：

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
generic metadata extractors
generic block/table extractors
doc_type-specific field extractors
DeepSeek-assisted candidate suggestions, report-only/review-required
deduplicate
risk annotate
return candidates
```

### 11.2 policy_doc extractors

实现字段：

```text
publish_date
issuer
effective_date
document_number
policy_measures
target_audience
valid_until
summary
```

#### publish_date

可接受 evidence：

```text
网页 metadata published_at
页面明确“发布时间”
页面明确“发布日期”
正文头部“发布日期”
source manifest 中明确 publication_date
```

禁止 evidence：

```text
成文日期
施行日期
有效期至
检索时间 retrieved_at
附件日期
网页抓取时间
```

#### issuer

可接受 evidence：

```text
发文机关
印发机关
发布机关
文件头部主办发文机构
正文末尾落款机构
联合发文机构
```

禁止直接 accepted：

```text
承办单位
解读机构
联系人单位
网站主办单位
栏目名称
平台名称
```

#### effective_date

可接受 evidence：

```text
自 X 起施行
自 X 起执行
施行日期
实施时间
有效期自 X 起
```

禁止：

```text
发布日期
成文日期
检索时间
```

#### policy_measures

来源：

```text
支持措施
政策措施
主要措施
重点任务
主要内容
奖励/补贴/扶持条款
```

需 section-aware，不要抽全文。

#### target_audience

来源：

```text
适用对象
支持对象
面向对象
申报主体
服务对象
```

需要和 general_doc.service_object 区分。

### 11.3 meeting_doc extractors

实现字段：

```text
meeting_number
topics
organizer
attendees
meeting_date
decisions
action_items
```

#### meeting_number

匹配：

```text
第49次会议
第 64 次常务会议
2026年第2次会议
会议纪要第 X 号
```

来源优先：

```text
title
first paragraph
document metadata
```

#### topics

匹配：

```text
会议研究了
会议审议了
会议听取了
会议原则同意
研究部署
审议通过
```

输出列表化候选，保留 source block。

#### organizer

匹配：

```text
由 X 主持召开
X 组织召开
X 召集
```

注意不与 chairperson 混淆。若只有“主持人”，优先 chairperson，不自动 organizer。

#### attendees

匹配：

```text
出席人员
参会人员
参加会议的有
列席人员
```

禁止：

```text
联系人
主持人单人
发布人
```

#### meeting_date

匹配：

```text
会议于 X 召开
召开时间：X
X，召开第 N 次会议
```

禁止：

```text
网页发布时间
纪要发布日期
事项截止日期
```

### 11.4 general_doc extractors

实现字段：

```text
application_conditions
service_object
contact
application_materials
process_steps
```

重点修 ranking：

```text
application_conditions candidate_extracted_but_not_ranked
```

---

## 12. Conditional Template 与 Evidence Ranking

### 12.1 模板层级

Template 不再只是 alias 表，应支持：

```text
global aliases
doc_type-specific aliases
conditional aliases
negative aliases / forbidden contexts
required evidence scopes
default review behavior
```

### 12.2 conditional alias 示例

```json
{
  "target_field": "publish_date",
  "doc_type": "policy_doc",
  "aliases": ["发布日期", "发布时间"],
  "required_context_any": ["发布时间", "发布日期", "published_at", "source_metadata"],
  "forbidden_context_any": ["成文日期", "施行日期", "有效期至", "检索时间"],
  "auto_accept": true,
  "risk": "low"
}
```

```json
{
  "target_field": "issuer",
  "doc_type": "policy_doc",
  "aliases": ["发文机关", "印发机关", "发布机关"],
  "required_context_any": ["文件头", "落款", "发文机关", "印发"],
  "forbidden_context_any": ["承办单位", "解读机构", "联系人", "网站主办"],
  "auto_accept": false,
  "default_action": "review_required",
  "risk": "high"
}
```

### 12.3 Evidence ranking score

建议：

```text
final_score =
  label_score * 0.25
+ section_score * 0.25
+ value_pattern_score * 0.20
+ doc_type_prior * 0.15
+ source_position_score * 0.10
+ llm_support_score * 0.05
- negative_evidence_penalty
- badcase_penalty
```

`llm_support_score` 只加小权重，且不能让 LLM-only candidate auto accepted。

### 12.4 Ranking output trace

每个 mapping decision 需要输出：

```json
{
  "target_field": "publish_date",
  "selected_candidate": "...",
  "score_breakdown": {
    "label_score": 0.8,
    "section_score": 1.0,
    "value_pattern_score": 0.9,
    "doc_type_prior": 1.0,
    "source_position_score": 0.7,
    "llm_support_score": 0.0,
    "negative_evidence_penalty": 0.0
  },
  "evidence": [],
  "risk_flags": [],
  "review_required_reason": null
}
```

---

## 13. Review / Knowledge 飞轮

### 13.1 Review 后生成 knowledge candidate

只有以下情况允许：

```text
Review Judge approve
safe_to_apply = true
deterministic safety checks passed
or real human confirmed
source evidence exists
not LLM-only
```

Knowledge candidate 必须带 scope：

```text
schema_id
template_id
doc_type
source_system
department/site if known
field
source_label
section_path
value_pattern
approved_by
reviewer_type
```

### 13.2 Draft pack

Codex 可以创建 draft pack，但不得默认 active。

### 13.3 Impact preview

激活前必须生成：

```text
reports/knowledge_pack_impact_preview_phase_d.json
reports/knowledge_pack_impact_preview_phase_d.md
```

检查：

```text
新增 accepted mappings
减少 review count
是否命中 badcase
是否影响 old snapshots
是否扩大到不该影响的 doc_type/source_system
```

### 13.4 Active pack

默认不要自动 activate。只有以下条件才可自动激活：

```text
用户显式要求
impact preview passed
badcase violations = 0
old snapshot unchanged
scope 非 global，除非人工确认
```

---

## 14. Production Shadow / Blind Set

### 14.1 数据集结构

建议：

```text
examples/production_shadow/
  manifest.json
  warmup/
    general/
    meeting/
    policy/
  blind/
    general/
    meeting/
    policy/
  gold/
    mapping_gold.jsonl
    badcases.jsonl
```

### 14.2 数据划分

最低建议：

```text
warmup/dev: 150~300 UIR
blind-test: 100~200 UIR
```

若当前拿不到这么多，先建立结构，并用当前 50 样本 + 后续新增样本模拟：

```text
warmup: 可调参
blind: 不看答案，不调参
```

### 14.3 新增评测脚本

```text
scripts/eval_production_shadow_mapping.py
```

命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_shadow_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --manifest examples\production_shadow\manifest.json `
  --split blind `
  --out reports\blind_set_eval_report.json `
  --markdown reports\blind_set_eval_report.md
```

### 14.4 指标

```text
auto_accepted_precision
auto_accepted_recall
mapped_or_review_recall
average_recall
strict_pass_rate
required_missing_rate
review_required_rate
badcase_violations
llm_auto_accepted_count
package_verification_rate
by_doc_type metrics
by_source_system metrics
by_quality_gate_status metrics
```

### 14.5 0.85 证明标准

只有满足以下条件，才能写“生产有效 UIR 达到 0.85+”：

```text
blind-set average_recall >= 0.85
auto_accepted_precision >= 0.95
mapped_or_review_recall >= 0.90
policy_doc recall >= 0.85 或明确 unsupported/needs-review 规则
meeting_doc recall >= 0.85 或明确 unsupported/needs-review 规则
general_doc recall >= 0.90
required_missing_rate <= 2%~5%
badcase violations = 0
llm_auto_accepted_count = 0
package_verification_rate = 1.0
secret_leaks = 0
```

若只达到 0.80~0.85，应表述为：

```text
生产 shadow blind set 初步达标，但尚未完成 0.85 目标。
```

---

## 15. Strict Validation Hardening

### 15.1 必修内容

```text
date role classifier
date format normalizer
enum normalizer
required field preflight
semantic review repair suggestions
```

### 15.2 date role classifier

识别日期类型：

```text
publish_date
issue_date / document_date
effective_date
valid_until
meeting_date
deadline
retrieved_at
```

禁止：

```text
用日期格式匹配替代日期语义分类
把 retrieved_at 当 effective_date
把 成文日期 当 publish_date
把 publish_date 当 effective_date
```

### 15.3 required preflight

在 mapping 后、transform 前检查：

```text
required fields missing
candidate exists but rejected
candidate exists but review_required
candidate exists but value invalid
```

输出 repair suggestions，但不要自动补无 evidence 的值。

---

## 16. 测试计划

### 16.1 单元测试

新增或更新：

```text
backend/tests/test_policy_field_extractors.py
backend/tests/test_meeting_field_extractors.py
backend/tests/test_general_field_extractors.py
backend/tests/test_conditional_template_aliases.py
backend/tests/test_evidence_ranking.py
backend/tests/test_review_judge_subagent.py
backend/tests/test_deepseek_provider_safety.py
backend/tests/test_uir_quality_gate_service.py
backend/tests/test_secret_redaction.py
```

运行：

```powershell
backend\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_policy_field_extractors.py `
  backend\tests\test_meeting_field_extractors.py `
  backend\tests\test_general_field_extractors.py `
  backend\tests\test_conditional_template_aliases.py `
  backend\tests\test_evidence_ranking.py `
  backend\tests\test_review_judge_subagent.py `
  backend\tests\test_deepseek_provider_safety.py `
  backend\tests\test_uir_quality_gate_service.py `
  backend\tests\test_secret_redaction.py -q
```

### 16.2 回归测试

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_d_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_d_non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\phase_d_semantic_mapping_quality_report.json `
  --markdown reports\phase_d_semantic_mapping_quality_report.md
```

### 16.3 DeepSeek + Review Judge

```powershell
backend\.venv\Scripts\python.exe scripts\eval_deepseek_provider_smoke.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\deepseek_provider_smoke_report.json `
  --markdown reports\deepseek_provider_smoke_report.md

backend\.venv\Scripts\python.exe scripts\run_review_judge_subagent.py `
  --base-url http://127.0.0.1:8000 `
  --mode dry-run `
  --use-deepseek `
  --out reports\review_judge_subagent_report.json `
  --markdown reports\review_judge_subagent_report.md

backend\.venv\Scripts\python.exe scripts\eval_deepseek_ablation.py `
  --base-url http://127.0.0.1:8000 `
  --dataset examples\real_world `
  --out reports\deepseek_ablation_report.json `
  --markdown reports\deepseek_ablation_report.md
```

### 16.4 最终统一 gate

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

---

## 17. 禁止事项

Codex 不得执行：

```text
不得把 DeepSeek output 直接 accepted
不得把 Review Judge 标记为 human reviewer
不得把 API key 写入 tracked 文件
不得把 key 写入 reports/docs/fixtures/logs/audit/task options
不得关闭 badcase filter
不得删除 required fields 来提升指标
不得放宽 schema strict validation 来刷分
不得把 medium/low-confidence fuzzy 自动 approved
不得把 source-untraceable mapping approved
不得让 draft knowledge pack 影响当前 task
不得修改历史 task snapshots
不得把 package verification 当作 strict semantic validation
不得在 blind set 上调参
```

Forbidden pairs 必须继续保护：

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

## 18. 验收标准

### 18.1 Phase D 验收

```text
dataset_size = 50
average_recall >= 0.78
policy_doc recall >= 0.75
meeting_doc recall >= 0.76
general_doc recall >= 0.85
strict_pass >= 38/50
required_missing <= 2
review_required <= 18
badcase_violations = 0
llm_auto_accepted_count = 0
package_verification = 50/50
secret_leaks = 0
```

### 18.2 Phase E 验收

```text
DeepSeek provider smoke test passed or explicitly skipped due to missing key
DeepSeek suggestions are evidence-linked or safely ignored
Review Judge dry-run report generated
apply-guarded does not apply unsafe decisions
llm_auto_accepted_count = 0
badcase_violations = 0
secret_leaks = 0
```

### 18.3 Phase F 验收

```text
production shadow dataset manifest exists
blind split exists
blind-set eval report exists
blind-set average_recall >= 0.85 才可宣称 0.85 泛化达标
若 blind-set average_recall < 0.85，则必须列出 top gaps 和下一轮计划
```

---

## 19. 最终交接说明模板

Codex 完成后，在 `docs/phase_d_e_f_deepseek_review_subagent_handoff.md` 中写：

```markdown
# Phase D/E/F Handoff

## Summary

- Dataset size:
- Phase D average recall:
- Phase D strict pass:
- Policy recall:
- Meeting recall:
- General recall:
- Required missing:
- Review required:
- Badcase violations:
- LLM auto accepted:
- Package verification:
- Secret leaks:

## DeepSeek Result

- configured:
- provider smoke:
- suggestions:
- evidence-linked suggestions:
- measurable contribution:
- failure modes:

## Review Judge Result

- pending reviewed:
- approve suggestions:
- reject suggestions:
- keep pending:
- applied approve:
- applied reject:
- unsafe skipped:
- reviewer_type:

## 0.85 Status

- 50-sample score:
- blind-set score:
- can claim 0.85:
- if not, why:

## Remaining Gaps

- policy_doc:
- meeting_doc:
- general_doc:

## Safety

- badcase:
- LLM auto accepted:
- secret redaction:
- old snapshots:
- knowledge pack scope:

## Commands

...
```

---

## 20. 最终评价口径

如果 Phase D 达成但 Phase F 没有 blind 0.85：

```text
当前系统已显著提升 50 样本语义映射质量，并完成 DeepSeek + Review Judge 安全闭环；
但尚不能宣称“任意生产 UIR 0.85+”，因为缺少生产 blind-set 证明或 blind-set 指标未达 0.85。
```

如果 Phase F blind-set 达到 0.85：

```text
当前系统在通过 UIR Quality Gate 的生产 blind set 上达到 average recall >= 0.85，
且 auto accepted precision、badcase、LLM auto accepted、package verification、secret redaction 均满足门禁。
可以声明“对有效生产 UIR，在已支持 schema family 内达到 0.85+ 语义映射质量”。
```

---

## 21. 优先级执行顺序

严格按以下顺序执行：

```text
1. 保护 secrets，确认 DeepSeek 配置方式
2. 跑当前基线
3. 实现 UIR Quality Gate
4. 实现字段级 extractor registry
5. 硬化 policy_doc
6. 硬化 meeting_doc
7. 修 general_doc ranking
8. 实现 conditional template + evidence ranking
9. 实现 Review Judge Sub-Agent dry-run
10. 接入 DeepSeek provider smoke test
11. 跑 DeepSeek ablation
12. apply-guarded 只处理安全 review
13. 生成 scoped knowledge draft + impact preview
14. 跑 Phase D evaluator
15. 建 production shadow / blind set
16. 跑 blind-set evaluator
17. 生成 handoff
18. 运行 verify_all
19. 做 secret audit
20. 提交 PR
```

---

## 22. 给 Codex 的最终一句话

本轮的最高优先级不是“让 LLM 自动替我们做决定”，而是：

```text
把 DeepSeek 变成可测量、可审计、不会越权的候选/审查辅助；
把 Review Judge 子智能体变成安全的人审模拟器；
把字段级 extractor、conditional template、evidence ranking、quality gate 和 blind-set evaluation 建起来；
最终用生产 blind set 证明 0.85，而不是在本地样本上自我证明。
```
