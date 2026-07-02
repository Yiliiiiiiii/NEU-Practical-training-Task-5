# SchemaPack Agent 最终 Demo 脚本

本脚本面向在 `F:\p2` 中使用 PowerShell 的评审者，演示从真实采购 UIR input 到 schema-governed、verifier-checked package output 的当前已验证路径。

## 1. 运行统一验证 Gate

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

当前期望基线：

- backend pytest：通过；
- Ruff：clean；
- frontend production build：successful；
- OpenAPI export：32 paths 写入 `docs\openapi.json`。

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
- non-procurement recall 仍未达 Phase 1，原因是 average recall 与 review-required targets 未达标。

## 8. 说明 Strict-Validation 与 Production Boundaries

明确说明：

- 当前 production input 是 UIR；raw PDF、Word、Excel、image、scan 和 OCR parsing 在 runtime boundary 之外；
- real-world package generation 已覆盖 import、execution 与 package verification；
- strict semantic validation 与 package verification 是不同概念；
- 非采购样本仍需持续减少 review-required 和 missing fields；
- optional LLM fallback 默认关闭、仅 Review、不会 auto-accept mappings；
- retrieval evidence 是 deterministic chunk-ranking evidence，不是 full RAG 或 vector-search service；
- enterprise SSO、tenant management、TLS termination、managed secrets、model monitoring 和 model training 不在当前实现边界内。

## 9. 展示 Downstream Consumption

1. 打开 **下游就绪度** 面板，展示 CSV、RAG 和 contract status。
2. 对 ZIP 或 package directory 运行 `export_structured_csv.py`。
3. 运行 `export_rag_corpus.py --granularity child`。
4. 展示 `downstream_contract_eval_report` 中 30 packages 和 0 failures 的结果。
