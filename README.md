# SchemaPack Agent

SchemaPack Agent is the project for topic 5: standardizing an upstream UIR document into schema-driven output packages.

Current implementation status: Phase 5 transform engine and canonical model.

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
- Pytest baseline for bootstrap, schemas, examples, storage, documents, tasks, Target Schema APIs, Mapping Template APIs, candidate extraction, mapping, reports, review, transform engine, trace service, and canonical builder

Not implemented yet:

- Multi-format rendering (content.json, content.md, chunks.json)
- Validation, manifest, package ZIP, verifier
- Frontend
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
```

Task creation currently records `schema_id` and `template_id` from the request without checking that Schema/Template records exist. Mapping execution loads those records when a task is run; Transform, Canonical, Render, Validate, Manifest, and Zip stages remain later phases.

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
