# SchemaPack Phase 2 Documents And Tasks Implementation Plan

> **Historical plan:** Preserved as an execution record. Current status: [`../../project_status.md`](../../交接/project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first usable document and conversion-task management slice.

**Architecture:** Keep routers thin and place filesystem/database behavior in services. `StorageService` owns all runtime paths and JSON persistence; `DocumentService` validates and saves UIR input; `TaskService` creates conversion tasks with deterministic input hashes and exposes task status. This phase does not implement mapping, transform, rendering, packaging, or LLM behavior.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite, pytest, FastAPI TestClient.

---

### File Structure

- Create `backend/app/services/storage_service.py`: safe path construction, JSON/text read-write, SHA-256, and directory initialization.
- Create `backend/app/services/document_service.py`: import UIR into storage and `documents` table, list documents, get document details.
- Create `backend/app/services/task_service.py`: create task rows, compute input hash from saved UIR, list tasks, get task status, enforce basic state transitions.
- Create `backend/app/api/deps.py`: provide database sessions to routers.
- Create `backend/app/api/v1/documents.py`: document import/list/detail routes.
- Create `backend/app/api/v1/tasks.py`: task create/list/detail routes.
- Modify `backend/app/api/v1/router.py`: include document and task routers.
- Modify `backend/app/schemas/api.py`: add request/response models for document and task APIs.
- Create `backend/tests/test_storage_service.py`: storage behavior tests.
- Create `backend/tests/test_documents_api.py`: UIR import and document API tests.
- Create `backend/tests/test_tasks_api.py`: conversion task API tests.

### Task 1: StorageService

**Files:**
- Create: `backend/tests/test_storage_service.py`
- Create: `backend/app/services/storage_service.py`

- [ ] **Step 1: Write failing storage tests**

Test that `StorageService` writes JSON as UTF-8, reads JSON back, writes text, computes SHA-256, creates nested directories, and rejects absolute paths plus `..` traversal.

- [ ] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_storage_service.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services'`.

- [ ] **Step 3: Implement minimal StorageService**

Implement `save_json(relative_path, data)`, `read_json(relative_path)`, `write_text(relative_path, text)`, `read_text(relative_path)`, `sha256(relative_path)`, and `resolve(relative_path)`.

- [ ] **Step 4: Run test to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_storage_service.py -q`

Expected: PASS.

### Task 2: Document Import And Read APIs

**Files:**
- Create: `backend/tests/test_documents_api.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/services/document_service.py`
- Create: `backend/app/api/v1/documents.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [ ] **Step 1: Write failing document API tests**

Test `POST /api/v1/documents/import`, `GET /api/v1/documents`, and `GET /api/v1/documents/{doc_id}` using `examples/demo/example_uir_general_doc.json`.

- [ ] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_documents_api.py -q`

Expected: FAIL with 404 routes or missing service imports.

- [ ] **Step 3: Implement document service and routes**

Use `UIRDocument` for validation. Save UIR to `documents/{doc_id}/uir.json`, upsert `documents` table, return imported document metadata, and expose list/detail responses.

- [ ] **Step 4: Run test to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_documents_api.py -q`

Expected: PASS.

### Task 3: Conversion Task APIs

**Files:**
- Create: `backend/tests/test_tasks_api.py`
- Create: `backend/app/services/task_service.py`
- Create: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [ ] **Step 1: Write failing task API tests**

Test that creating a task for an imported document returns status `created`, task detail returns doc/schema/template references, list includes the new task, and creating a task for an unknown document returns 404.

- [ ] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_tasks_api.py -q`

Expected: FAIL with 404 routes or missing service imports.

- [ ] **Step 3: Implement task service and routes**

Create task IDs with a compact UUID prefix. Read the saved UIR JSON to calculate SHA-256. For Phase 2, store schema/template IDs and versions from the request without requiring schema CRUD to exist yet.

- [ ] **Step 4: Run test to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_tasks_api.py -q`

Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README status**

Add Phase 2 implemented APIs and keep later phases marked as not implemented.

- [ ] **Step 2: Run all tests**

Run: `cd backend; .\.venv\Scripts\python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Run lint**

Run: `cd backend; .\.venv\Scripts\python -m ruff check .`

Expected: PASS.

---

### Self-Review

Spec coverage: covers Phase 2.1 through 2.5 from the blueprint: storage service, UIR import, document list/detail, task creation, task status.

Placeholder scan: no task depends on unspecified behavior.

Type consistency: API names match blueprint routes and existing schema module naming.
