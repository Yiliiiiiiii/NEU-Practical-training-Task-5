# Task 02 Report: Unified Conversion Status Semantics

## RED

Command:

```powershell
cd F:\p2\backend
python -m pytest tests/test_conversion_status_service.py -q
```

Result: expected collection error because
`app.services.conversion_status_service` did not exist (`1 error`).

Command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\python.exe -m pytest tests/test_topic5_convert_api.py::test_topic5_package_verifier_failure_overrides_artifact_consistency_failure tests/test_task_execution_api.py::test_registered_schema_validation_failure_requires_review tests/test_task_execution_api.py::test_registered_package_verifier_failure_overrides_consistency_failure -q
```

Result: `3 failed`. Inline and registered verifier/consistency cases returned
`review_required` instead of `failed`; registered Schema validation failure returned
`completed` instead of `review_required`.

## GREEN

Focused command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\python.exe -m pytest tests/test_conversion_status_service.py tests/test_topic5_convert_api.py::test_topic5_package_verifier_failure_overrides_artifact_consistency_failure tests/test_task_execution_api.py::test_registered_schema_validation_failure_requires_review tests/test_task_execution_api.py::test_registered_package_verifier_failure_overrides_consistency_failure -q
```

Result: `5 passed in 3.10s`.

Affected suite command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\python.exe -m pytest tests/test_conversion_status_service.py tests/test_topic5_convert_api.py tests/test_task_execution_api.py tests/test_topic5_conversion_assertion_integration.py tests/test_topic11_chunk_provider.py -q
```

Result: `69 passed in 15.34s`.

Ruff command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\ruff.exe check app/services/conversion_status_service.py app/services/topic5_conversion_service.py app/services/task_execution_service.py tests/test_conversion_status_service.py tests/test_topic5_convert_api.py tests/test_task_execution_api.py
```

Result: `All checks passed!`.

`git diff --check` also passed for the modified tracked files.

## Changed Files

- `backend/app/services/conversion_status_service.py`
- `backend/app/services/topic5_conversion_service.py`
- `backend/app/services/task_execution_service.py`
- `backend/tests/test_conversion_status_service.py`
- `backend/tests/test_topic5_convert_api.py`
- `backend/tests/test_task_execution_api.py`
- `.tmp/topic5-batch2-sdd/task-02-report.md`

## Concerns

- The shared typed contract covers runtime exceptions, package write failures, and strict
  Topic 11 provider failures. Existing execution compatibility is preserved: registered
  exceptions are still persisted as failed by `_mark_failed`, while inline strict-provider
  failures retain the existing HTTP 422 behavior.
- The provider fallback review policy is supplied through the existing free-form task/request
  `options` key `provider_fallback_requires_review`; fallback remains non-reviewing by default.
- Existing unrelated untracked `.tmp`, `docs/guildline`, and PDF files were not modified or
  staged.

## Review Finding Fix: Required Unmapped Source Presence

The review finding was reproduced before production changes. Both execution callers counted
every required unmapped item as source-present because mapping reports did not expose source
presence.

### RED

Focused command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\python.exe -m pytest tests/test_conversion_status_service.py::test_required_unmapped_only_requires_review_when_source_is_present tests/test_conversion_status_service.py::test_required_unmapped_source_present_count_uses_strict_booleans tests/test_candidate_mapping_services.py::test_mapping_service_records_unmapped_required_fields tests/test_candidate_mapping_services.py::test_mapping_service_marks_source_present_from_generic_aliases tests/test_global_assignment_mapping_service.py::test_global_assignment_required_unmapped_fields_are_reported tests/test_global_assignment_mapping_service.py::test_global_assignment_tracks_source_present_at_candidate_threshold tests/test_topic5_convert_api.py::test_topic5_convert_source_absent_unmapped_reviews_for_schema_validation -q
```

Result: `7 failed`. The status helper tests failed with `AttributeError`; the legacy,
global-assignment, and inline API tests failed with `KeyError: 'source_present'`.

### GREEN

The same focused cases passed after the minimal implementation (`7 passed in 1.78s`). The
legacy source-present regression was then tightened to exercise generic `target_hints`, and a
global-assignment regression confirmed that unrelated/below-threshold candidates are not used
as a source-presence proxy (`3 passed in 0.35s`).

Affected suite command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\python.exe -m pytest tests/test_conversion_status_service.py tests/test_candidate_mapping_services.py tests/test_global_assignment_mapping_service.py tests/test_mapping_repair_service.py tests/test_topic5_convert_api.py tests/test_task_execution_api.py -q
```

Result: `84 passed in 14.88s`.

Ruff command:

```powershell
cd F:\p2\backend
.\.venv\Scripts\ruff.exe check app/services/conversion_status_service.py app/services/mapping_service.py app/services/global_assignment_mapping_service.py app/services/topic5_conversion_service.py app/services/task_execution_service.py tests/test_conversion_status_service.py tests/test_candidate_mapping_services.py tests/test_global_assignment_mapping_service.py tests/test_topic5_convert_api.py
```

Result: `All checks passed!`.

### Implementation Notes

- Legacy mapping records `source_present` by comparing normalized generic target descriptors,
  schema/template aliases, and candidate `source_name`/`display_name`/`target_hints`.
- Global assignment records `source_present` only when a built target pair meets the configured
  minimum candidate score; blocked pairs already produce review items.
- `ConversionStatusService.count_required_unmapped_source_present` strictly counts only items
  whose `required is True` and `source_present is True`; inline and registered callers use it.
- The source-absent inline API regression proves `review_required` comes independently from the
  failed Schema validation report.
