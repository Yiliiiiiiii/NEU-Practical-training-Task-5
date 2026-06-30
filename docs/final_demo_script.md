# SchemaPack Agent Final Demo Script

This script is written for reviewers running commands from `F:\p2` in
PowerShell. It demonstrates the current verified path from real procurement UIR
input to schema-governed, verifier-checked package output.

## 1. Run The Unified Verification Gate

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected current baseline:

- backend pytest: 202 passed;
- Ruff: clean;
- frontend production build: successful;
- OpenAPI export: 32 paths written to `docs\openapi.json`.

## 2. Start Backend And Frontend

Terminal A, from `F:\p2`:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal B, from `F:\p2`:

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

Open:

```text
http://127.0.0.1:5173/
```

The Docker Compose alternative is also runnable from `F:\p2`:

```powershell
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8080/
```

## 3. Import A Real Procurement UIR

Terminal C, from `F:\p2`:

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

In the UI, the same step is: choose/import the real procurement UIR, then confirm
the imported document appears in the workbench.

## 4. Create And Execute A Procurement Task

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

In the UI, create a task with `procurement_doc` and
`procurement_doc_base_v1`, then click `Execute`.

## 5. Inspect Evidence And Package Output

Mapping evidence:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
```

Validation:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
```

Content organization:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

Package metadata and ZIP:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package"

Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "reports\demo_standard_package.zip"
```

Explain to reviewers that package verification proves structural integrity,
manifest hashes, required artifacts, JSON/JSONL parseability, Markdown presence,
and traceability. It does not mean every target field passed strict semantic
validation.

## 6. Demonstrate Review To Knowledge-Pack Activation

If the task produced review-required rows, inspect pending reviews:

```powershell
$pending = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
$pending.items | Select-Object -First 3
```

Approve one reviewed item when the evidence is acceptable:

```powershell
$reviewId = $pending.items[0].review_id
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/reviews/$reviewId/approve"
```

Accept a resulting candidate and create an active pack:

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

Explain that review decisions are human-gated, active packs affect future task
resolution, and old task snapshots remain immutable.

## 7. Show The Four Deepening Reports

Open the committed report evidence:

```powershell
Get-Content reports\real_world_mapping_eval_report.md -Encoding UTF8
Get-Content reports\procurement_doc_eval_report.md -Encoding UTF8
Get-Content reports\content_organization_retrieval_eval.md -Encoding UTF8
Get-Content reports\knowledge_loop_eval_report.md -Encoding UTF8
```

Useful current talking points:

- real-world mapping uses 16 source-backed UIR documents and records zero
  badcase violations;
- procurement required coverage is 1.000 versus 0.333 for the generic schema;
- content retrieval uses 32 queries and records `Recall@3 = 1.000`;
- the knowledge-loop report preserves old snapshots and records zero badcase
  violations.

## 8. Explain Strict-Validation And Production Boundaries

State these boundaries explicitly:

- current production input is UIR; raw PDF, Word, Excel, image, scan, and OCR
  parsing are outside the runtime boundary;
- real-world package generation is 16/16 for import, execution, and package
  verification;
- strict semantic validation currently passes for the five procurement samples;
- the other 11 real-world samples remain review-required and are not claimed as
  field-valid;
- optional LLM fallback is disabled by default, review-only, and never
  auto-accepts mappings;
- retrieval evidence is deterministic chunk-ranking evidence, not a full RAG or
  vector-search service;
- enterprise SSO, tenant management, TLS termination, managed secrets, model
  monitoring, and model training are outside the implemented boundary.
