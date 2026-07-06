# SchemaPack Phase 0-1 Implementation Plan

> **Historical plan:** Preserved as an execution record. Current status: [`../../project_status.md`](../../交接/project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable SchemaPack Agent backend skeleton and data-contract baseline.

**Architecture:** Create a FastAPI backend with thin routing, environment settings, SQLite metadata, and Pydantic v2 schemas. Use demo examples as contract fixtures so later mapping and packaging work has stable inputs.

**Tech Stack:** Python 3.13 local runtime, FastAPI, Pydantic v2, SQLAlchemy 2.x, pytest, httpx, ruff.

---

### Task 1: Backend Bootstrap Tests

**Files:**
- Create: `backend/tests/test_bootstrap.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`

- [ ] **Step 1: Write failing health/config/database tests**

Create tests that import `app.main`, `app.config`, and `app.db.models`, then assert `/health`, settings defaults, env overrides, and required table names.

- [ ] **Step 2: Run tests to verify red**

Run: `cd backend; pytest tests/test_bootstrap.py -q`

Expected: fails because `app` package and modules do not exist yet.

- [ ] **Step 3: Implement minimal bootstrap modules**

Create `backend/app/main.py`, `backend/app/config.py`, `backend/app/api/v1/router.py`, `backend/app/db/session.py`, and `backend/app/db/models.py` with only the behavior covered by tests.

- [ ] **Step 4: Run tests to verify green**

Run: `cd backend; pytest tests/test_bootstrap.py -q`

Expected: all bootstrap tests pass.

### Task 2: Pydantic Contract Tests

**Files:**
- Create: `backend/tests/test_schemas.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/uir.py`
- Create: `backend/app/schemas/target_schema.py`
- Create: `backend/app/schemas/mapping_template.py`
- Create: `backend/app/schemas/mapping.py`
- Create: `backend/app/schemas/transform.py`
- Create: `backend/app/schemas/canonical.py`
- Create: `backend/app/schemas/reports.py`
- Create: `backend/app/schemas/package.py`
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/schemas/run_snapshot.py`
- Create: `backend/app/schemas/output_profile.py`
- Create: `backend/app/schemas/api.py`

- [ ] **Step 1: Write failing schema tests**

Create tests for valid UIR, Target Schema, Mapping Template, Canonical Model, reports, package metadata, review records, execution snapshots, and output profiles. Include invalid cases for missing `doc_id`, empty `fields`, and transform rules without targets.

- [ ] **Step 2: Run tests to verify red**

Run: `cd backend; pytest tests/test_schemas.py -q`

Expected: fails because schema modules do not exist.

- [ ] **Step 3: Implement minimal Pydantic models**

Define only the fields required by the blueprint examples and tests. Use Pydantic validators for non-empty field lists and transform-rule target checks.

- [ ] **Step 4: Run tests to verify green**

Run: `cd backend; pytest tests/test_schemas.py -q`

Expected: all schema tests pass.

### Task 3: Demo Example Fixtures

**Files:**
- Create: `examples/demo/example_uir_general_doc.json`
- Create: `examples/demo/example_uir_policy_doc.json`
- Create: `examples/demo/target_schema_general.json`
- Create: `examples/demo/target_schema_policy.json`
- Create: `examples/demo/mapping_template_general.json`
- Create: `examples/demo/mapping_template_policy.json`
- Create: `backend/tests/test_examples_load.py`

- [ ] **Step 1: Write failing example-loading tests**

Test that all six demo files exist, load as UTF-8 JSON, and validate through the Pydantic models.

- [ ] **Step 2: Run tests to verify red**

Run: `cd backend; pytest tests/test_examples_load.py -q`

Expected: fails because demo fixtures do not exist.

- [ ] **Step 3: Add demo fixtures**

Create one general document and one policy document. Include exact, alias, regex, type, fuzzy-ish naming, date conversion, enum mapping, defaults, and required validation coverage in the schemas/templates.

- [ ] **Step 4: Run tests to verify green**

Run: `cd backend; pytest tests/test_examples_load.py -q`

Expected: all example-loading tests pass.

### Task 4: Baseline Verification

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Add minimal project docs/config files**

Document backend startup, tests, project boundaries, and Phase 0/1 scope. Add `.env.example` with safe defaults and `.gitignore` for Python, Node, SQLite, and `storage/`.

- [ ] **Step 2: Run all backend tests**

Run: `cd backend; pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Run lint if dependencies are installed**

Run: `cd backend; ruff check .`

Expected: no lint errors. If `ruff` is unavailable, install requirements first and rerun.

---

### Self-Review

Spec coverage: this plan covers Phase 0 and Phase 1 from the blueprint only.

Placeholder scan: no implementation step depends on unspecified behavior.

Type consistency: file names and model names match the blueprint and the design document.
