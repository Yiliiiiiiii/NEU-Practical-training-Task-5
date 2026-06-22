# Phase 9 Test And Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a high-confidence Phase 9 baseline with measurable coverage, uniform API failures, atomic persistence, versioned badcases, full API E2E tests, and deterministic concurrency/retry behavior.

**Architecture:** Keep the existing engines and services, adding only focused stabilization boundaries: a typed application-error layer, atomic storage publication, and a process-local task mutation guard. Tests are organized by unit, API contract, E2E, and stability responsibilities, with coverage gates consuming machine-readable reports.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Pydantic v2, pytest, pytest-cov/coverage.py, React 18, TypeScript, Vitest, Testing Library, V8 coverage, Ruff, ESLint.

---

## File Responsibility Map

- `backend/app/errors.py`: application error types and stable public error codes.
- `backend/app/error_handlers.py`: FastAPI exception handlers and error-envelope serialization.
- `backend/app/services/storage_service.py`: atomic UTF-8 JSON/text publication.
- `backend/app/services/task_lock_service.py`: process-local per-task mutation guard.
- `backend/tests/coverage_gate.py`: independent total-line, total-branch, and core-file coverage checks.
- `backend/tests/test_error_contract.py`: global and route-specific failure contracts.
- `backend/tests/test_storage_atomic.py`: atomic write and retry behavior.
- `backend/tests/test_api_inventory.py`: exact MVP route inventory and generic negative contracts.
- `backend/tests/test_phase9_badcases.py`: committed badcase fixture behavior.
- `backend/tests/test_phase9_e2e.py`: complete general/policy API pipelines.
- `backend/tests/test_phase9_stability.py`: concurrency, idempotency, retry, and damaged package tests.
- `frontend/src/__tests__/workflowPages.test.tsx`: task detail/package workflow behavior.
- `frontend/src/__tests__/apiFailures.test.ts`: unified API failures and download evidence.

### Task 1: Install And Enforce Coverage Infrastructure

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/coverage_gate.py`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vitest.config.ts`

- [ ] **Step 1: Add a failing backend gate self-test**

Create a temporary unit inside `backend/tests/test_coverage_gate.py` that writes a coverage JSON document with 94 percent lines and 89 percent branches, calls `evaluate_coverage`, and asserts the returned failures include all missed thresholds:

```python
from tests.coverage_gate import evaluate_coverage


def test_gate_rejects_low_total_and_core_file_coverage():
    report = {
        "totals": {
            "percent_covered": 94.0,
            "num_branches": 100,
            "covered_branches": 89,
        },
        "files": {
            "app/engines/mapping_engine.py": {
                "summary": {"percent_covered": 93.0}
            }
        },
    }

    failures = evaluate_coverage(report)

    assert "total line coverage 94.00% < 95.00%" in failures
    assert "total branch coverage 89.00% < 90.00%" in failures
    assert any("mapping_engine.py" in failure for failure in failures)
```

- [ ] **Step 2: Run the gate test and verify RED**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_coverage_gate.py -q`

Expected: FAIL because `tests.coverage_gate` does not exist.

- [ ] **Step 3: Add pinned coverage dependencies and the backend gate**

Add `pytest-cov==6.0.0` to `backend/requirements.txt`. Implement `evaluate_coverage(report)` in `backend/tests/coverage_gate.py` with constants `TOTAL_LINES=95.0`, `TOTAL_BRANCHES=90.0`, `CORE_FILE_LINES=95.0`. Core files are paths beginning with `app/api/v1/`, `app/engines/`, `app/services/`, or `app/validators/`, excluding `__init__.py`.

The script entry point reads the JSON path from `sys.argv[1]`, prints one failure per line, and exits 1 when failures exist.

Add deterministic coverage settings:

```toml
[tool.coverage.run]
branch = true
source = ["app"]

[tool.coverage.report]
show_missing = true
skip_covered = false
```

- [ ] **Step 4: Add frontend V8 coverage configuration**

Run: `cd frontend; npm.cmd install --save-dev @vitest/coverage-v8@2.1.9`

Add script:

```json
"test:coverage": "vitest run --config vitest.config.ts --coverage"
```

Configure:

```ts
coverage: {
  provider: "v8",
  reporter: ["text", "json-summary"],
  include: ["src/**/*.{ts,tsx}"],
  exclude: ["src/**/*.d.ts", "src/main.tsx", "src/test/**", "src/demo/**"],
  thresholds: { lines: 90, branches: 85, functions: 90, statements: 90 },
},
```

- [ ] **Step 5: Verify gate behavior and capture the honest baseline**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest tests/test_coverage_gate.py -q
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=json:coverage.json --cov-report=term-missing -q
.\.venv\Scripts\python tests/coverage_gate.py coverage.json
cd ..\frontend
npm.cmd run test:coverage
```

Expected: the gate unit passes; one or both project coverage commands may fail and must print the measured baseline rather than being waived.

- [ ] **Step 6: Commit coverage infrastructure**

```powershell
git add backend/requirements.txt backend/pyproject.toml backend/tests/coverage_gate.py backend/tests/test_coverage_gate.py frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "test: add strict phase 9 coverage gates"
```

### Task 2: Implement The Unified API Error Envelope

**Files:**
- Create: `backend/app/errors.py`
- Create: `backend/app/error_handlers.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/v1/documents.py`
- Modify: `backend/app/api/v1/mappings.py`
- Modify: `backend/app/api/v1/reports.py`
- Modify: `backend/app/api/v1/schemas.py`
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/api/v1/templates.py`
- Test: `backend/tests/test_error_contract.py`

- [ ] **Step 1: Write failing envelope tests**

Test malformed task creation, missing task, schema binding error, convert-before-mapping, package-before-render, and an injected unexpected failure. Use `create_app(init_database=False)`, dependency overrides, and `TestClient(app, raise_server_exceptions=False)` for the injected 500. Assert exact shape:

```python
def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], list)


def test_request_validation_uses_unified_error(client):
    response = client.post("/api/v1/tasks", json={})
    assert_error(response, 422, "VALIDATION_ERROR")
    assert {item["path"] for item in response.json()["error"]["details"]} >= {
        "body.doc_id", "body.schema_id", "body.template_id"
    }
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_error_contract.py -q`

Expected: FAIL because FastAPI currently returns `detail`.

- [ ] **Step 3: Implement typed application errors**

Create `AppError(status_code, code, message, details=[])` plus constructors:

```python
class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(404, "NOT_FOUND", message)


class TaskStateError(AppError):
    def __init__(self, message: str):
        super().__init__(409, "TASK_STATE_ERROR", message)


class SchemaInvalidError(AppError):
    def __init__(self, message: str):
        super().__init__(400, "SCHEMA_INVALID", message)


class MappingReviewRequiredError(AppError):
    def __init__(self, message: str):
        super().__init__(409, "MAPPING_REVIEW_REQUIRED", message)


class PackageNotReadyError(AppError):
    def __init__(self, message: str):
        super().__init__(409, "PACKAGE_NOT_READY", message)
```

- [ ] **Step 4: Register exception handlers**

`register_error_handlers(app)` must serialize `ErrorResponse`, convert `RequestValidationError.errors()` into dotted `path` plus `message`, map fallback `HTTPException` statuses, and return `INTERNAL_ERROR` with the generic message `Internal server error` for unexpected exceptions.

Use `JSONResponse(status_code=..., content=ErrorResponse(...).model_dump(mode="json"))`.

- [ ] **Step 5: Replace router exception translations**

Across all six route modules, replace `HTTPException` creation with the typed errors. Convert package readiness messages to `PackageNotReadyError`; unresolved review messages to `MappingReviewRequiredError`; other illegal transitions to `TaskStateError`; schema/template validation failures to `SchemaInvalidError`; missing records/files to `NotFoundError`.

- [ ] **Step 6: Verify targeted and full API tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_error_contract.py -q
.\.venv\Scripts\python -m pytest tests/test_documents_api.py tests/test_tasks_api.py tests/test_schemas_api.py tests/test_templates_api.py tests/test_phase4_mapping_api.py tests/test_phase7_package.py -q
```

Expected: all pass after updating existing assertions from `detail` to `error` where required.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/errors.py backend/app/error_handlers.py backend/app/main.py backend/app/api/v1 backend/tests/test_error_contract.py backend/tests
git commit -m "feat: unify API error responses"
```

### Task 3: Make Storage Publication Atomic And Retry-Safe

**Files:**
- Modify: `backend/app/services/storage_service.py`
- Test: `backend/tests/test_storage_atomic.py`

- [ ] **Step 1: Write failing atomicity tests**

Use monkeypatch to make `Path.replace` fail. Verify the existing destination remains unchanged and no sibling `*.tmp` file survives. Add a concurrent write test with eight threads writing complete JSON values and verify the final file parses as one complete submitted value.

```python
def test_failed_publish_preserves_previous_json(storage, monkeypatch):
    storage.save_json("tasks/t1/content.json", {"version": 1})
    monkeypatch.setattr(Path, "replace", lambda *_: (_ for _ in ()).throw(OSError("publish")))

    with pytest.raises(OSError, match="publish"):
        storage.save_json("tasks/t1/content.json", {"version": 2})

    assert storage.read_json("tasks/t1/content.json") == {"version": 1}
    assert list(storage.resolve("tasks/t1").glob("*.tmp")) == []
```

- [ ] **Step 2: Run and verify RED**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_storage_atomic.py -q`

Expected: FAIL because current writes truncate the destination directly.

- [ ] **Step 3: Implement `_atomic_write`**

Create a uniquely named sibling temporary file using `tempfile.NamedTemporaryFile(delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")`, write and flush UTF-8 bytes, call `os.fsync`, close, then `Path(temp_name).replace(path)`. In `finally`, unlink the temporary path when it still exists. Route both `save_json` and `write_text` through `_atomic_write`.

- [ ] **Step 4: Verify storage and package regressions**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_storage_atomic.py tests/test_storage_service.py tests/test_phase7_package.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/storage_service.py backend/tests/test_storage_atomic.py
git commit -m "fix: publish storage outputs atomically"
```

### Task 4: Add Versioned Badcase Fixtures

**Files:**
- Create: `examples/badcases/badcase_missing_required.json`
- Create: `examples/badcases/badcase_type_error.json`
- Create: `examples/badcases/badcase_mapping_ambiguous.json`
- Create: `examples/badcases/badcase_broken_block_link.json`
- Create: `backend/tests/test_phase9_badcases.py`

- [ ] **Step 1: Write the fixture-contract test before creating fixtures**

Parameterize the four exact paths. Require keys `case_id`, `description`, `input`, `expected`. Require `expected` keys `error_code`, `task_status`, `trace_action`.

- [ ] **Step 2: Run and verify RED**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase9_badcases.py::test_badcase_fixture_contract -q`

Expected: FAIL with four missing files.

- [ ] **Step 3: Create the four complete fixtures**

Use demo-derived minimal UIR/schema/template data. Expectations:

- `missing_required`: `VALIDATION_ERROR`, task `failed`, trace `create_package`.
- `type_error`: `TASK_STATE_ERROR`, task `failed`, trace `type_cast` with failed status.
- `mapping_ambiguous`: `MAPPING_REVIEW_REQUIRED`, task `review_required`, trace `run_mapping`.
- `broken_block_link`: consistency error `chunk_source_blocks_backlink`, task `failed`, trace `create_package`.

- [ ] **Step 4: Add one behavior test per fixture**

Load each fixture and execute the relevant validator/engine/service. Assertions must use fixture expectations, not duplicate hard-coded values.

- [ ] **Step 5: Verify and commit**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase9_badcases.py -q`

```powershell
git add examples/badcases backend/tests/test_phase9_badcases.py
git commit -m "test: add phase 9 badcase fixtures"
```

### Task 5: Complete Unit And Historical Regression Coverage

**Files:**
- Create: `backend/tests/test_unit_coverage_gaps.py`
- Modify only when a failing test reveals a defect: focused files under `backend/app/engines`, `backend/app/services`, `backend/app/validators`, `backend/app/renderers`

- [ ] **Step 1: Generate the uncovered-line report**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=json:coverage.json -q
.\.venv\Scripts\python tests/coverage_gate.py coverage.json
```

Record every core file below 95 percent in the test module docstring as the initial gap inventory.

- [ ] **Step 2: Add focused RED tests in risk order**

Cover uncovered branches for schema/template validation, candidate metadata/block/table flags, mapping priority/ties, every transform error path, canonical provenance/required fields, chunk boundaries, renderer empty assets, validator pattern/range/type failures, manifest unsafe paths, trace export, and package verification.

Each new test must first fail because a branch is untested or because it exposes incorrect behavior. Defects receive minimal production fixes in the owning module.

- [ ] **Step 3: Preserve Phase 5-8 regressions**

Add explicit assertions for Chinese metadata rename, date warning preservation, merge/split provenance, review blocking, required/default rules, chunk text loss prevention, render write failure state, manifest self-exclusion, package SHA, and CORS exposure.

- [ ] **Step 4: Run the gate until core thresholds pass**

Run the commands from Step 1. Expected: total lines at least 95, total branches at least 90, every core file at least 95 lines.

- [ ] **Step 5: Commit**

```powershell
git add backend/app backend/tests/test_unit_coverage_gaps.py
git commit -m "test: close core backend coverage gaps"
```

### Task 6: Cover The Exact MVP API Inventory

**Files:**
- Create: `backend/tests/test_api_inventory.py`
- Modify: existing API tests only where the new error envelope changes assertions

- [ ] **Step 1: Write an exact route-inventory test**

Define the 26 `(method, path)` pairs from the design spec and compare them with routes under `/api/v1`, excluding `HEAD` and `OPTIONS`.

```python
def test_mvp_route_inventory_is_exact():
    actual = {
        (method, route.path)
        for route in app.routes
        if route.path.startswith("/api/v1")
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }
    assert actual == EXPECTED_MVP_ROUTES
```

- [ ] **Step 2: Run and verify the inventory result**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_api_inventory.py::test_mvp_route_inventory_is_exact -q`

Expected: PASS only when all 26 currently documented routes are listed exactly; an accidental new or missing route fails.

- [ ] **Step 3: Add parameterized missing-resource and malformed-body tests**

Assert all relevant GET/POST/PUT routes return the unified envelope. For stateful endpoints seed the minimum valid record, then assert `MAPPING_REVIEW_REQUIRED`, `TASK_STATE_ERROR`, or `PACKAGE_NOT_READY` as appropriate.

- [ ] **Step 4: Run every API test**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/*api*.py tests/test_error_contract.py -q`

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/test_api_inventory.py backend/tests
git commit -m "test: cover complete MVP API inventory"
```

### Task 7: Build True API-Driven General And Policy E2E Tests

**Files:**
- Create: `backend/tests/test_phase9_e2e.py`

- [ ] **Step 1: Write a failing API pipeline helper**

Implement a test-local `run_pipeline(client, fixture_names)` that calls import, schema, template, task, candidates, mapping, optional review, convert, package, and download only through HTTP. Do not seed application tables directly.

- [ ] **Step 2: Verify RED at the first uncovered contract mismatch**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase9_e2e.py -q -x`

Expected: initial failure until helper, unified errors, and fixture handling are complete.

- [ ] **Step 3: Complete both demo assertions**

For each demo verify:

- task status progression and final `completed`;
- canonical fields and `source_candidates`/`source_blocks` rules;
- `content.json`, `content.md`, and `chunks.json` entries;
- validation and consistency `passed`;
- trace includes mapping, transform, render, and package stages;
- manifest excludes itself and every listed byte count/hash matches ZIP bytes;
- response `X-SHA256` equals the downloaded ZIP hash.

- [ ] **Step 4: Run both E2E tests and commit**

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_phase9_e2e.py -q
cd ..
git add backend/tests/test_phase9_e2e.py
git commit -m "test: add API-driven demo pipelines"
```

### Task 8: Stabilize Concurrent Mutations, Retry, And Damaged Packages

**Files:**
- Create: `backend/app/services/task_lock_service.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/api/v1/mappings.py`
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/services/package_service.py`
- Create: `backend/tests/test_phase9_stability.py`

- [ ] **Step 1: Write failing lock and concurrency tests**

Test that two threads cannot enter `task_mutation("task-1")` simultaneously, while different task IDs can. API tests run concurrent convert/package requests against a file-backed SQLite database and assert each response is 200 or deterministic `409 TASK_STATE_ERROR`, with no 500 response.

- [ ] **Step 2: Run and verify RED**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_phase9_stability.py -q`

Expected: FAIL because no task mutation registry exists and concurrent publication is uncontrolled.

- [ ] **Step 3: Implement the process-local mutation guard**

Use a registry-level `threading.Lock` protecting a `dict[str, threading.Lock]`. The context manager acquires the task lock non-blocking and raises `TaskMutationConflict(task_id)` when busy. Always release in `finally`. Inject one shared registry from `app.api.deps` and wrap candidate generation, mapping, review, convert, and package mutations.

- [ ] **Step 4: Add retry and idempotency tests**

Inject a one-shot storage failure during render/package. Assert no temp file/completed package survives, then retry and reach `rendered`/`completed`. Re-run import, candidate generation, mapping, render, and package according to the design semantics and assert record counts plus output hashes.

- [ ] **Step 5: Add the deliberately damaged package test**

Generate staging payload and manifest, alter one payload byte, then call `_verify_manifest_files` and `_verify_zip_payload`. Both must raise a specific SHA mismatch before a completed `OutputPackageRecord` is written.

- [ ] **Step 6: Verify and commit**

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_phase9_stability.py tests/test_phase7_package.py -q
cd ..
git add backend/app backend/tests/test_phase9_stability.py
git commit -m "fix: stabilize concurrent and retried task mutations"
```

### Task 9: Reach The Frontend Coverage Standard

**Files:**
- Create: `frontend/src/__tests__/apiFailures.test.ts`
- Create: `frontend/src/__tests__/workflowPages.test.tsx`
- Modify only for defects proven by failing tests: `frontend/src/api/client.ts`, `frontend/src/pages/*.tsx`, `frontend/src/components/*.tsx`

- [ ] **Step 1: Run frontend coverage and record gaps**

Run: `cd frontend; npm.cmd run test:coverage`

Expected: FAIL below the confirmed 90 line/85 branch thresholds.

- [ ] **Step 2: Add RED API client tests**

Stub `fetch` to cover unified `error.message`, non-JSON errors, 204, request headers, package blob download, and `X-SHA256`. Assert user-facing messages and returned evidence.

- [ ] **Step 3: Add RED workflow page tests**

Test import parse failures and success selection, task list failures/selection, mapping generate/map/review, conversion and optional report 404s, package readiness, package success, object-URL download, and toast expiry with fake timers.

- [ ] **Step 4: Fix only behaviors exposed by failing tests**

Keep API stubs at the typed client boundary and assert visible controls/status. Do not add mobile-specific code.

- [ ] **Step 5: Run coverage, lint, and build**

```powershell
cd frontend
npm.cmd run test:coverage
npm.cmd run lint
npm.cmd run build
```

Expected: at least 90 lines, 85 branches, 90 functions/statements; lint/build pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend
git commit -m "test: cover frontend workflow failure paths"
```

### Task 10: Final Three-Run Stability Gate And Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Mark Phase 9 complete, list coverage commands, unified error shape, badcase location, and desktop frontend gates. Keep Phase 10 features listed as not implemented.

- [ ] **Step 2: Run strict coverage gates**

```powershell
cd backend
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=json:coverage.json --cov-fail-under=95
.\.venv\Scripts\python tests/coverage_gate.py coverage.json
.\.venv\Scripts\python -m ruff check .
cd ..\frontend
npm.cmd run test:coverage
npm.cmd run lint
npm.cmd run build
```

- [ ] **Step 3: Run the complete backend and frontend suites three times**

```powershell
1..3 | ForEach-Object {
  Push-Location backend
  .\.venv\Scripts\python -m pytest -q
  if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
  Pop-Location
  Push-Location frontend
  npm.cmd run test
  if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
  Pop-Location
}
```

Expected: six suite executions pass with no flaky failure.

- [ ] **Step 4: Check repository hygiene**

Run:

```powershell
git diff --check
git status --short
```

Delete generated `coverage.json`, HTML coverage, `.coverage`, and frontend coverage directories if they are not ignored; add stable ignore rules when necessary.

- [ ] **Step 5: Commit documentation and final hygiene**

```powershell
git add README.md .gitignore backend/pyproject.toml frontend/vitest.config.ts
git commit -m "docs: document phase 9 stability gates"
git status --short
```

Expected: clean worktree.

## Completion Gate

Phase 9 is complete only when the design's ten acceptance criteria pass with real command output. The completion report must include measured backend/frontend coverage percentages, all test counts, three-run evidence, the exact four badcase paths, concurrency/retry/damaged-package results, Git commits, and any remaining Phase 10 boundary.
