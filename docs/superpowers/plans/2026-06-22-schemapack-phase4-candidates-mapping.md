# SchemaPack Phase 4 Candidates And Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement field candidate extraction, rule-based field mapping, mapping reports, and manual review updates.

**Architecture:** Add a small engine layer for deterministic extraction and mapping. Services own database persistence and task status updates. Routers expose the blueprint routes under `/api/v1/tasks/{task_id}/...`; LLM support is represented by a mockable client seam only, and does not generate final content.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite, pytest, Python standard library `difflib` for fuzzy matching.

---

### File Structure

- Create `backend/app/engines/field_candidate_engine.py`: extract candidates from UIR metadata, block attributes, headings, table-like columns, and simple label-value text.
- Create `backend/app/engines/mapping_engine.py`: exact, alias, regex-label, type, and fuzzy mapping strategy.
- Create `backend/app/clients/llm_client.py`: disabled/mock/openai-compatible seam returning structured suggestions; Phase 4 uses mock only.
- Create `backend/app/services/candidate_service.py`: generate and persist candidates for a task, list candidates.
- Create `backend/app/services/mapping_service.py`: execute rule mapping, persist mappings, create `mapping_report.json`, list mappings.
- Create `backend/app/services/review_service.py`: update mappings from human review and record review rows.
- Create `backend/app/api/v1/mappings.py`: candidate generation, mapping execution, mapping list, and review routes.
- Create `backend/app/api/v1/reports.py`: mapping report route.
- Modify `backend/app/api/v1/router.py`: include mappings and reports routers.
- Modify `backend/app/schemas/api.py`: request/response models for Phase 4 routes.
- Modify `README.md`: list Phase 4 APIs and limitations.
- Create `backend/tests/test_phase4_mapping_api.py`: integration tests for candidate extraction, mapping, report, and review.

### Task 1: Candidate Extraction API

**Files:**
- Create: `backend/tests/test_phase4_mapping_api.py`
- Create: `backend/app/engines/field_candidate_engine.py`
- Create: `backend/app/services/candidate_service.py`
- Create: `backend/app/api/v1/mappings.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [x] **Step 1: Write failing candidate extraction tests**

Test that importing the demo UIR, creating schema/template/task, then calling `POST /api/v1/tasks/{task_id}/generate-candidates` persists candidates and `GET /api/v1/tasks/{task_id}/candidates` returns metadata and block-derived candidates.

- [x] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: FAIL with missing routes or service imports.

- [x] **Step 3: Implement candidate extraction**

Extract metadata fields, block attributes, heading titles, and label-value pairs such as `发布日期：2026年6月1日`. Persist into `field_candidates` and update task status to `candidates_ready`.

- [x] **Step 4: Run candidate tests to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: candidate tests pass; mapping tests still fail until Task 2.

### Task 2: Rule Mapping And Report

**Files:**
- Create: `backend/app/engines/mapping_engine.py`
- Create: `backend/app/services/mapping_service.py`
- Create: `backend/app/api/v1/reports.py`
- Modify: `backend/app/api/v1/mappings.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`

- [x] **Step 1: Write failing mapping tests**

Test that `POST /api/v1/tasks/{task_id}/map` maps demo fields using alias/exact/type/fuzzy rules, `GET /mappings` lists results, and `GET /reports/mapping` returns summary.

- [x] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: FAIL on missing mapping behavior.

- [x] **Step 3: Implement mapping engine/service**

Use deterministic priority: exact, alias, regex_match, type_match, fuzzy_match. Persist `field_mappings`, generate `tasks/{task_id}/mapping_report.json`, and update task status to `mapping_completed` or `review_required`.

- [x] **Step 4: Run mapping tests to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: mapping tests pass.

### Task 3: Manual Review And LLM Seam

**Files:**
- Create: `backend/app/services/review_service.py`
- Create: `backend/app/clients/llm_client.py`
- Modify: `backend/app/api/v1/mappings.py`
- Modify: `backend/app/schemas/api.py`

- [x] **Step 1: Write failing review tests**

Test that high review threshold marks mappings for review and `POST /api/v1/tasks/{task_id}/mappings/review` confirms or changes target fields.

- [x] **Step 2: Run test to verify red**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: FAIL on missing review behavior.

- [x] **Step 3: Implement review service and mock LLM client**

Review updates mapping `target_field_id`, `status`, `need_review`, and inserts a `review_records` row. LLM client returns structured mock suggestions and is not used to write final outputs.

- [x] **Step 4: Run review tests to verify green**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase4_mapping_api.py -q`

Expected: all Phase 4 tests pass.

### Task 4: Verification And Commit

**Files:**
- Modify: `README.md`

- [x] **Step 1: Update README**

List Phase 4 implemented APIs and keep Transform/Canonical/Render/Package marked as not implemented.

- [x] **Step 2: Run all tests**

Run: `cd backend; .\.venv\Scripts\python -m pytest -q`

Expected: PASS.

- [x] **Step 3: Run lint**

Run: `cd backend; .\.venv\Scripts\python -m ruff check .`

Expected: PASS.

- [x] **Step 4: Commit Phase 4**

Run: `git add .; git commit -m "feat: add candidate extraction and rule mapping"`

Expected: commit succeeds on `phase4-candidates-mapping`.

---

### Self-Review

Spec coverage: covers Phase 4.1 through 4.10 at MVP level, except real LLM fallback which remains a later validation enhancement.

Placeholder scan: no task depends on unspecified behavior.

Type consistency: API paths match the blueprint and existing `/api/v1/tasks/{task_id}` route style.
