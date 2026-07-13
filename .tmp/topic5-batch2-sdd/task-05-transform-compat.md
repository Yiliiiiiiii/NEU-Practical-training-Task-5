# Task 5: Disable Legacy Domain Transform Heuristics by Default

- Introduce `enable_legacy_transform_heuristics`, default `false`, in the typed Topic 5 execution path available at this stage.
- With false, disable implicit document-type maps, field-ID-specific array splitting, contact cleanup, and organization cleanup. The default core may transform only what Target Schema, Mapping Rules, or Metadata Template declares.
- Keep generic type conversion (date/datetime/number/array) only when justified by target type and declared mapping/transform rule; do not absorb Topic 4 cleanup.
- With true, preserve prior behavior for one compatibility release and emit trace/warning evidence that legacy heuristics were used.
- Update bundled SchemaPack configuration to declare any business mappings it still needs. Acceptance/evaluator paths must use false.
- Convert existing tests that intentionally exercise legacy behavior to explicitly opt in; add default-off regressions.

Use TDD; do not implement strict execution-options model or shared engine yet. Run transform, inline/registered, SchemaPack and evaluator affected tests plus Ruff. Report to `.tmp/topic5-batch2-sdd/task-05-report.md`; scoped commit `refactor: move legacy transform heuristics behind compatibility flag`; never stage `.tmp` or user files.
