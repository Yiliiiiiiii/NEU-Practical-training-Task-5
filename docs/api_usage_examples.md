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

## 10. Maturity Platform APIs

The synchronized OpenAPI surface also includes:

```text
POST /api/v1/schema-drafts/discover
POST /api/v1/schema-drafts/generate
GET  /api/v1/schema-drafts/{draft_id}
POST /api/v1/schema-drafts/{draft_id}/validate
POST /api/v1/schema-drafts/{draft_id}/export

GET  /api/v1/reviews/summary
GET  /api/v1/reviews/grouped
POST /api/v1/reviews/{review_id}/impact-preview
POST /api/v1/reviews/batch-approve
POST /api/v1/reviews/batch-reject

GET  /api/v1/knowledge/conflicts
GET  /api/v1/knowledge/packs/{pack_id}/diff
GET  /api/v1/knowledge/packs/{pack_id}/impact
POST /api/v1/knowledge/packs/{pack_id}/rollback

GET  /api/v1/evaluation-center/datasets
POST /api/v1/evaluation-center/run
GET  /api/v1/evaluation-center/runs
GET  /api/v1/evaluation-center/metrics
GET  /api/v1/evaluation-center/scorecard
```

Draft generation, review decisions, knowledge activation/rollback, and
evaluation runs are separate explicit operations. No endpoint in this group
auto-activates an LLM suggestion.

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

## Downstream Adapters

```powershell
backend\.venv\Scripts\python.exe scripts\export_structured_csv.py --package standard_package.zip --out reports\exports\content.csv
backend\.venv\Scripts\python.exe scripts\export_rag_corpus.py --package standard_package.zip --out reports\exports\rag.jsonl --granularity all
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --package standard_package.zip
```

These are offline consumers of the existing package contract; they do not add a
vector database or RAG runtime API.

## External UIR Adapter CLI

External UIR conversion is available through both the legacy offline CLI and
the `/api/v1/external-uir/*` API/UI workflow. The legacy CLI converts upstream
UIR dialect JSON into the standard `UIRDocument` contract:

```powershell
backend\.venv\Scripts\python.exe scripts\convert_external_uir.py `
  --input examples\external_uir\dialect_a_block_list\sample_procurement_external.json `
  --source-system topic11 `
  --out examples\external_uir\converted\sample_procurement_standard_uir.json `
  --report reports\external_uir_adapter\sample_procurement_adapter_report.json `
  --route-schema `
  --route-report reports\external_uir_adapter\sample_procurement_route_report.json
```

Batch evaluation:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md
```

The CLI does not create tasks, activate schema/template drafts, or accept LLM
mapping suggestions automatically.

## Unified CLI And Python SDK

The unified CLI calls the public HTTP API and can compose the full External UIR
to Package workflow. `convert-external --out` writes only the standard UIR so it
can be passed directly to `import`; the terminal response still includes route
and adapter reports.

```powershell
$env:SCHEMAPACK_BASE_URL = "http://127.0.0.1:8000"
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py list-adapters
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py list-schemas
```

SDK example:

```python
from schemapack_client import SchemaPackClient

with SchemaPackClient("http://127.0.0.1:8000") as client:
    imported = client.import_uir(standard_uir)
    task = client.create_task(
        imported["doc_id"],
        "policy_doc",
        "policy_doc_base_v1",
    )
    client.execute_task(task["task_id"])
    client.download_package(task["task_id"], "standard_package.zip")
```

When authentication is enabled, pass the SDK `api_key` argument or set
`SCHEMAPACK_API_KEY` for the CLI. Do not place keys in command output, fixtures,
reports, or adapter manifests.

## Optional Raw Document Upstream Handoff

Generate reviewable External UIR offline:

```powershell
python scripts\upstream_unstructured_to_external_uir.py `
  input.pdf `
  --out external.json `
  --report upstream_report.json
```

Then use the public API through the unified CLI. `--base-url` is a global option
and must appear before the command:

```powershell
python scripts\schemapack_cli.py --base-url http://127.0.0.1:8000 `
  convert-external --input external.json --out standard_uir.json `
  --source-system raw_upstream --route
python scripts\schemapack_cli.py --base-url http://127.0.0.1:8000 `
  import --input standard_uir.json --out imported.json
```

Review the conversion and route reports before explicitly calling
`create-task`. Raw-document tooling never imports a document, creates a task,
executes a task, or accepts an LLM suggestion by itself.

## External UIR API

Convert upstream External UIR JSON without persisting a document:

```powershell
$external = Get-Content examples\external_uir\dialect_a_block_list\sample_procurement_external.json -Raw | ConvertFrom-Json
$body = @{
  payload = $external
  source_system = "topic11"
  dialect_hint = "auto"
  route_schema = $true
  allow_llm = $false
} | ConvertTo-Json -Depth 100

$result = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/external-uir/convert `
  -ContentType "application/json" `
  -Body $body

$result.route_report
```

Request DeepSeek suggestions without auto-accepting mappings:

```powershell
$body = @{
  payload = $external
  source_system = "topic11"
  dialect_hint = "auto"
  route_schema = $true
  allow_llm = $true
  llm_mode = "deepseek"
} | ConvertTo-Json -Depth 100
```

`allow_llm=true` only requests suggestions in the adapter report. It does not
create mappings, activate schemas/templates, create tasks, or execute tasks.

## SchemaPack-Lineage API

```powershell
$taskId = "task_xxx"

# Full graph and summary
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$taskId/lineage"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$taskId/lineage/summary"

# Bounded upstream field path
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/tasks/$taskId/lineage/fields/title?direction=upstream&max_depth=8"

# Chunk source path
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/tasks/$taskId/lineage/chunks/chunk_1?direction=upstream&max_depth=8"

# Artifact path (URL encode nested paths)
$artifact = [uri]::EscapeDataString("content.json")
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/tasks/$taskId/lineage/artifacts/$artifact?direction=both&max_depth=8"
```

Create an External UIR task with trace preservation by passing the
`adapter_report` returned by `/external-uir/convert` or `/external-uir/import`
to `/external-uir/create-task`. The web workbench does this automatically.
