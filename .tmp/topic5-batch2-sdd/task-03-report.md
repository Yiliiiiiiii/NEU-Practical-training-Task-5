# Task 03 Report: Business Output Metadata Boundary

Status: DONE

## Outcome

- `RenderService` now emits an explicit business-facing `content.json` boundary with `source_metadata`, `document_metadata`, `metadata_template`, `document_summary`, `data`, `blocks`, and `assets`.
- Missing metadata-template and document-summary configurations render as `{}` to preserve the explicit object shape; artifact consistency treats `{}` as the absent-summary representation.
- The deprecated Package 1.1 `metadata` alias is retained because an existing consumer test requires it. It now contains only the recursively sanitized union of source and document metadata; the production comment documents the deprecation.
- Task/document/schema execution identifiers and execution snapshots are no longer rendered into business output.
- Known reports, summaries, traces, report paths, runtime durations, package/task IDs, and credential-shaped keys are recursively removed from every business-output branch. Provider-prefixed secrets and report-path variants are covered by suffix filtering.
- Canonical operational state remains intact for dedicated reports, lineage, and package artifacts. No report, summary, transform, package, or engine redesign was performed.

## TDD Evidence

Initial RED:

```text
backend/.venv/Scripts/python.exe -m pytest \
  backend/tests/test_topic5_convert_api.py::test_inline_business_content_has_explicit_shape_and_no_operational_keys \
  backend/tests/test_topic5_convert_api.py::test_packaged_content_has_explicit_shape_and_no_operational_keys -q

2 failed
Expected failure: content.json had task_id/doc_id/schema_id/execution_snapshot,
lacked source_metadata, and legacy metadata merged the full canonical doc_meta.
```

Second RED added realistic key variants (`topic11_api_key`, `mapping_report_path`):

```text
2 failed
Expected failure: both variants remained under source_metadata/legacy metadata.
```

GREEN for the focused regressions:

```text
2 passed in 1.93s
```

Object-shape RED/GREEN:

```text
test_topic5_document_summary_can_be_disabled
test_topic5_legacy_request_without_metadata_template_remains_valid

RED: 2 failed because metadata_template/document_summary rendered as null.
GREEN: 2 passed in 1.81s after renderer defaults and consistency comparison
were aligned to the explicit empty-object contract.
```

## Verification

Affected render/inline/package/entity/summary/task-execution suite:

```text
106 passed in 14.88s
```

Static checks:

```text
python -m ruff check backend/app backend/tests
All checks passed!
```

`git diff --check` passed. Self-review confirmed the diff is limited to the renderer/consistency output boundary and directly related regression/compatibility assertions. User-owned `.tmp`, `docs/guildline`, and other untracked files were not staged or modified (apart from this required, untracked report).

## Review Fix Evidence

- RED: `test_render_service_sanitizes_only_arbitrary_metadata_branches` failed because nested `metadata_report`, `mapping_trace`, `processing_duration_ms`, `bearer_token`, `doc_id`, and case-variant `SCHEMA_ID` remained in source metadata. The same test also establishes that same-name target field IDs and nested target values in `data` must remain intact.
- GREEN: renderer construction now sanitizes only arbitrary-key source/document metadata, document summary, and block `source_anchor`; top-level output is explicitly constructed, while `data` and fixed block/asset fields are not name-filtered. The deprecated `metadata` alias remains derived only from sanitized source and document metadata.
- Compatibility correction: the classifier keeps business `document_summary.sentence_traces` while filtering the exact internal `field_traces` key and singular operational `_trace` variants.
- Focused boundary/summary/package checks: `4 passed in 2.15s`.
- Affected renderer/inline/package/entity/summary/task-execution suite: `89 passed in 15.41s`.
- Ruff: `All checks passed!` for `backend/app` and `backend/tests`.
- `git diff --check` passed.
