# SchemaPack Agent 三项质量打磨执行文档

> 交给 Codex 执行。  
> 聚焦三个方向：提升 strict validation、扩充 Adapter fixtures、打磨 Evaluation Center 展示。  
> 原则：不再盲目扩功能，而是把当前平台型原型做得更稳定、更可信、更好展示。

---

## 0. 当前基线与本轮目标

### 0.1 当前项目基线

当前项目已经不是单纯的格式转换 demo，而是具备平台化雏形的 Schema 化治理系统。当前已验证能力包括：

- Backend：491 tests passed。
- Ruff：clean。
- Frontend：15 tests passed，production build successful。
- OpenAPI：58 paths。
- Regression gates：4/4 passed。
- Real-world UIR：45 documents，45/45 import、execute、package verify。
- Real-world mapping：recall `0.5672514619883041`，validation pass `27/45`，badcase violations `0`。
- Non-procurement：35 documents，average recall `0.5677551020408163`，package verify `35/35`，strict pass `13/35`，review-required `69`，required missing `6`，badcase violations `0`。
- Adapter Framework：2 adapters、4 fixtures，selection / validation / router / trace coverage 均为 1.0。
- Evaluation Center：已有 dataset/run/metric/scorecard API 与 regression gates。

### 0.2 本轮目标

本轮只做三件事：

```text
1. 提升 strict validation
2. 扩充 Adapter fixtures
3. 打磨 Evaluation Center 展示
```

不要继续堆新方向，不要新增 OCR、完整 RAG、模型训练、生产级多租户、Webhook 或企业级权限。

### 0.3 总体验收目标

| 指标 | 当前参考 | 本轮目标 |
|---|---:|---:|
| Backend tests | 491 passed | 不下降，新增测试通过 |
| Ruff | clean | clean |
| Frontend tests | 15 passed | 不下降，新增测试通过 |
| Frontend build | successful | successful |
| OpenAPI paths | 58 | 无 API 变更则保持；有变更必须重新导出 |
| Real-world package verification | 45/45 | 45/45 |
| Real-world badcase violations | 0 | 0 |
| LLM auto accepted | 0 | 0 |
| Non-procurement strict pass | 13/35 | 保守目标 ≥16/35，理想目标 ≥18/35 |
| Required missing | 6 | ≤4，最低要求不增加 |
| Review-required | 69 | ≤60，最低要求不增加 |
| Adapter fixtures | 4 | ≥12 |
| Adapter trace coverage | 1.0 | ≥0.95，理想 1.0 |
| Adapter router top-1 accuracy | 1.0 on 4 fixtures | ≥0.85 on expanded fixtures |
| Evaluation Center regression gates | 4/4 | 4/4 |
| Downstream contract pass | 1.0 | 1.0 |

如果某指标无法达到，必须输出原因分析，不得删除失败样本、降低 required 字段、关闭 badcase 或伪造报告。

---

## 1. 禁止事项

本轮严禁以下行为：

```text
1. 删除 required fields 来提升 strict pass。
2. 把 required 改 optional 来掩盖缺口。
3. 用默认值填充真实语义字段来通过 validation。
4. 把 retrieved_at 当 publish_date/effective_date。
5. 把 成文日期 当 publish_date。
6. 把 发布日期 当 effective_date。
7. 把 主持人/联系人 当 attendees。
8. 把 预算金额/控制价 当 award_amount。
9. 关闭 badcase filter。
10. 将 DeepSeek/LLM suggestion 自动 accepted。
11. 让 Schema/Template Draft 自动注册或自动 active。
12. 放宽 backend/app/schemas/uir.py 来容纳任意外部 JSON。
13. 把 Optional Raw Upstream 做成生产 API。
14. 把 package verification 宣称为字段语义全部正确。
```

安全优先级：

```text
badcase safety > traceability > reproducibility > strict pass > UI aesthetics
```

---

# Phase A：建立本轮基线

## A.1 必跑命令

从仓库根目录执行：

```powershell
git branch --show-current
git status --short

backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
npm run build
Pop-Location

backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

若需要 API-backed evaluator，另开终端启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

再运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

## A.2 输出基线报告

新增：

```text
reports/quality_polish_baseline.json
reports/quality_polish_baseline.md
```

`quality_polish_baseline.json` 至少包含：

```json
{
  "timestamp": "...",
  "git_branch": "...",
  "backend_tests": 491,
  "frontend_tests": 15,
  "openapi_paths": 58,
  "real_world": {
    "dataset_size": 45,
    "package_verify": "45/45",
    "validation_pass": "27/45",
    "mapping_recall": 0.5672514619883041,
    "badcase_violations": 0
  },
  "non_procurement": {
    "dataset_size": 35,
    "strict_pass": "13/35",
    "average_recall": 0.5677551020408163,
    "review_required": 69,
    "required_missing": 6,
    "badcase_violations": 0
  },
  "adapter": {
    "fixture_count": 4,
    "trace_coverage": 1.0,
    "router_top1_accuracy": 1.0,
    "llm_auto_accepted": 0
  },
  "regression_gates": {
    "passed": 4,
    "total": 4
  }
}
```

---

# Phase B：提升 strict validation

## B.1 目标

当前 real-world validation pass 为 `27/45`，non-procurement strict pass 为 `13/35`。本阶段目标是提升 meeting_doc、policy_doc 等真实文档的 strict validation。

重点：

```text
1. 定位 strict validation 失败原因。
2. 修复 candidate extraction、template alias/regex、transform/validation 中真实缺陷。
3. 保持 badcase violations = 0。
4. 保持 LLM auto accepted = 0。
5. 不通过删除 required fields 提升指标。
```

## B.2 新增 strict failure 分析脚本

新增脚本：

```text
scripts/analyze_strict_validation_failures.py
```

运行方式：

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_strict_validation_failures.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --out reports\strict_validation_gap_analysis.json `
  --markdown reports\strict_validation_gap_analysis.md
```

脚本职责：

1. 读取 real-world packages。
2. 汇总 validation pass / fail。
3. 按 doc_type 统计失败。
4. 按 target_field 统计 required missing。
5. 汇总 review-required 高频字段。
6. 识别可能的 transform/type/date/array 格式问题。
7. 明确列出不允许自动化的高风险规则。

输出 JSON 示例：

```json
{
  "summary": {
    "total_packages": 45,
    "validation_pass": 27,
    "validation_failed": 18
  },
  "by_doc_type": {
    "meeting_doc": {"total": 10, "failed": 3},
    "policy_doc": {"total": 15, "failed": 15}
  },
  "ranked_gaps": [
    {
      "doc_type": "policy_doc",
      "target_field": "issuer",
      "gap_type": "candidate_not_extracted",
      "count": 4,
      "risk": "medium",
      "suggested_action": "enhance_candidate_extraction"
    }
  ],
  "unsafe_shortcuts_rejected": [
    {
      "source_label": "成文日期",
      "target_field": "publish_date",
      "reason": "成文日期不是明确发布日期"
    }
  ]
}
```

Markdown 报告必须包含：

```text
1. 当前 strict pass 概况。
2. 失败样本列表。
3. 按 doc_type 分组统计。
4. 按字段排序的缺口。
5. 每个缺口的修复建议。
6. 拒绝的捷径规则。
7. 本轮修复优先级。
```

## B.3 Candidate Extraction 增强

优先修改：

```text
backend/app/services/candidate_service.py
```

新增或增强测试：

```text
backend/tests/test_candidate_service_strict_validation.py
backend/tests/test_candidate_service_non_procurement.py
```

### B.3.1 meeting_doc.topics

增强来源：

- heading 为“会议议题”“研究事项”“审议事项”“会议内容”“议定事项”的 section。
- 句式包含“会议研究了”“会议审议了”“会议听取了”。
- 列表项包含“关于……的事项”“研究……工作”。
- section-tree 转换后的 title path。

规则：

- 多个明确议题输出 array。
- 单段综合描述可进入 Review。
- 主持人、联系人、参会人员不得映射为 topics。

### B.3.2 meeting_doc.meeting_date

增强来源：

- `YYYY年M月D日召开`
- `会议于YYYY年M月D日`
- `第X次会议于...召开`
- metadata 中明确为 `meeting_date`、`会议日期`、`召开日期`

风险控制：

- 发布日期、成文日期、抓取日期不得自动作为 meeting_date。
- 多个日期无法判断时进入 Review。

### B.3.3 meeting_doc.meeting_number

增强来源：

- `第X次常务会议`
- `第X次会议`
- `第X号会议纪要`
- 标题中的会议编号。

风险控制：

- 政策文号、采购编号、公告编号不得映射为 meeting_number。

### B.3.4 policy_doc.issuer

增强来源：

- 明确字段：`issuer`、`issuing_body`、`发文机关`。
- 文尾落款单位。
- 正文“由X发布”“X印发”。
- 标题下方的发文机关区域。

风险控制：

- `承办单位` 不等于 `issuer`。
- `解读机构` 不等于 `issuer`。
- `发布机构` 缺少上下文时必须 review-required。
- 联合发文机关不得丢失。

### B.3.5 policy_doc.publish_date

增强来源：

- 明确“发布日期”“发布时间”“公开日期”。
- 官方网页 metadata 中明确的 publication date。

风险控制：

- `成文日期` 不自动等于 `publish_date`。
- `实施日期` 不等于 `publish_date`。
- `retrieved_at` 不等于 `publish_date`。
- 只有落款日期时进入 Review。

## B.4 Template Alias / Regex 增强

查找 template 文件位置：

```powershell
Get-ChildItem -Recurse examples -Filter "*template*.json"
Get-ChildItem -Recurse backend -Filter "*template*.json"
```

可能涉及：

```text
examples/production_like/mapping_templates/*.json
```

新增测试：

```text
backend/tests/test_strict_validation_templates.py
backend/tests/test_non_procurement_templates.py
```

规则：

```text
1. 只添加 source-backed、安全、窄范围 alias。
2. Regex 必须有正例和负例。
3. 不新增宽泛规则导致 badcase 自动接受。
4. 对高风险字段默认 review-required。
```

必须覆盖以下负例：

```text
成文日期 -> publish_date 不自动接受
发布日期 -> effective_date 不自动接受
retrieved_at -> effective_date 不自动接受
主持人 -> attendees 不自动接受
联系人 -> attendees 不自动接受
预算金额 -> award_amount 不自动接受
控制价 -> award_amount 不自动接受
```

## B.5 Transform / Validation 修复

检查：

```text
backend/app/services/transform_service.py
backend/app/services/validation_service.py
backend/app/schemas/target_schema.py
```

可修复：

- 日期格式标准化：`YYYY年M月D日` -> schema 期望格式。
- array 字段：明确单值可转一元素数组。
- 空字符串不能算 required field 有效值。
- 多值 issuer/topics 按 schema 类型处理。
- 数值字段仅在明确金额/数量时 normalize。

不可修复为：

- 通过降低 validation 标准来过关。
- 通过默认值填充语义字段。
- 通过删除 required field 过关。

## B.6 输出 strict validation 改进报告

新增：

```text
reports/strict_validation_improvement_report.json
reports/strict_validation_improvement_report.md
```

内容包含：

```text
1. 改进前 strict pass。
2. 改进后 strict pass。
3. required missing 前后变化。
4. review-required 前后变化。
5. 修改了哪些规则。
6. 哪些风险规则被拒绝。
7. badcase violations 是否仍为 0。
8. LLM auto accepted 是否仍为 0。
```

## B.7 Phase B 验收命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_candidate_service_non_procurement.py tests/test_candidate_service_strict_validation.py tests/test_non_procurement_templates.py tests/test_strict_validation_templates.py -q
.\.venv\Scripts\python.exe -m ruff check .
cd ..

backend\.venv\Scripts\python.exe scripts\analyze_strict_validation_failures.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --out reports\strict_validation_gap_analysis.json `
  --markdown reports\strict_validation_gap_analysis.md

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60
```

---

# Phase C：扩充 Adapter fixtures

## C.1 目标

将 External UIR Adapter fixtures 从 4 个扩充到至少 12 个，覆盖常见正常样本、表格、嵌套 section、缺字段、噪声字段和 badcase。

目标不是宣称“任意 UIR 都能完美适配”，而是证明 adapter framework 可扩展、可测试、可追踪。

## C.2 目录建议

建议扩展为：

```text
examples/external_uir/
  dialect_a_block_list/
    sample_procurement_external.json
    sample_policy_external.json
    sample_meeting_external.json
    sample_general_external.json
    sample_procurement_table_external.json
    sample_general_table_external.json
    sample_policy_missing_fields_external.json
    sample_general_noisy_external.json
    sample_meeting_host_not_attendees_external.json
    sample_procurement_budget_not_award_external.json
  dialect_b_section_tree/
    sample_policy_section_tree_external.json
    sample_meeting_nested_sections_external.json
    sample_general_table_sections_external.json
    sample_procurement_nested_award_external.json
    sample_policy_multi_issuer_external.json
  expected/
    adapter_expected.jsonl
    router_expected.jsonl
    trace_expected.jsonl
    badcases.jsonl
```

若现有结构不同，不要强制迁移旧文件；可兼容旧结构后新增 expected 文件。

## C.3 必须覆盖的 fixture 类型

### C.3.1 正常样本

至少覆盖：

```text
procurement_doc
policy_doc
meeting_doc
general_doc
```

要求：

- 可转换为标准 UIRDocument。
- Router 能推荐正确 schema/template。
- adapter report 有 trace。
- no secret leaks。
- llm_auto_accepted = 0。

### C.3.2 表格样本

新增：

```text
sample_procurement_table_external.json
sample_general_table_external.json
```

要求：

- 外部 UIR 包含 rows。
- 转换后保留 `attributes.rows`。
- table rows parseable。
- trace 记录 table path。

### C.3.3 嵌套 section-tree 样本

新增：

```text
sample_meeting_nested_sections_external.json
sample_policy_section_tree_external.json
```

要求：

- 顶层 `document.sections[]`。
- section 包含 heading、paragraphs、tables、children。
- 转换后保留 title path 或 section path。
- trace 能追踪 external section path。

### C.3.4 缺字段 / 噪声样本

新增：

```text
sample_policy_missing_fields_external.json
sample_general_noisy_external.json
```

要求：

- 缺少部分 metadata 时 adapter 不 crash。
- 空文本、未知字段、额外字段要产生 warning。
- router 低置信时 `review_required=true`。

### C.3.5 badcase 样本

新增：

```text
sample_meeting_host_not_attendees_external.json
sample_procurement_budget_not_award_external.json
sample_policy_written_date_not_publish_external.json
```

必须验证：

```text
预算金额 不自动成为 award_amount
控制价 不自动成为 award_amount
主持人 不自动成为 attendees
联系人 不自动成为 attendees
成文日期 不自动成为 publish_date
retrieved_at 不自动成为 effective_date
```

## C.4 expected 文件格式

### adapter_expected.jsonl

```json
{
  "fixture": "dialect_a_block_list/sample_procurement_table_external.json",
  "expected_adapter_id": "block_list",
  "expected_min_blocks": 5,
  "expected_has_tables": true,
  "expected_trace_coverage_min": 0.95,
  "expected_validation_pass": true
}
```

### router_expected.jsonl

```json
{
  "fixture": "dialect_b_section_tree/sample_meeting_nested_sections_external.json",
  "expected_schema_id": "meeting_doc",
  "expected_template_id": "meeting_doc_base_v1",
  "min_confidence": 0.5,
  "allow_review_required": true
}
```

### trace_expected.jsonl

```json
{
  "fixture": "dialect_a_block_list/sample_general_noisy_external.json",
  "required_trace_fields": [
    "external_path",
    "target_block_id",
    "conversion_rule",
    "source_value_preview"
  ],
  "min_trace_coverage": 0.95
}
```

### badcases.jsonl

```json
{
  "fixture": "dialect_a_block_list/sample_meeting_host_not_attendees_external.json",
  "source_label": "主持人",
  "forbidden_target": "attendees",
  "reason": "主持人不是完整参会人员列表"
}
```

## C.5 增强 evaluator

修改：

```text
scripts/eval_external_uir_adapter.py
scripts/eval_external_uir_api.py
```

输出指标至少包括：

```text
adapter_fixture_count
adapter_selection_accuracy
uir_validation_pass_count
trace_coverage
router_top1_accuracy
router_review_required_count
badcase_violations
llm_auto_accepted_count
secret_leaks
```

输出报告：

```text
reports/external_uir_adapter_eval_report.json
reports/external_uir_adapter_eval_report.md
reports/external_uir_api_eval_report.json
reports/external_uir_api_eval_report.md
```

## C.6 新增测试

新增或增强：

```text
backend/tests/test_external_uir_adapter_fixtures.py
backend/tests/test_external_uir_adapter_trace.py
backend/tests/test_schema_router_expanded_fixtures.py
backend/tests/test_external_uir_badcases.py
backend/tests/test_external_uir_api.py
backend/tests/test_external_uir_llm_safety.py
```

测试重点：

```text
1. 所有 fixtures 可转换。
2. 所有 expected validation pass 的 fixture 必须通过 UIRDocument validation。
3. trace coverage 达标。
4. router top-1 accuracy 达标。
5. badcases 不被自动接受。
6. DeepSeek disabled 默认不调用 provider。
7. allow_llm=true 不改变 deterministic standard_uir。
8. secret-looking values 不出现在 reports。
```

## C.7 Adapter scaffold 检查

检查：

```text
templates/adapter_plugin/
scripts/scaffold_adapter.py
```

要求：

- 生成 adapter skeleton。
- manifest 默认 `auto_register=false`。
- skeleton 包含 fixture、badcase、eval TODO。
- 未补充 deterministic conversion、trace evidence、fixtures、badcases 前不得进入 registry。

## C.8 Phase C 验收命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest `
  tests/test_external_uir_adapter_service.py `
  tests/test_external_uir_adapter_fixtures.py `
  tests/test_external_uir_adapter_trace.py `
  tests/test_schema_router_service.py `
  tests/test_schema_router_expanded_fixtures.py `
  tests/test_external_uir_badcases.py `
  tests/test_external_uir_api.py `
  tests/test_external_uir_llm_safety.py `
  -q
.\.venv\Scripts\python.exe -m ruff check .
cd ..

backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md
```

---

# Phase D：打磨 Evaluation Center 展示

## D.1 目标

让 Evaluation Center 更适合演示和验收，让老师一眼能看懂：

```text
1. 数据集有哪些。
2. 评测跑了什么。
3. 指标好坏如何。
4. Gate 有没有过。
5. 哪些模块仍需改进。
6. Package pass 不等于 strict semantic pass。
```

## D.2 后端 API 检查

确认已有：

```text
GET  /api/v1/evaluation-center/datasets
POST /api/v1/evaluation-center/run
GET  /api/v1/evaluation-center/runs
GET  /api/v1/evaluation-center/metrics
GET  /api/v1/evaluation-center/scorecard
```

若只是改 UI，不要修改 API。若修改 response model，必须运行：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
git diff -- docs/openapi.json
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

## D.3 Scorecard 数据结构

确保 scorecard 至少包含：

```json
{
  "summary": {
    "status": "passed",
    "generated_at": "...",
    "gates_passed": 4,
    "gates_total": 4
  },
  "cards": [
    {
      "name": "Package Verification",
      "value": 1.0,
      "target": 1.0,
      "status": "passed",
      "explanation": "45/45 packages passed verifier"
    },
    {
      "name": "Strict Validation",
      "value": 0.6,
      "target": 0.7,
      "status": "needs_attention",
      "explanation": "Validation pass and semantic strictness are tracked separately"
    },
    {
      "name": "Badcase Safety",
      "value": 0,
      "target": 0,
      "status": "passed",
      "explanation": "No forbidden mappings auto-accepted"
    }
  ],
  "warnings": [
    "Package verification does not imply every target field is semantically valid."
  ]
}
```

## D.4 前端展示要求

优先修改：

```text
frontend/src/App.tsx
```

如已有拆分组件，则修改对应组件：

```text
frontend/src/components/EvaluationCenter*.tsx
frontend/src/api/*.ts
```

### D.4.1 页面分区

Evaluation Center 分为四个面板：

```text
1. Dataset Registry
2. Evaluation Runs
3. Metric Scorecard
4. Regression Gates
```

#### Dataset Registry

展示：

```text
dataset id
name
type：real-world / non-procurement / adapter / production-like / downstream
document count
fixture count
last run time
report links
```

#### Evaluation Runs

展示：

```text
run id
run type
status
started_at / finished_at
duration
package pass rate
badcase violations
llm auto accepted
report JSON/Markdown link
```

#### Metric Scorecard

展示指标卡片：

```text
Package Verification
Mapping Recall
Strict Validation
Review Required
Required Missing
Badcase Safety
LLM Auto Accept
Adapter Trace Coverage
Router Accuracy
Downstream Contract
```

每个卡片包含：

```text
当前值
目标值
状态 passed / needs_attention / failed
解释说明
```

#### Regression Gates

展示：

```text
gate name
metric
operator
threshold
current value
status
failure reason
```

必须突出：

```text
badcase violations = 0
LLM auto accepted = 0
package verification rate = 1.0
adapter trace coverage >= threshold
```

### D.4.2 必须显示的说明

在页面顶部或底部加入固定说明：

```text
Package verification 证明成果包结构、manifest、hash、JSON/JSONL 可解析和 traceability；
不代表所有 target field 都通过 strict semantic validation。
```

再加入：

```text
LLM suggestions 和 Schema Draft 均不会自动激活 production rules。
```

### D.4.3 UI 设计原则

不要做大屏炫技，保持清晰：

```text
1. 指标清楚。
2. 状态清楚。
3. 风险提示清楚。
4. 报告链接清楚。
5. 复现命令清楚。
6. 不只靠颜色区分状态，必须有文字标签。
```

## D.5 报告增强

更新或新增：

```text
reports/evaluation_center/scorecard.md
reports/evaluation_center/scorecard.json
reports/evaluation_center/regression_gate_report.md
reports/evaluation_center/current_metrics.json
```

如无现成生成脚本，新增：

```text
scripts/build_evaluation_center_scorecard.py
```

运行方式：

```powershell
backend\.venv\Scripts\python.exe scripts\build_evaluation_center_scorecard.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\scorecard.json `
  --markdown reports\evaluation_center\scorecard.md
```

Markdown 输出结构：

```markdown
# Evaluation Center Scorecard

## Summary

| Item | Value |
|---|---|
| Overall status | passed |
| Gates | 4/4 |
| Package verification | 1.0 |
| Badcase violations | 0 |
| LLM auto accepted | 0 |

## Metrics

| Metric | Current | Target | Status | Note |
|---|---:|---:|---|---|

## Regression Gates

| Gate | Current | Target | Status |
|---|---:|---:|---|

## Known Gaps

- Package verification is not semantic strict validation.
- Meeting/policy fields still require review in some real-world cases.

## Reproduction

...
```

## D.6 前端测试

新增或增强：

```text
frontend/src/__tests__/EvaluationCenter.test.tsx
```

测试：

```text
1. 能渲染 scorecard。
2. 能显示 passed / needs_attention / failed。
3. 显示 package verification != strict validation 的说明。
4. API error 时有降级提示。
5. LLM auto accepted > 0 时显示 failed。
6. Badcase violations > 0 时显示 failed。
```

命令：

```powershell
Push-Location frontend
npm.cmd test
npm run build
Pop-Location
```

---

# Phase E：最终验证与报告

## E.1 总验证命令

所有修改完成后执行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
npm run build
Pop-Location

backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

启动 backend 后运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md
```

如果 consumer contract 需要复验：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_consumer_contract.py `
  --package-root reports\real_world_packages `
  --contract contracts\package_contract_v1_1.json `
  --out reports\evaluation_center\package_contract_report.json `
  --markdown reports\evaluation_center\package_contract_report.md `
  --min-pass-rate 0.95
```

## E.2 最终输出报告

新增：

```text
reports/quality_polish_final_report.json
reports/quality_polish_final_report.md
```

必须包含：

```text
1. 本轮改动摘要。
2. strict validation 改进前后对比。
3. Adapter fixtures 扩展前后对比。
4. Evaluation Center 展示增强说明。
5. 所有 gate 结果。
6. 未解决问题。
7. 明确未做事项：OCR、完整 RAG、LLM 自动激活、raw-document production API。
```

Markdown 模板：

```markdown
# SchemaPack Agent Quality Polish Final Report

## Summary

本轮聚焦 strict validation、Adapter fixtures、Evaluation Center 展示。

## Before / After

| Metric | Before | After | Status |
|---|---:|---:|---|

## Strict Validation

...

## Adapter Fixtures

...

## Evaluation Center

...

## Safety Gates

| Gate | Result |
|---|---|

## Known Gaps

...

## Reproduction Commands

...
```

## E.3 更新文档

只更新当前状态入口和直接相关文档：

```text
docs/交接/project_status.md
README.md
docs/交接/final_handoff_status.md
docs/user_web_workbench_guide.md
docs/developer_guide.md
docs/external_uir_integration.md
docs/demo_workflow.md
docs/交接/final_demo_script.md
```

不要改写历史资料目录：

```text
docs/guildline/
docs/nbl/
docs/superpowers/
```

历史文档保留当时语境，不作为当前能力缺口清单。

---

# 2. 推荐 Commit 拆分

建议分 5 个 commit：

```text
commit 1: Add strict validation gap analyzer and quality polish baseline
commit 2: Improve strict validation for meeting and policy fields
commit 3: Expand External UIR fixtures and adapter evaluator coverage
commit 4: Polish Evaluation Center scorecard and frontend display
commit 5: Regenerate reports and update current-status documentation
```

每个 commit 都要能通过对应小测试。

---

# 3. 最终交付清单

完成后应新增或更新：

```text
reports/quality_polish_baseline.json
reports/quality_polish_baseline.md
reports/strict_validation_gap_analysis.json
reports/strict_validation_gap_analysis.md
reports/strict_validation_improvement_report.json
reports/strict_validation_improvement_report.md
reports/external_uir_adapter_eval_report.json
reports/external_uir_adapter_eval_report.md
reports/external_uir_api_eval_report.json
reports/external_uir_api_eval_report.md
reports/evaluation_center/scorecard.json
reports/evaluation_center/scorecard.md
reports/evaluation_center/regression_gate_report.json
reports/quality_polish_final_report.json
reports/quality_polish_final_report.md
```

新增或增强测试：

```text
backend/tests/test_candidate_service_strict_validation.py
backend/tests/test_strict_validation_templates.py
backend/tests/test_external_uir_adapter_fixtures.py
backend/tests/test_external_uir_adapter_trace.py
backend/tests/test_schema_router_expanded_fixtures.py
backend/tests/test_external_uir_badcases.py
frontend/src/__tests__/EvaluationCenter.test.tsx
```

最终必须通过：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
npm run build
Pop-Location
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

---

# 4. 最终汇报口径

本轮完成后，对外可以这样说明：

```text
本轮没有改变 SchemaPack Agent 的主链路，而是从三个方面增强成熟度：

第一，提升 strict validation。针对 meeting/policy 等真实文档中的语义字段，
增强候选抽取、模板规则和 transform/validation，不通过删除 required fields 或
关闭 badcase 来提升指标。

第二，扩充 Adapter fixtures。把 External UIR 从少量示例扩展为覆盖正常、表格、
嵌套、缺字段、噪声和 badcase 的 fixture suite，证明 adapter framework 具备
可扩展性和可回归测试能力。

第三，打磨 Evaluation Center。把分散的评测报告整理成 dataset、run、metric、
scorecard 和 regression gate 视图，让质量指标、风险指标和成果包契约更容易展示
和复现。
```

最后强调：

```text
Package verification 证明结构完整与可追溯；
strict validation 衡量字段语义是否满足 schema；
二者不会混为一谈。
```

---

# 5. Codex 最后提醒

如果出现以下任一情况，必须停止并修复：

```text
badcase violations > 0
LLM auto accepted > 0
package verification rate < 1.0
adapter trace coverage < 0.95
OpenAPI drift 未解释
frontend build 失败
backend tests 失败
```

宁可让歧义字段进入 Review，也不要为了指标自动接受高风险映射。
