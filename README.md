# SchemaPack Agent

SchemaPack Agent is the project for topic 5: standardizing an upstream UIR document into schema-driven output packages.

Current implementation status: Phase 8 desktop document workbench with end-to-end package delivery.

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
- Pytest baseline for bootstrap, schemas, examples, storage, documents, tasks, Target Schema APIs, Mapping Template APIs, candidate extraction, mapping, reports, review, transform, canonical construction, conversion APIs, multi-format rendering, and package validation
- Vitest, ESLint, and production build gates for the frontend workbench

Not implemented yet:

- Independent external package verifier
- Real LLM fallback

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
npm run lint
npm run build
```

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
GET  /api/v1/tasks/{task_id}/trace
```

Task creation currently records `schema_id` and `template_id` from the request without checking that Schema/Template records exist. Mapping, conversion, and packaging execution load those records when a task is run. Transform, canonical construction, rendering, validation, manifest generation, and package ZIP creation are implemented. The independent external package verifier remains a later phase.

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

The core development line remains:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> Zip
```

`examples/` contains versioned development and evaluation samples. `storage/` is runtime output only and should not be used as a fixed test fixture location.
