# SchemaPack Agent

SchemaPack Agent is the project for topic 5: standardizing an upstream UIR document into schema-driven output packages.

Current implementation status: Phase 10 acceptance and productization baseline.

Implemented:

- FastAPI backend skeleton with `/health`
- Environment settings
- SQLite SQLAlchemy metadata for MVP tables
- Pydantic v2 contracts for UIR, Target Schema, Mapping Template, Mapping, Transform, Canonical Model, reports, package metadata, reviews, execution snapshots, and output profiles
- Demo examples under `examples/demo/`
- Runtime-safe `StorageService` for UTF-8 JSON/text files and SHA-256
- UIR document import, list, and detail APIs
- Conversion task create, list, and detail APIs
- Target Schema create, list, and detail APIs
- Mapping Template create, update, list, and detail APIs
- Template-to-Schema binding validation for target field references
- Field candidate extraction from UIR metadata, blocks, heading text, label-value text, and table columns
- Deterministic field mapping with exact, alias, regex-label, type, and fuzzy strategies
- Mapping report JSON generation
- Manual review API for confirming or changing field mappings
- Mock-only LLM client seam for later fallback integration
- Transform engine: rename, type_cast, date_format, enum_map, default, merge, split
- Trace service: records every transform action with before/after values
- Canonical builder: constructs unified canonical model from UIR and transformed fields
- Canonical service: orchestrates transform and canonical construction, persists results
- Content JSON renderer with stable protocol metadata and canonical field projection
- Content Markdown renderer with YAML front matter and block provenance comments
- Deterministic chunks renderer with stable chunk IDs, heading context, source backlinks, and SHA-256 hashes
- Conversion service and API orchestration for canonical construction and three-output rendering
- Render trace events and task state transitions after all outputs are written successfully
- Content validation reports for required, type, enum, range, pattern, length, and date contracts
- Cross-format consistency reports for canonical, content JSON, Markdown, and chunks
- Manifest generation with stable relative paths, bytes, media types, roles, and SHA-256 hashes excluding `manifest.json`
- Package service for validation, consistency checks, manifest verification, atomic ZIP publication, package trace events, and database records
- Package, report, trace, and ZIP download APIs
- Desktop React workbench for demo/pasted JSON import, task creation, candidate generation, mapping review, conversion, report inspection, packaging, and ZIP download
- Typed frontend API client with local CORS support and exposed package SHA-256 response evidence
- Unified API error envelope for validation, missing resources, state conflicts, review requirements, package readiness, and unexpected failures
- Atomic UTF-8 JSON/text publication with same-path concurrency protection and temporary-file cleanup
- Process-local task mutation guard for candidate generation, mapping, review, conversion, and packaging
- Recoverable render/package I/O failures with partial-output cleanup, failure traces, and deterministic retry
- Exact contract inventory for all 36 MVP API routes
- True API-driven general and policy demo pipelines through verified ZIP download
- Versioned badcases for missing required fields, invalid casts, ambiguous mappings, and broken provenance links
- Package corruption tests for manifest tampering, ZIP payload changes, unsafe paths, byte counts, and SHA-256 mismatches
- Strict backend and frontend line, branch, function, lint, and production build gates
- Independent external package verifier module and CLI
- Package verifier reports stored outside the ZIP and exposed through API
- Auditable LLM mapping fallback with disabled, mock, and OpenAI-compatible modes
- Deterministic task replay with `parent_task_id`
- Expanded config snapshots with mapping lineage and model audit
- Controlled Mapping Knowledge growth loop for reviewed aliases, rules, badcases, and evaluation assets
- Human approval gate for all learned mapping knowledge before activation
- Active knowledge packs merged into Mapping Templates before deterministic mapping, with applied pack IDs recorded in mapping reports
- Knowledge review APIs and frontend review page for real-run capture, candidate approval/rejection, draft pack creation, explicit activation, and metrics
- Frozen evaluation fixture under `examples/eval/` with 30 cases and 150 gold mappings
- Mapping evaluation CLI and generated report under `docs/reports/`
- Deterministic content labels, chunk labels, upstream entities, and consumer smoke CLI
- Frozen OpenAPI JSON and delivery documents

Not implemented yet:

- A live cloud-model acceptance run with user-provided credentials
- Human-reviewed public accuracy claims beyond the synthetic regression fixture
- Package signing or cryptographic attestation beyond SHA-256

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

## Frontend

The Phase 8 workbench is designed for desktop use. Start the backend first, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The default API base URL is
`http://127.0.0.1:8000/api/v1`; override it with `VITE_API_BASE_URL` when needed.

Frontend quality gates:

```powershell
cd frontend
npm run test
npm run test:coverage
npm run lint
npm run build
```

## Phase 9 Quality Baseline

Measured on 2026-06-22:

- Backend: 271 tests, 98.22% line coverage, 94.66% branch coverage.
- Frontend: 50 tests, 97.07% line coverage, 90.51% branch coverage, 98.83% function coverage.
- Every core backend file under `app/api/v1`, `app/engines`, `app/services`, and `app/validators` has at least 95% line coverage.
- Both demo document types complete the real HTTP workflow from import through package download and per-entry manifest verification.
- Concurrent same-task mutations return a deterministic `409 TASK_STATE_ERROR`; different task locks remain independent.
- Atomic-write, retry, idempotency, malformed request, badcase, and deliberately damaged package tests are version controlled.

Backend quality gates:

```powershell
cd backend
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=json:coverage.json -q
.\.venv\Scripts\python tests\coverage_gate.py coverage.json
.\.venv\Scripts\python -m ruff check .
```

Frontend quality gates:

```powershell
cd frontend
npm run test:coverage
npm run lint
npm run build
```

Phase 9 badcases:

```text
examples/badcases/badcase_missing_required.json
examples/badcases/badcase_type_error.json
examples/badcases/badcase_mapping_ambiguous.json
examples/badcases/badcase_broken_block_link.json
```

## Phase 10 Acceptance Baseline

External package verifier:

```powershell
cd backend
.\.venv\Scripts\python -m app.tools.package_verifier <path-to-standard_package.zip>
```

Consumer smoke test:

```powershell
cd backend
.\.venv\Scripts\python -m app.tools.consume_package <path-to-standard_package.zip>
```

Frozen mapping evaluation:

```powershell
cd backend
.\.venv\Scripts\python -m app.tools.evaluate_mappings ..\examples\eval\eval_cases.json --json-out ..\docs\reports\evaluation_report.json --md-out ..\docs\reports\evaluation_report.md
```

Measured on the synthetic frozen fixture:

- Samples: 30
- Gold mappings: 150
- Precision/Recall/F1: 1.0000 / 1.0000 / 1.0000

These metrics are regression evidence for the checked-in fixture. Human review of gold mappings is still required before making external accuracy claims.

Implemented API slice:

```text
POST /api/v1/documents/import
GET  /api/v1/documents
GET  /api/v1/documents/{doc_id}
POST /api/v1/tasks
GET  /api/v1/tasks
GET  /api/v1/tasks/{task_id}
POST /api/v1/schemas
GET  /api/v1/schemas
GET  /api/v1/schemas/{schema_id}
POST /api/v1/templates
PUT  /api/v1/templates/{template_id}
GET  /api/v1/templates
GET  /api/v1/templates/{template_id}
POST /api/v1/tasks/{task_id}/generate-candidates
GET  /api/v1/tasks/{task_id}/candidates
POST /api/v1/tasks/{task_id}/map
GET  /api/v1/tasks/{task_id}/mappings
POST /api/v1/tasks/{task_id}/mappings/review
GET  /api/v1/tasks/{task_id}/reports/mapping
POST /api/v1/tasks/{task_id}/convert
GET  /api/v1/tasks/{task_id}/canonical
POST /api/v1/tasks/{task_id}/package
GET  /api/v1/tasks/{task_id}/package/download
GET  /api/v1/tasks/{task_id}/reports/validation
GET  /api/v1/tasks/{task_id}/reports/consistency
GET  /api/v1/tasks/{task_id}/reports/package-verifier
GET  /api/v1/tasks/{task_id}/trace
POST /api/v1/tasks/{task_id}/replay
POST /api/v1/knowledge/real-runs/from-task/{task_id}
POST /api/v1/knowledge/real-runs/{real_run_id}/derive
GET  /api/v1/knowledge/candidates
POST /api/v1/knowledge/candidates/{candidate_id}/decision
POST /api/v1/knowledge/packs
POST /api/v1/knowledge/packs/{pack_id}/activate
GET  /api/v1/knowledge/packs
GET  /api/v1/knowledge/metrics
```

Task creation currently records `schema_id` and `template_id` from the request without checking that Schema/Template records exist. Mapping, conversion, packaging, replay, config snapshotting, external package verification, and evaluation tooling are implemented.

## Development Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest -q
```

Lint:

```powershell
cd backend
.\.venv\Scripts\python -m ruff check .
```

## Project Boundaries

The project receives UIR as input. It does not parse PDF, Word, Excel, images, OCR outputs, or raw source files. It does not implement cleaning, normalization, full quality scoring, full RAG, or model training.

The Mapping Knowledge growth loop only learns mapping knowledge and evaluation assets. It does not train models, parse raw documents, clean data, normalize entities, or bypass human review for uncertain mappings. Learned knowledge must pass human approval and explicit pack activation before it can influence future deterministic mapping runs.

The core development line remains:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> Zip
```

`examples/` contains versioned development and evaluation samples. `storage/` is runtime output only and should not be used as a fixed test fixture location.
