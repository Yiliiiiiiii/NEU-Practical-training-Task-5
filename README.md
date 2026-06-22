# SchemaPack Agent

SchemaPack Agent is the project for topic 5: standardizing an upstream UIR document into schema-driven output packages.

Current implementation status: Phase 3 schema and template management baseline.

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
- Pytest baseline for bootstrap, schemas, examples, storage, documents, tasks, Target Schema APIs, and Mapping Template APIs

Not implemented yet:

- Field candidate extraction
- Mapping engine
- Transform engine
- Canonical rendering
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

Phase 2 API slice:

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
```

Task creation currently records `schema_id` and `template_id` from the request without checking that Schema/Template records exist. The actual schema/template records are managed by the Phase 3 endpoints and will be wired into conversion execution in later phases.

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
