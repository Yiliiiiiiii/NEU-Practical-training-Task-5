# Topic 5 Batch 2 Task 4 Second Review Fix Report

Status: DONE

## Findings addressed

- Restored `DocumentSummary.source_chunk_ids` as real references to emitted chunks. Runtime task IDs remain part of the real chunk IDs; deterministic tests compare stable semantic fields separately and assert referential integrity on every run.
- Added an input-only, excluded Pydantic field with validation alias `summary_mode`. Validation JSON Schema and OpenAPI now explicitly accept the deprecated one-release input while nested `summary.chunk_mode` remains the runtime and serialization source of truth.
- Regenerated `docs/openapi.json` and verified it has no drift.

## Verification

- Focused migration/OpenAPI/inline tests: 59 passed.
- Full affected Task 4 matrix, including content organization, summaries, consistency, chunk/provider, Topic 11 contracts, SchemaPack, inline/registered execution, full convert API, and OpenAPI export: 220 passed in 28.74s.
- Ruff: all checks passed.
- `scripts/export_openapi.py --check`: passed.
- `git diff --check`: passed.

## Scope

- No transform heuristics, package finalization, or shared/full engine changes.
- `.tmp` and user-owned `docs/guildline` files remain untracked and unstaged.
