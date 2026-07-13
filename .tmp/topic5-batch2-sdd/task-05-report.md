# Task 5 report: legacy transform compatibility

## Scope implemented

- Added typed `enable_legacy_transform_heuristics: bool = False` fields to registered task creation, External UIR task creation, and inline Topic 5 conversion requests.
- Propagated the typed value through inline conversion and registered task persistence/execution.
- Made document-type maps, field-ID-specific array splitting, contact cleanup, and organization cleanup opt-in in `TransformService`.
- Preserved target-type-driven date/datetime/number/array conversion and declared enum maps/transform rules with the compatibility flag disabled.
- Added deterministic per-field trace markers and a sorted, de-duplicated transform warning only when an enabled legacy heuristic changes a value.
- Converted existing tests whose purpose is legacy heuristic behavior to explicitly opt in.
- Regenerated `docs/openapi.json` for all three request contracts.

## TDD evidence

Initial RED run:

`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transform_legacy_compatibility.py -q`

- 4 failed.
- Default coercion mapped `policy_doc` to `policy`.
- `_coerce_value` and `transform` did not accept the compatibility flag.
- No deterministic transform warning/trace evidence was available.
- Registered, External UIR, and inline request models did not expose the typed field.

A later RED regression proved that a declared `enum_maps` conversion was incorrectly classified as a legacy heuristic when compatibility was enabled. The implementation now distinguishes declared enum mapping from the implicit document-type map.

## SchemaPack and evaluator audit

- No bundled SchemaPack edit was required. The announcement and event-notice packs already declare their required business behavior through `transform_rules` (`normalize_date`/`normalize_datetime`, `trim`) and do not rely on the four disabled implicit heuristics for their accepted fixtures.
- Inline, registered, SchemaPack, and evaluator payloads that do not opt in resolve to the typed/default value `false`.
- `scripts/eval_production_like.py` calls `TransformService.transform` without the compatibility argument and therefore runs on the new default-off path.
- Topic 5 inline evaluator request models also omit the field and therefore validate to `false`.

## Verification

- Focused RED-to-GREEN suite: 5 passed.
- Transform + inline/registered + SchemaPack + evaluator affected suite: 167 passed in 28.03s.
- Additional inline/SchemaPack regression group: 148 passed in 19.37s.
- Ruff on all changed Python files: passed.
- `scripts/export_openapi.py --check`: passed, 65 paths current.
- `git diff --check`: passed (only Windows LF/CRLF notices).

Isolated pre-existing/cross-task failure observed while widening verification:

- `test_topic5_hard_gap_golden_packages.py` had 2 failures (announcement and event_notice) and 45 other tests passed in that run.
- The failures compare hashes across three conversions after Task 4 began using real generated task IDs in chunk identity. They are in the semantic-hash normalization layer and are unrelated to transform compatibility. Per root coordination, that Task 4 follow-up is intentionally not included in this commit.

## Self-review

- Compatibility evidence is emitted only for actual implicit conversions; declared enum mappings are not mislabeled.
- Default array behavior remains target-type conversion (`str` to one-element array), while field-specific splitting is opt-in.
- The feature does not introduce the later strict execution-options model or alter Topic 4 cleanup.
- No `.tmp`, `docs/guildline`, PDF, or unrelated user file is intended for staging.
