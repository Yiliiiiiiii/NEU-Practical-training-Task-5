# SchemaPack Agent

SchemaPack Agent is the project for topic 5: standardizing an upstream UIR document into schema-driven output packages.

Current implementation status in this checkout: the full topic 5 follow-up
plan is implemented, including the core UIR-to-schema conversion service layer,
production-like evaluator, downstream package smoke tests, deployment profile,
optional LLM fallback adapter, enhanced frontend workbench, and
database-backed catalog/review/knowledge governance.

Implemented:

- FastAPI backend skeleton with `/health`
- Environment settings
- SQLite SQLAlchemy metadata for MVP tables
- Pydantic v2 contracts for UIR, Target Schema, Mapping Template, Mapping, Transform, Canonical Model, reports, package metadata, reviews, execution snapshots, and output profiles
- Demo examples under `examples/demo/`
- Production-like evaluation dataset under `examples/production_like/`
- Runtime-safe `StorageService` for UTF-8 JSON/text files and SHA-256
- File-backed Schema and Mapping Template services for production-like fixtures
- Database-backed schema/template catalog governance with seeded fixtures,
  CRUD-style version creation, draft/active/archived status transitions,
  referenced-version protections, and immutable task version snapshots
- Field candidate extraction service for UIR metadata, table rows, and block hints
- Deterministic Mapping service for exact, alias, regex, type, fuzzy, and
  optional LLM review suggestions, with confidence tiers, structured evidence,
  risk flags, badcase filters, and review-required reasons
- Transform service for mapped field projection, date/number normalization, enum maps, and defaults
- Canonical model builder preserving schema-aligned data and UIR source blocks
- Render service for structured JSON, Markdown, and source-linked chunks
- Configurable chunk organization service for deterministic summaries, keywords,
  content tags, management tags, quality tags, entity-tag placeholders, source
  links, protected table/list/code blocks, and optional parent-child chunks
- Validation service for schema fields and rendered artifact consistency
- Manifest, package ZIP, and package verifier services
- UIR document import, list, and detail APIs
- Conversion task create, list, detail, and explicit execute APIs
- Task execution pipeline that wires schema/template loading, mapping,
  transform, canonical build, render, validation, packaging, and task status
  updates into `POST /api/v1/tasks/{task_id}/execute`
- Production-like evaluator conversion path migrated to the real service layer
- Review, Knowledge, and Effective Template services for review-derived alias
  candidates, draft/active knowledge packs, badcase filtering, and active-pack
  template resolution
- Database-backed Review and Knowledge APIs for pending reviews, candidate
  approval/rejection, draft pack creation, active pack activation, effective
  template reads, and metrics
- Optional LLM fallback adapter layer with disabled, deterministic stub, and
  OpenAI-compatible modes; default disabled, always review-required, with
  bounded retries, per-task suggestion caps, timeout warnings, latency/hash
  metadata, safe configuration snapshots, and badcase filtering
- Schema/template catalog governance APIs and task report/package retrieval APIs
  for the UI
- Minimal React/Vite frontend workbench for import, task creation, execution,
  mapping review with evidence/risk flags, validation, content organization,
  review approval, knowledge pack activation, content organization options,
  enriched chunk preview, collapsible raw JSON reports, and package download
- Containerized deployment profile with backend/frontend Dockerfiles, Nginx
  proxying, Docker Compose volumes, and production environment defaults
- Optional API key auth, task/package audit logs, audit log API, and safe
  retention cleanup script
- Downstream package smoke scripts for ZIP/directory ingestion checks and
  training-corpus JSONL export
- OpenAPI export script and `docs/openapi.json`
- Unified local verification script and GitHub Actions CI workflow
- Demo workflow guide in `docs/demo_workflow.md`
- Final demo script, requirement mapping, badcase analysis, and API examples
  under `docs/`
- Pytest baseline for bootstrap, schemas, examples, production-like evaluation,
  storage, documents, tasks, and task execution

Topic 5 four-part deepening evidence is now included:

- Real-world mapping evaluation:
  `reports/real_world_mapping_eval_report.md`
- Procurement catalog comparison:
  `reports/procurement_doc_eval_report.md`
- Content organization retrieval evaluation:
  `reports/content_organization_retrieval_eval.md`
- Human-review knowledge-loop evaluation:
  `reports/knowledge_loop_eval_report.md`

Current reproduced highlights: 16/16 real-world packages pass verification,
procurement required coverage improves from 0.333 to 1.000 versus the generic
schema, retrieval Recall@1 is 0.500 on the lightweight evaluator, and the
knowledge-loop report preserves old task snapshots while activating one pack.

Remaining production hardening not implemented yet:

- Authorization, tenancy, SSO/TLS integration, and advanced operator controls
- Hosted credential provisioning, model evaluation, and enterprise LLM
  monitoring

## Topic 5 Follow-up Evidence (2026-06-29)

The guideline follow-up phases are recorded in deterministic reports:

- `reports/acceptance_report.{json,md}` and `docs/acceptance_report.md`
- `reports/real_world_knowledge_loop_report.{json,md}`:
  `old_snapshot_unchanged=true`, `badcase_violation_count=0`
- `reports/chunk_retrieval_eval_report.{json,md}`: four real-world retrieval
  queries across procurement, policy, and meeting samples
- `reports/llm_fallback_eval_report.{json,md}`:
  `auto_accepted_count=0`, `secret_redaction_passed=true`

Network LLM evaluation is intentionally skipped unless an operator explicitly
passes the network flag and credentials for that invocation. The production
boundary remains UIR input; raw PDF/Word/Excel/OCR parsing is outside this core
pipeline.

## Backend

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Current API slice:

```text
POST /api/v1/documents/import
GET  /api/v1/documents
GET  /api/v1/documents/{doc_id}
GET  /api/v1/schemas
POST /api/v1/schemas
GET  /api/v1/schemas/{schema_id}
POST /api/v1/schemas/{schema_id}/versions/{version}/activate
POST /api/v1/schemas/{schema_id}/versions/{version}/archive
GET  /api/v1/templates
POST /api/v1/templates
GET  /api/v1/templates/{template_id}
POST /api/v1/templates/{template_id}/versions/{version}/activate
POST /api/v1/templates/{template_id}/versions/{version}/archive
GET  /api/v1/reviews
GET  /api/v1/reviews/{review_id}
POST /api/v1/reviews/{review_id}/approve
POST /api/v1/reviews/{review_id}/reject
GET  /api/v1/knowledge/candidates
POST /api/v1/knowledge/candidates/{candidate_id}/accept
POST /api/v1/knowledge/candidates/{candidate_id}/reject
GET  /api/v1/knowledge/packs
POST /api/v1/knowledge/packs
POST /api/v1/knowledge/packs/{pack_id}/activate
POST /api/v1/knowledge/packs/{pack_id}/archive
GET  /api/v1/knowledge/effective-template
GET  /api/v1/knowledge/metrics
POST /api/v1/tasks
GET  /api/v1/tasks
GET  /api/v1/tasks/{task_id}
POST /api/v1/tasks/{task_id}/execute
GET  /api/v1/tasks/{task_id}/reports/{report_name}
GET  /api/v1/tasks/{task_id}/package
GET  /api/v1/tasks/{task_id}/package/download
GET  /api/v1/audit-logs
```

Supported task report names include `mapping`, `validation`, `transform`,
`canonical`, `content`, `chunks`, `verifier`, `content_organization`, and
`content-organization`.

Task execution resolves schema/template IDs and versions through the
database-backed catalog. File-backed examples are seeded into the catalog on
read, archived versions are rejected for new executions, and referenced task
versions are protected from archival so historical snapshots stay reproducible.

## Development Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest -q
```

Backend tests initialize isolated SQLite databases in pytest temporary
directories and override the application database dependency. They do not
require a pre-existing `backend/schemapack.db`.

Lint:

```powershell
cd backend
.\.venv\Scripts\python -m ruff check .
```

Unified verification from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

## Frontend

```powershell
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Use `npm ci` for a reproducible install from the committed
`frontend/package-lock.json`.

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. Start the
backend first, then open:

```text
http://127.0.0.1:5173/
```

See `docs/demo_workflow.md` for the complete UI and API sequence. Regenerate the
OpenAPI snapshot with:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

## Container Deployment

Build and start the local container profile:

```powershell
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8080/
```

The profile uses named volumes for `/data/storage` and `/data/db`, initializes
SQLite tables on backend startup, and keeps `LLM_MODE=disabled` by default. See
`docs/deployment.md` for reset commands and environment details.

Final delivery support documents:

- `docs/developer_guide.md`
- `docs/openapi_workflow.md`
- `docs/final_demo_script.md`
- `docs/demo_workflow.md`
- `docs/deployment.md`
- `docs/requirement_mapping.md`
- `docs/badcase_analysis.md`
- `docs/api_usage_examples.md`
- `docs/package_spec.md`

## Optional LLM Fallback

LLM fallback is disabled by default and never auto-accepts mappings. To enable
an OpenAI-compatible suggestion adapter, configure:

```text
LLM_FALLBACK_ENABLED=true
LLM_MODE=openai_compatible
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=...
LLM_MODEL=...
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=0
LLM_MAX_SUGGESTIONS_PER_TASK=20
LLM_STRICT_FAILURE=false
```

Suggestions remain `review_required`, include model/latency/hash metadata, and
are filtered by badcase protections. Request failures become mapping warnings
and human-review items by default. Set task option `strict_llm=true` only when
an LLM failure must fail the whole task. API keys are read from the environment,
never from task options, and are redacted from snapshots, reports, and audit
metadata.

## Production-like Evaluation

Run the reproducible synthetic evaluation dataset from the repository root:

```powershell
python scripts/eval_production_like.py
```

Outputs:

```text
reports/production_like_eval_report.json
reports/production_like_eval_report.md
reports/packages/
```

The dataset covers `policy_doc`, `contract_doc`, `meeting_doc`, and
`general_doc`, including base-template mapping, simulated review, knowledge-pack
activation, badcase checks, manifest checksums, Markdown rendering, structured
JSON, enriched chunks, and content organization summaries.

The evaluator also records a downstream smoke summary proving generated
packages can be opened, manifest checksums validated, and chunks consumed.

Run the downstream smoke scripts against any generated package ZIP or package
directory:

```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "鍒跺害 绠＄悊"
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl --granularity all
```

This checkout now contains the core production conversion services, including
mapping and package services. The evaluator still owns dataset loading, scoring,
phase metrics, and report writing, but conversion artifacts are generated through
the real service layer. Knowledge growth now uses Review, Knowledge, and
Effective Template services to derive draft packs, persist review records and
knowledge candidates, activate packs, and resolve effective templates while
preserving badcase protections.

## Content Organization Options

Task creation accepts optional deterministic content organization settings under
`options.content_organization`. Supported strategies are `fixed_window`,
`heading_aware`, `source_block_aware`, `table_protect`, and `parent_child`.
When omitted, the legacy render-to-chunk behavior remains compatible. When
provided, generated chunks include strategy, token estimate, character count,
quality flags, title path, source links, and optional parent-child identifiers.

## Real-world UIR Dataset

The independent `examples/real_world/` toolchain builds traceable UIR evaluation
inputs from official public HTML pages, text-layer PDFs, and optional DOCX files:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py
```

Raw downloads remain in the ignored local cache. Generated UIR files retain the
source URL, retrieval timestamp, source SHA-256, format, and extraction method.
Scanned PDFs are identified and skipped; the toolchain does not perform OCR.
See [the dataset guide](docs/real_world_uir_dataset.md) for source policy,
privacy checks, reproduction steps, and limitations.

## Project Boundaries

The production system receives UIR as input. It does not parse PDF, Word, Excel,
images, OCR outputs, or raw source files. The separate real-world dataset
toolchain performs offline example construction only; it does not expand the
production API boundary. The project does not implement full quality scoring,
full RAG, or model training.

The core development line remains:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> Zip
```

At package time, rendered chunks are enriched by `ChunkOrganizerService` before
final validation and ZIP generation.

`examples/` contains versioned development and evaluation samples. `storage/` is runtime output only and should not be used as a fixed test fixture location.

