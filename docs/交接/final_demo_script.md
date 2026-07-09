# SchemaPack Agent 最终 Demo 脚本

本脚本面向在 `F:\p2` 中使用 PowerShell 的评审者，优先演示课题 5 标准输入输出：UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config -> schema-governed、verifier-checked package output。

## 0. Topic 5 标准接口与 no-code SchemaPack 演示

演示顺序：

1. 展示任务书课题 5 输入输出。
2. 展示 Topic 5 标准接口请求体：UIR + Schema + Rules + ContentConfig。
3. 运行 announcement_doc inline convert。
4. 展示 mapping_report：字段映射、置信度、证据、review_required。
5. 展示 validation_report：类型/必填/值域定位。
6. 展示 content.json、content.md、chunks.jsonl。
7. 展示 manifest 和 verifier_report。
8. 最后补充：已有 5 类 SchemaPack 是示例配置；External UIR、Review、Lineage 是增强能力。

```powershell
backend\.venv\Scripts\python.exe scripts\run_topic5_inline_convert.py `
  --request examples\topic5_inline\announcement_convert_request.json `
  --out reports\topic5_inline_announcement_result.json `
  --create-package

backend\.venv\Scripts\python.exe scripts\check_topic5_alignment_gate.py
```

SchemaPack 只是示例配置与评测基准，不是系统能力边界。

## 0.1 Basic-stage Evidence Pack

先运行基本阶段一键复现：

```powershell
.\scripts\run_basic_stage_verification.ps1
```

演示口径：

1. 展示 UIR / External UIR 输入。
2. 展示 mapping report 中的 confidence、review-required、evidence、badcase safety。
3. 展示 DeepSeek suggestion report：report-only，不自动接受，不写规则。
4. 展示 Codex review subagent dry-run：`applied_count = 0`。
5. 展示 package consistency：JSON + Markdown + manifest + checksum + downstream parseability。
6. 展示 [`evidence/basic_stage/final/basic_stage_acceptance_matrix.md`](evidence/basic_stage/final/basic_stage_acceptance_matrix.md)：`passed` 与 `partial` 分开说明。

当前基本阶段 mapping gate 为 `partial`：dev/test/blind assisted recall 分别为 `0.798`、`0.794`、`0.826`，不能宣称 0.85 已达成。

## 0.2 Strengthen-stage Evidence Pack

运行强化阶段一键复现：

```powershell
.\scripts\run_strengthen_stage_verification.ps1
```

演示口径：

1. 展示 `docs/交接/evidence/strengthen_stage/mapping/splits/summary.md`：dev/test/blind assisted recall 分别为 `0.868`、`0.868`、`0.884`，mapping quality gate passed。
2. 展示 `docs/交接/evidence/strengthen_stage/llm/deepseek_mapping_live_eval_report.md`：DeepSeek live report-only 15 requests，LLM auto accepted 0；unsafe suggestions 只进入报告。
3. 展示 `docs/交接/evidence/strengthen_stage/review/codex_review_subagent_live_report.md`：dry-run，reviewed_items 48，applied_count 0，production_write_count 0。
4. 展示 `docs/交接/evidence/strengthen_stage/operation/`：field operation accuracy 1.000，schema localization rate 1.000。
5. 展示 `docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md`：final conclusion 为 `conditional_pass`。

答辩时必须说明：当前不是生产级盲测达标；review-required rate `0.109` 高于 0.08 目标，content quality 仍 partial，Codex review 不能宣称 live subagent。

## 1. 运行统一验证 Gate

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

当前期望基线：

- backend pytest：通过；
- Ruff：clean；
- frontend production build：successful；
- OpenAPI export：63 paths 写入 `docs\openapi.json`。

## 2. 启动 Backend 与 Frontend

推荐方式：

```powershell
.\scripts\start_dev.ps1
```

手动方式，Terminal A：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal B：

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

打开：

```text
http://127.0.0.1:5173/
```

Docker Compose 备用方式：

```powershell
docker compose up --build
```

然后打开：

```text
http://127.0.0.1:8080/
```

## 3. 导入真实采购 UIR

Terminal C：

```powershell
$uirPath = "examples\real_world\uir\procurement\real_procurement_001_broadcast_security_supervision.json"
$uir = Get-Content $uirPath -Raw -Encoding UTF8 | ConvertFrom-Json
$body = @{ uir = $uir } | ConvertTo-Json -Depth 100

$document = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/documents/import `
  -ContentType "application/json" `
  -Body $body

$document.doc_id
```

UI 中的同等步骤：导入真实 procurement UIR，并确认 imported document 出现在工作台中。

## 4. 创建并执行 Procurement Task

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "procurement_doc"
  schema_version = "1.0.0"
  template_id = "procurement_doc_base_v1"
  template_version = "1.0.0"
  options = @{
    content_organization = @{
      chunk_strategy = "heading_aware"
      target_tokens = 768
      min_tokens = 128
      max_tokens = 1024
      overlap_tokens = 80
      protect_tables = $true
      protect_lists = $true
      protect_code_blocks = $true
      enable_parent_child = $false
      enable_light_semantic_boundary = $true
      summary_mode = "deterministic"
      keyword_mode = "deterministic"
    }
  }
} | ConvertTo-Json -Depth 30

$task = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/tasks `
  -ContentType "application/json" `
  -Body $taskBody

$result = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/execute"

$result.status
```

UI 中选择 `procurement_doc` 与 `procurement_doc_base_v1`，然后点击“执行”。

## 5. 查看 Evidence 与 Package Output

Mapping evidence：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
```

Validation：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
```

Content organization：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

Package metadata 与 ZIP：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package"

Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "reports\demo_standard_package.zip"
```

向评审者说明：package verification 证明 structural integrity、manifest hashes、required artifacts、JSON/JSONL parseability、Markdown presence 和 traceability；它不代表每个 target field 都通过 strict semantic validation。

## 6. 演示 Review 到 Knowledge-Pack Activation

如果 task 产生 review-required rows，查看 pending reviews：

```powershell
$pending = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
$pending.items | Select-Object -First 3
```

当 evidence 可接受时 approve 一个 review item：

```powershell
$reviewId = $pending.items[0].review_id
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/reviews/$reviewId/approve"
```

接受生成的 candidate 并创建 active pack：

```powershell
$candidates = Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/candidates
$candidateId = $candidates.items[0].candidate_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/candidates/$candidateId/accept"

$packBody = @{
  schema_id = "procurement_doc"
  template_id = "procurement_doc_base_v1"
  name = "demo procurement aliases"
  created_by = "demo_user"
} | ConvertTo-Json -Depth 5

$pack = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/knowledge/packs `
  -ContentType "application/json" `
  -Body $packBody

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/packs/$($pack.pack_id)/activate"

Invoke-RestMethod "http://127.0.0.1:8000/api/v1/knowledge/effective-template?schema_id=procurement_doc&template_id=procurement_doc_base_v1"
```

说明：review decisions 是 human-gated；active packs 影响 future task resolution；old task snapshots 保持 immutable。

## 7. 展示深化报告

打开已提交报告：

```powershell
Get-Content reports\real_world_mapping_eval_report.md -Encoding UTF8
Get-Content reports\procurement_doc_eval_report.md -Encoding UTF8
Get-Content reports\content_organization_retrieval_eval.md -Encoding UTF8
Get-Content reports\knowledge_loop_eval_report.md -Encoding UTF8
Get-Content reports\non_procurement_acceptance_report.md -Encoding UTF8
```

可讲解要点：

- real-world mapping 记录 zero badcase violations；
- procurement required coverage 优于 generic schema；
- content retrieval 记录 `Recall@3 = 1.000`；
- knowledge-loop report 保持 old snapshots，并记录 zero badcase violations；
- non-procurement 深化 gate 已通过：average recall `0.5678`、review-required 69、required missing 6、badcase violations 0。

## 8. 说明 Strict-Validation 与 Production Boundaries

明确说明：

- 当前 production input 是 UIR；raw PDF、Word、Excel、image、scan 和 OCR parsing 在 runtime boundary 之外；
- real-world package generation 已覆盖 60/60 import、execution 与 package verification；
- strict semantic validation 与 package verification 是不同概念；
- 非采购样本仍需持续减少 review-required 和 missing fields；
- optional LLM fallback 默认关闭、仅 Review、不会 auto-accept mappings；
- retrieval evidence 是 deterministic chunk-ranking evidence，不是 full RAG 或 vector-search service；
- enterprise SSO、tenant management、TLS termination、managed secrets、model monitoring 和 model training 不在当前实现边界内。

## 9. 展示 Downstream Consumption

1. 打开 **下游就绪度** 面板，展示 CSV、RAG 和 contract status。
2. 对 ZIP 或 package directory 运行 `export_structured_csv.py`。
3. 运行 `export_rag_corpus.py --granularity child`。
4. 展示 `downstream_contract_eval_report` 中 45/45 packages 和 0 failures 的结果；同时说明 real-world pipeline 当前 package verification 为 60/60。
## External UIR Adapter Segment

Show the External UIR Adapter API/UI MVP:

1. Paste the topic11 External UIR JSON fixture.
2. Click `Convert & Preview`.
3. Review the standard UIR preview, adapter trace, and route recommendation.
4. Confirm the recommended `procurement_doc / procurement_doc_base_v1` route.
5. Click `Import Standard UIR`.
6. Click `Create Task`.
7. Execute with the existing task pipeline and package flow.

## 10. 展示成熟化平台能力

1. 在 `Schema Draft Lab` 中从样本发现字段、生成并校验 draft，说明不会自动激活。
2. 在 `Review Workbench` 中展示分组、影响预览、批量安全和负知识。
3. 展示 Knowledge Pack conflict、diff、impact 与 rollback。
4. 在 `Evaluation Center` 中展示 dataset、run、metric、scorecard 和 8/8 gates。
5. 展示质量打磨后的当前非采购语义评测结果：non-procurement 50 samples，
   average recall `0.8063730159`，strict pass 47/50，review-required 16，
   required missing 2，package verification 50/50，badcase violations 0；
   Adapter fixtures `4 -> 18`，trace coverage 与 router top-1 accuracy 均为 `1.0`。
6. 强调 package verification 只证明结构完整、hash/manifest/JSON/JSONL
   可解析和 traceability，不代表每个字段都通过 strict semantic validation。
7. 用统一 CLI 或 Python SDK 完成一次集成调用，并用版本化 consumer contract
   校验成果包。
8. 展示可选 raw-upstream 样例，说明其是离线入口，不是 OCR 或生产上传 API。
9. 明确说明当前不能宣称 production blind recall 0.85：blind/shadow reports 为
   `not_run`，原因是缺少独立 production shadow/blind gold corpus。

## 11. 展示 SchemaPack-Lineage

1. 执行一个已导入的 Standard/External UIR task，确认产生
   `lineage_graph.json` 与 `lineage_summary.json` task reports。
2. 在“可信链路”中选择 `title` 或当前文档代表字段，展示 upstream path。
3. 选择一个 chunk，展示 source blocks；选择 `content.json` 或
   `chunks.jsonl`，展示 manifest hash、role 与 consumer contract。
4. 展示 review-required、badcase-blocked、knowledge 和
   `source_not_present` 状态文字。
5. 打开 Evaluation Center，确认 lineage parse/edge/secret/coverage gates
   通过。
6. 说明 lineage 不改变 mapping，不让 LLM 自动接受，也不等于 strict semantic
   correctness。
