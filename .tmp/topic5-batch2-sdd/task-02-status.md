# Task 2: Unified Conversion Status Semantics

## Goal

Create one deterministic status service and route both inline and registered Topic 5 execution through it.

## Required behavior

Create `backend/app/services/conversion_status_service.py` with an explicit typed input contract. It must return:

- `failed` for unrecoverable runtime exception, package write failure, package verifier failure, strict metadata failure, strict output assertion failure, or strict Topic 11 provider failure;
- `review_required` for mapping review items, a required source-present target field left unmapped, Schema validation failure, non-strict metadata failure, non-strict assertion error, summary faithfulness failure, artifact consistency failure before packaging, or provider fallback when policy requires review;
- `completed` only when none apply.

Package verifier failure is always `failed`, even when artifact consistency also failed. Registered execution must include `validation_report.passed` in its status input. Inline and registered paths must no longer own separate status algorithms.

## Tests

1. Add a truth-table/unit test that enumerates combinations (a full Cartesian enumeration or equivalent exhaustive parametrization) and verifies failure precedence, review precedence, and completed only for all-clear.
2. Add registered-task regression: Schema validation failure cannot produce completed.
3. Add inline and registered regression: package verifier false plus artifact consistency false is failed.
4. Cover strict/non-strict metadata, assertions, and Topic 11 fallback/provider failure semantics already exposed by current paths.

Use TDD and preserve public response compatibility. Do not refactor the full conversion engine in this task. Current `.git` may be read-only; do not bypass it. Report focused RED/GREEN commands and changed files in `.tmp/topic5-batch2-sdd/task-02-report.md`.
