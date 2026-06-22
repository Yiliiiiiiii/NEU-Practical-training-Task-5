# SchemaPack Phase 3 Schema And Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Target Schema CRUD, Mapping Template CRUD, and template-to-schema binding validation.

**Architecture:** Keep validation and persistence in services, with routers limited to HTTP request/response handling. `SchemaService` stores Target Schemas in SQLite and runtime storage, while `TemplateService` stores Mapping Templates and rejects templates whose `schema_id` is unknown or whose target references do not exist in the bound schema.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite, pytest, FastAPI TestClient.

---

### File Structure

- Create `backend/app/services/schema_service.py`: create/list/get Target Schema records and save schema JSON under `schemas/{schema_id}/schema.json`.
- Create `backend/app/services/template_service.py`: create/update/list/get Mapping Template records and save JSON under `templates/{template_id}/template.json`.
- Create `backend/app/validators/schema_validator.py`: service-level schema checks beyond Pydantic, including duplicate field IDs and required JSON Schema shape.
- Create `backend/app/api/v1/schemas.py`: `POST /schemas`, `GET /schemas`, `GET /schemas/{schema_id}`.
- Create `backend/app/api/v1/templates.py`: `POST /templates`, `PUT /templates/{template_id}`, `GET /templates`, `GET /templates/{template_id}`.
- Modify `backend/app/api/v1/router.py`: include schemas and templates routers.
- Modify `backend/app/schemas/api.py`: add request/response models for schema and template endpoints.
- Create `backend/tests/test_schemas_api.py`: API tests for Target Schema CRUD and invalid schema handling.
- Create `backend/tests/test_templates_api.py`: API tests for Mapping Template CRUD and schema binding validation.

### Task 1: Target Schema API

**Files:**
- Create: `backend/tests/test_schemas_api.py`
- Create: `backend/app/validators/schema_validator.py`
- Create: `backend/app/services/schema_service.py`
- Create: `backend/app/api/v1/schemas.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [ ] **Step 1: Write failing Target Schema API tests**

Test creating `examples/demo/target_schema_general.json`, listing schemas, reading detail, rejecting duplicate field IDs with HTTP 400, and returning 404 for unknown schema IDs.

- [ ] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_schemas_api.py -q`

Expected: FAIL with 404 routes or missing service imports.

- [ ] **Step 3: Implement Target Schema API**

Persist schema JSON to SQLite and storage. Reject duplicate `field_id` values and non-object `json_schema` definitions. Return stable response models.

- [ ] **Step 4: Run test to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_schemas_api.py -q`

Expected: PASS.

### Task 2: Mapping Template API

**Files:**
- Create: `backend/tests/test_templates_api.py`
- Create: `backend/app/services/template_service.py`
- Create: `backend/app/api/v1/templates.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [ ] **Step 1: Write failing Mapping Template API tests**

Test creating a template for an existing schema, listing templates, reading detail, updating a template, rejecting unknown `schema_id` with HTTP 404, and rejecting a template that references a target field missing from the bound schema with HTTP 400.

- [ ] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_templates_api.py -q`

Expected: FAIL with 404 routes or missing service imports.

- [ ] **Step 3: Implement Mapping Template API**

Persist template JSON to SQLite and storage. Validate `schema_id` exists, aliases keys exist in schema fields, regex target field IDs exist, transform target field IDs exist, and enum map keys exist.

- [ ] **Step 4: Run test to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_templates_api.py -q`

Expected: PASS.

### Task 3: Verification And Commit

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

List Phase 3 implemented APIs and keep Phase 4+ features marked as not implemented.

- [ ] **Step 2: Run all tests**

Run: `cd backend; .\.venv\Scripts\python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Run lint**

Run: `cd backend; .\.venv\Scripts\python -m ruff check .`

Expected: PASS.

- [ ] **Step 4: Commit Phase 3**

Run: `git add .; git commit -m "feat: add schema and template management"`

Expected: commit succeeds on `phase3-schema-template`.

---

### Self-Review

Spec coverage: covers Phase 3.1 through 3.4 from the blueprint.

Placeholder scan: no task depends on unspecified behavior.

Type consistency: API paths match the blueprint and existing `/api/v1` routing style.
