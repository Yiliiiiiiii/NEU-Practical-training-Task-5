# API Usage Examples

These examples assume the backend is running at `http://127.0.0.1:8000`.
They intentionally show representative workflows from the current 32-path
OpenAPI surface instead of duplicating every operation in
[`docs/openapi.json`](openapi.json).

If API-key authentication is enabled, add:

```powershell
$headers = @{ "X-API-Key" = "your-dev-key" }
```

and pass `-Headers $headers` to `/api/v1/*` calls. `/health` remains anonymous.

## 1. Health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 2. Schema And Template Catalogs

Read catalog summaries:

```powershell
$schemas = Invoke-RestMethod http://127.0.0.1:8000/api/v1/schemas
$templates = Invoke-RestMethod http://127.0.0.1:8000/api/v1/templates
```

Read one schema and one template:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/schemas/procurement_doc
Invoke-RestMethod http://127.0.0.1:8000/api/v1/templates/procurement_doc_base_v1
```

Activation examples:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/schemas/procurement_doc/versions/1.0.0/activate

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/templates/procurement_doc_base_v1/versions/1.0.0/activate
```

Archive examples are lifecycle operations for versions that should no longer be
used by new tasks. Do not run them against the schema or template version used
later in this walkthrough:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/schemas/example_schema/versions/0.9.0/archive

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/templates/example_template/versions/0.9.0/archive
```

Archived or referenced versions may be rejected by governance protections.

## 3. Import A UIR Document

```powershell
$uir = Get-Content examples\real_world\uir\procurement\real_procurement_001_broadcast_security_supervision.json -Raw | ConvertFrom-Json
$body = @{ uir = $uir } | ConvertTo-Json -Depth 100

$document = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/documents/import `
  -ContentType "application/json" `
  -Body $body

$document.doc_id
```

List and read imported documents:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/documents
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/documents/$($document.doc_id)"
```

## 4. Create And Execute A Task

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

Task lookup:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/tasks
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)"
```

To request safe LLM fallback suggestions, keep them review-required:

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "procurement_doc"
  template_id = "procurement_doc_base_v1"
  options = @{
    enable_llm_fallback = $true
    strict_llm = $false
  }
} | ConvertTo-Json -Depth 10
```

Do not send `llm_api_key` in task options. Credentials are deployment
configuration and secret-looking values are redacted before persistence.

## 5. Reports And Package Retrieval

Representative task reports:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

Package metadata and download:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package"

Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "standard_package.zip"
```

The ZIP contains `metadata.json`, `manifest.json`, `content.json`,
`content.md`, `chunks.jsonl`, task reports, and verifier output. See
[`docs/package_spec.md`](package_spec.md) for required roles, media types, and
strict verification rules.

## 6. Review Approval And Rejection

```powershell
$pending = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
$reviewToApprove = $pending.items[0].review_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/reviews/$reviewToApprove/approve"

$reviewToReject = "another-review-id"
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/reviews/$reviewToReject/reject"
```

Use approve or reject according to the actual operator decision.

## 7. Knowledge Candidates And Pack Activation

```powershell
$candidates = Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/candidates
$candidateId = $candidates.items[0].candidate_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/candidates/$candidateId/accept"

$packBody = @{
  schema_id = "procurement_doc"
  template_id = "procurement_doc_base_v1"
  name = "procurement aliases from review"
  created_by = "demo_user"
} | ConvertTo-Json -Depth 5

$pack = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/knowledge/packs `
  -ContentType "application/json" `
  -Body $packBody

$packId = $pack.pack_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/packs/$packId/activate"

Invoke-RestMethod "http://127.0.0.1:8000/api/v1/knowledge/effective-template?schema_id=procurement_doc&template_id=procurement_doc_base_v1"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/metrics
```

Candidate rejection and pack archival are separate lifecycle examples for
records that should not become active knowledge:

```powershell
$candidateToReject = "another-candidate-id"
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/candidates/$candidateToReject/reject"

$packToArchive = "another-pack-id"
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/packs/$packToArchive/archive"
```

## 8. Evaluation Report Reads

Evaluation reports are read by report id:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/evaluation-reports/real-world-knowledge-loop
Invoke-RestMethod http://127.0.0.1:8000/api/v1/evaluation-reports/chunk-retrieval
Invoke-RestMethod http://127.0.0.1:8000/api/v1/evaluation-reports/llm-fallback
```

## 9. Audit Log Reads

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/audit-logs?entity_id=$($task.task_id)"
```

Audit entries are intentionally small. They should identify operations and
artifact references without logging API keys, LLM keys, full UIR payloads, or
package contents.

## Downstream Package Smoke Commands

After downloading or generating a package ZIP:

```powershell
backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py `
  --package standard_package.zip `
  --query "procurement supplier amount"

backend\.venv\Scripts\python.exe scripts\export_training_corpus.py `
  --package standard_package.zip `
  --out reports\training_corpus.jsonl `
  --granularity child
```
