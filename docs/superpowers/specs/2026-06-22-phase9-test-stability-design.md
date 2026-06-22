# Phase 9 Test And Stability Design

## Purpose

Phase 9 turns the Phase 0-8 implementation into a measurable, repeatable, failure-tolerant desktop product baseline. It adds no Phase 10 product capabilities. The work focuses on test depth, API error consistency, versioned badcases, concurrency behavior, retry safety, idempotency, atomic storage, and regression evidence.

## Confirmed Quality Bar

The accepted quality standard is risk-weighted rather than a vanity 100 percent target:

- Backend total line coverage: at least 95 percent.
- Backend total branch coverage: at least 90 percent.
- Core backend modules under `app/engines`, `app/services`, `app/validators`, and `app/api/v1`: at least 95 percent line coverage per file, with no unreviewed exclusions.
- Frontend total line coverage: at least 90 percent.
- Frontend total branch coverage: at least 85 percent.
- Every MVP API route has success, malformed request, missing resource, and relevant state-conflict coverage.
- The complete backend and frontend suites pass three consecutive times without flaky failures.

Coverage exclusions are limited to package marker files and executable bootstrap lines that cannot contain business behavior. Every exclusion must be visible in version-controlled configuration; inline `pragma: no cover` is not allowed merely to satisfy the threshold.

## Scope

### Included

1. Complete unit coverage for schema validation, candidate extraction, mapping, transformation, canonical construction, rendering, validators, manifest generation, storage, and packaging.
2. Contract tests for all 26 MVP API routes currently registered under `/api/v1`.
3. General-document and policy-document end-to-end pipelines from UIR import through ZIP verification.
4. Four versioned badcase fixtures under `examples/badcases/`:
   - missing required field;
   - invalid type conversion;
   - ambiguous mapping requiring review;
   - broken block provenance link.
5. Unified error responses for request validation, missing resources, schema errors, review requirements, task state conflicts, package readiness, and unexpected errors.
6. Failure traces and task-state assertions for task-scoped workflow failures.
7. Atomic JSON and text writes, deterministic retry behavior, concurrent mutation protection, and package corruption checks.
8. Backend and frontend coverage commands enforced by fail-under thresholds.
9. README updates describing Phase 9 quality gates.

### Excluded

- Real model fallback.
- Task replay and `parent_task_id`.
- Independent external verifier CLI.
- Frozen 30-document evaluation dataset and formal accuracy claims.
- Authentication, remote deployment, multi-node distributed locking, and mobile UI work.

These remain Phase 10 or later work.

## Architecture

### 1. Coverage Infrastructure

The backend adds `pytest-cov` and records line plus branch coverage through `coverage.py`. A version-controlled `backend/tests/coverage_gate.py` reads `coverage.json` and independently enforces total line coverage, total branch coverage, and per-file coverage for core modules. The frontend adds `@vitest/coverage-v8`. Thresholds live in the backend gate and `frontend/vitest.config.ts`, so the same local commands and future CI commands fail when coverage regresses.

Coverage reports are generated into ignored runtime directories and are not committed. Test commands remain deterministic and make no network calls.

### 2. Unified API Error Contract

All API errors use the existing public model:

```json
{
  "error": {
    "code": "TASK_STATE_ERROR",
    "message": "task status 'created' is not ready for packaging",
    "details": []
  }
}
```

`app/errors.py` owns typed application exceptions. `app/main.py` installs exception handlers for application errors, FastAPI request validation, HTTP fallback errors, and unexpected exceptions. Routers translate existing service exceptions at their ownership boundary instead of exposing FastAPI's default `detail` shape.

Error mapping:

| Condition | HTTP | Code |
| --- | ---: | --- |
| Invalid body/query/path | 422 | `VALIDATION_ERROR` |
| Missing document/task/schema/template/report/package | 404 | `NOT_FOUND` |
| Invalid Target Schema or Template binding | 400 | `SCHEMA_INVALID` |
| Mapping still requires review | 409 | `MAPPING_REVIEW_REQUIRED` |
| Other illegal task transition | 409 | `TASK_STATE_ERROR` |
| Rendered outputs/package prerequisites missing | 409 | `PACKAGE_NOT_READY` |
| Unexpected server failure | 500 | `INTERNAL_ERROR` |

Validation details contain stable dotted paths and messages. Internal exception types, file paths, SQL text, and stack traces are never returned to clients. Frontend error extraction continues to support this format.

### 3. Trace And Task-State Policy

Request-shape failures without a valid task ID cannot write a task trace. Once a task is resolved, workflow endpoints record a failure trace containing stage, action, reason, and status.

State rules:

- Precondition failures preserve the prior state: missing review, package not ready, or duplicate in-flight request.
- Terminal transformation, rendering, validation, consistency, or package I/O failures set the task to `failed` and persist error code/message.
- A retry after a recoverable precondition or injected I/O failure must not reuse partial files.
- A successful retry clears task error fields and reaches the same final state as a first-attempt success.

### 4. Atomic Storage And Concurrent Mutations

`StorageService.save_json` and `write_text` write UTF-8 bytes to a temporary sibling file, flush and close it, and publish with `Path.replace`. A failed publish removes the temporary file and leaves the previously published destination unchanged.

Task-mutating operations use a process-local task lock registry. Concurrent operations for the same task are serialized or rejected with deterministic `409 TASK_STATE_ERROR`; operations for different tasks remain independent. This is a single-process stabilization guarantee, not a distributed lock claim.

Concurrency tests use a file-backed SQLite database and real storage directories. They verify:

- concurrent duplicate UIR import does not corrupt JSON or create duplicate records;
- concurrent conversion/package attempts do not publish partial artifacts;
- concurrent package requests produce valid packages or a deterministic conflict, never a corrupt ZIP;
- no `.tmp` files remain after success or injected failure.

### 5. Retry And Idempotency Semantics

- Re-importing the same `doc_id` updates one document record and publishes valid UIR JSON.
- Re-running candidate generation replaces or deterministically refreshes candidates without multiplication.
- Re-running mapping leaves one current mapping set and a valid mapping report.
- Re-running render from unchanged canonical input produces byte-identical `content.json`, `content.md`, and `chunks.json`.
- Re-running package creates a new package ID by the existing contract; each ZIP is independently valid, and download returns the newest completed record.
- Retrying after an injected atomic-write failure succeeds without orphan records or partial files.

### 6. Badcase Fixtures

Badcases are version-controlled inputs, not generated runtime output:

```text
examples/badcases/
├── badcase_missing_required.json
├── badcase_type_error.json
├── badcase_mapping_ambiguous.json
└── badcase_broken_block_link.json
```

Each fixture includes a `case_id`, description, input object, target schema/template references where needed, expected HTTP/error code or validator issue, expected task state, and expected trace action. Tests validate the fixture schema before using it, preventing silent fixture drift.

### 7. Test Layers

#### Unit tests

Tests exercise real engines, services, validators, renderers, and storage with focused inputs. Edge coverage includes empty values, Unicode metadata, unsupported casts, date failures, split/merge provenance, required/default interactions, block backlink integrity, unsafe paths, manifest ordering, SHA mismatches, and ZIP traversal entries.

#### API contract tests

A route inventory test compares FastAPI's registered MVP routes against a versioned expected route set. Parameterized tests assert the unified error envelope and route-specific codes. Existing endpoint-specific tests remain the source of detailed success behavior.

#### End-to-end tests

Both demo scenarios run through:

```text
import -> schema -> template -> task -> candidates -> mapping
-> review when required -> convert -> package -> download -> unzip -> verify
```

Verification checks database state, trace stages, canonical provenance, three render outputs, reports, manifest entries, ZIP SHA-256, and task status.

#### Frontend tests

Vitest covers API URL/error/download behavior, import validation, task selection, mapping review, conversion/report loading, package generation/download, toast expiry/dismissal, and workflow state presentation. Network behavior uses explicit fetch stubs at the client boundary; component assertions focus on user-visible behavior.

#### Stability tests

Dedicated tests cover concurrency, retry, idempotency, atomic write failure, damaged manifest entries, altered ZIP bytes, missing required files, malformed JSON, and historical regressions from Phase 5-8 acceptance fixes.

## Damaged Package Requirement

Phase 9 must contain at least one deliberately damaged package. Because the independent external verifier is Phase 10, the damaged package is tested against internal package verification methods and consistency/manifest checks. The test alters a payload byte after manifest generation and proves verification rejects it before any completed package record or downloadable artifact is published.

## Quality Commands

Backend:

```powershell
cd backend
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=95
.\.venv\Scripts\python -m coverage json -o coverage.json
.\.venv\Scripts\python tests/coverage_gate.py coverage.json
.\.venv\Scripts\python -m ruff check .
```

Frontend:

```powershell
cd frontend
npm run test:coverage
npm run lint
npm run build
```

Stability repetition:

```powershell
1..3 | ForEach-Object {
  .\.venv\Scripts\python -m pytest -q
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

The final acceptance run also executes `git diff --check` and requires a clean worktree after the Phase 9 commits.

## Acceptance Criteria

Phase 9 is complete only when:

1. Tasks 9.1-9.5 from the revised implementation document are demonstrably covered.
2. The confirmed backend and frontend coverage thresholds pass.
3. All MVP routes match the expected inventory and return the unified error envelope on failures.
4. Both demo E2E pipelines pass and verify the real ZIP payload.
5. All four badcase fixtures are committed and exercised.
6. Concurrency, retry, idempotency, atomic write, and damaged-package tests pass.
7. Workflow failures have correct trace and task-state evidence.
8. Three consecutive full-suite runs pass without flakes.
9. Ruff, ESLint, frontend build, and Git whitespace checks pass.
10. No Phase 10 capability is introduced or claimed.
