# Task 6 Chunk Coverage Review Fix

## Review findings reproduced

The reviewer findings were confirmed:

1. A whitespace-only chunk with a known source ID earned source and canonical coverage because coverage was credited before checking meaningful derivability.
2. Protected integrity normalized whitespace, so table/code line breaks and indentation could change without failing.
3. Exclusions accepted whitespace-only evidence and any arbitrary non-empty `rule_id`; Topic 11 trusted the block ID without a deterministic registry contract.
4. Any duplicate text was a hard consistency failure, including intentional parent/child overlap.

## RED evidence

Command:

`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_artifact_consistency_service.py backend/tests/test_topic11_chunk_provider.py backend/tests/test_chunk_organizer_service.py -q`

Result before implementation: `11 failed, 57 passed`.

Failures covered whitespace pseudo-coverage, exact protected whitespace, registry membership, protected exclusion, duplicate metric semantics, and parent/child overlap.

## Fixes

- Coverage is credited only when chunk text is non-whitespace, all sources are known, and text is actually derivable from those sources.
- Whitespace-only chunk text emits `chunk_text_empty`, increments unexplained text, and cannot cover an ordinary source block.
- Protected-only chunks require raw string equality. Legitimately combined chunks require the raw protected source string as an exact substring. No whitespace normalization is used for protected integrity.
- Added typed `BlockExclusionRule` registry. Exclusion fields are stripped and blank values rejected; every exclusion rule must be registered.
- Unknown or protected exclusions are rejected by Topic 11 before provider invocation. Packaged and runtime artifact consistency receive the same registry IDs.
- Protected blocks are never eligible for artifact-consistency exclusion.
- Duplicate text remains observable through `duplicate_content_ratio` but is not a default hard failure.
- Parent/child-linked identical chunks are collapsed into one hierarchy component for duplicate metrics; unrelated duplicate components remain counted.
- New metric fields use `None` for legacy reports instead of fake-green historical defaults; newly generated reports always populate measured values.

## GREEN evidence

- Focused chunk suite: `69 passed`.
- Expanded artifact/chunk/package/golden/inline/registered suite: `147 passed`.
- Ruff: clean.
- OpenAPI regenerated and check-ready: 65 paths.
- `git diff --check`: clean.

## Scope

Package finalization behavior was not changed. Package service/verifier received only the registry-ID propagation needed so independent on-disk recomputation applies the exact same exclusion contract.
