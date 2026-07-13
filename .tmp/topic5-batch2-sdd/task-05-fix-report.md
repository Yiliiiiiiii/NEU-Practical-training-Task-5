# Task 5 review fix: applied legacy evidence only

## Reviewer findings verified

1. An enabled legacy array heuristic treated `"Alice" -> ["Alice"]` as applied even though generic target-type array coercion produces the same result.
2. With compatibility disabled, SPLIT_ARRAY_FIELDS still received field-specific `quality_flags` and `list_field_normalizer_v2` trace metadata even though only generic array wrapping ran.

Both findings reproduced against commit `90c2e58d`.

## RED evidence

Added regressions for:

- default-off single-value generic array wrapping;
- default-off multi-value text remaining a single array item;
- enabled single-value legacy no-op;
- enabled multi-value legacy split;
- declared `split` transform rule remaining rule-driven.

Initial focused result: 3 failed, 7 passed. The failures were the two default-off normalizer assertions and the enabled single-value no-op warning assertion. Enabled multi-value evidence and declared rule behavior already passed.

## Fix

- When compatibility is enabled, compute the corresponding generic target-type coercion and classify a legacy heuristic as applied only when the legacy result differs from that generic result.
- Emit `quality_flags` and `list_field_normalizer_v2` only for an actually applied `field_specific_array_split`.
- Describe ordinary target-type array wrapping as `target_type_array_wrap` without legacy trace or warning evidence.
- Leave declared split-rule trace and output unchanged.

## Verification

- Focused compatibility suite: 10 passed.
- Transform/inline/registered/SchemaPack/evaluator affected suite: 172 passed in 27.90s.
- Ruff on changed files: passed.
- OpenAPI drift check: current, 65 paths.
- `git diff --check`: passed (Windows line-ending notices only).

Only `backend/app/services/transform_service.py` and `backend/tests/test_transform_legacy_compatibility.py` are in commit scope. `.tmp` and user files remain untracked.
