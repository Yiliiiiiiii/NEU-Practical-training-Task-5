# API Usage Examples

These examples assume the backend is running at `http://127.0.0.1:8000`.

If API key auth is enabled, add:

```powershell
$headers = @{ "X-API-Key" = "your-dev-key" }
```

and pass `-Headers $headers` to `/api/v1/*` calls. `/health` remains anonymous.

## Health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Catalog

List schema versions:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/schemas
```

List template versions:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/templates
```

Activate a schema version:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/schemas/policy_doc/versions/1.0.0/activate
```

## Import UIR

```powershell
$uir = Get-Content examples\production_like\uir\policy\policy_001_standard.json -Raw | ConvertFrom-Json
$body = @{ uir = $uir } | ConvertTo-Json -Depth 100
$document = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/documents/import `
  -ContentType "application/json" `
  -Body $body
$document
```

## Create And Execute Task

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "policy_doc"
  schema_version = "1.0.0"
  template_id = "policy_doc_base_v1"
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
} | ConvertTo-Json -Depth 20

$task = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/tasks `
  -ContentType "application/json" `
  -Body $taskBody

$result = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/execute"

$result
```

## Read Reports

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

`mapping` rows include `strategy`, `confidence`, `confidence_tier`, `status`,
`evidence`, `evidence_text`, `risk_flags`, `badcase_filter`, and
`review_required_reason`. LLM fallback rows, when explicitly enabled, remain
`review_required` and include `llm_suggestion` in `risk_flags`. The mapping
summary includes a `warnings` list when the optional provider times out or
fails.

To request LLM fallback without changing its safe failure behavior:

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "policy_doc"
  template_id = "policy_doc_base_v1"
  options = @{
    enable_llm_fallback = $true
    strict_llm = $false
  }
} | ConvertTo-Json -Depth 5
```

Set `strict_llm=true` only when a provider error should fail the task. Do not
send `llm_api_key` in `options`; credentials are deployment configuration and
secret-looking option values are redacted before persistence.

`chunks` rows include enriched deterministic metadata such as `strategy`,
`granularity`, `parent_chunk_id`, `title_path`, `token_estimate`,
`source_block_ids`, `source_links`, `content_tags`, `management_tags`,
`quality_tags`, `quality_flags`, `summary`, and `keywords`.

## Review And Knowledge

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/candidates
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/packs
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/metrics
```

## Package

Package metadata:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package"
```

Download ZIP:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "standard_package.zip"
```

The ZIP contains `metadata.json`, `manifest.json`, `content.json`,
`content.md`, `chunks.jsonl`, reports, and verifier output. See
`docs/package_spec.md` for required roles, media types, and strict verification
rules.

Downstream exports can filter parent-child chunks:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py `
  --package standard_package.zip `
  --out reports\training_corpus.jsonl `
  --granularity child
```

## Audit Logs

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/audit-logs?entity_id=$($task.task_id)"
```
