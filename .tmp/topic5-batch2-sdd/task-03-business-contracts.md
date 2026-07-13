# Task 3: Business Output Boundary, Summary Migration, and Transform Compatibility

## Goal

Correct the remaining Batch 1 business-contract leaks and duplicate settings without absorbing upstream normalization.

## Business output

`content.json` must expose explicit top-level sections:

```json
{
  "source_metadata": {},
  "document_metadata": {},
  "metadata_template": {},
  "document_summary": {},
  "data": {},
  "blocks": [],
  "assets": []
}
```

Internal execution snapshots, mapping/transform summaries, metadata reports, traces, and operational identifiers must not appear in business output. Operational data remains in dedicated report artifacts. Retain a deprecated legacy field only if an existing consumer test proves it is required, and it must contain no forbidden/internal key. Add a recursive forbidden-key scan test.

## Summary contract migration

- `summary.chunk_mode` and `summary.document_mode` are the single source of truth.
- Accept legacy top-level `summary_mode`, migrate it when nested value was not explicitly supplied, emit a deprecation warning in the content-organization report, and reject conflicting legacy/new values.
- Update bundled SchemaPack configs to the new form.
- Fix internal chunk construction so real `task_id` is used; never pass `doc_id` as `task_id` when generating IDs.
- Add migration/conflict/deprecation/chunk-ID tests.

## Transform compatibility

- Add `enable_legacy_transform_heuristics`, default `false`.
- With default false, disable implicit document-type maps, special array-field lists, contact cleanup, and organization cleanup unless declared in Schema/mapping rules/metadata template configuration.
- Keep generic target-type conversion (date/datetime/number/array) only as justified by the target field and declared mapping operation.
- With the compatibility flag true, preserve the old behavior for one release.
- Acceptance tests must run with the default false. Existing legacy tests should explicitly opt in.

Use TDD; do not extract the full shared engine yet. Preserve Topic 5 scope. Report to `.tmp/topic5-batch2-sdd/task-03-report.md`.
