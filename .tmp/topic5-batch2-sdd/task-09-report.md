# Task 9 Report: Unified Runtime, Strict Options, and Fingerprints

## Runtime convergence

- Pure engine commit: `185ba08c742fe8277fd741917625ea8922cafa8c`.
- `Topic5ConversionEngine` contains candidate extraction, mapping/repair, transform, metadata, canonical construction, rendering, Topic 11 provider resolution, chunk organization, summary, validation, consistency, assertions, status inputs, and fingerprints.
- The pure engine does not access the database, write files, build packages/ZIPs, or construct HTTP responses.
- `Topic5ConversionService` and `TaskExecutionService` are adapters over the same engine. Package persistence, review knowledge, lineage, database state, and HTTP response construction remain outside it.

## Strict execution options

- `Topic5ExecutionOptions` is strict and versioned (`1.0`).
- Known mapping, threshold, strictness, LLM, repair, lineage, package, compatibility, provider, candidate, negative-pair, calibration, and SchemaPack controls are typed.
- Legacy option dictionaries emit a deprecation warning. Unknown legacy keys emit an explicit rejection-from-execution warning; strict migration mode raises instead of silently ignoring them.
- Conflicting top-level and nested threshold values are rejected.

## Deterministic fingerprints

- Conversion inputs hash canonical UTF-8 JSON with sorted keys, stable separators, normalized newlines, and no task IDs.
- Semantic hashes cover structured data, document metadata, document summary, canonical blocks, chunks, tag traces, entity tags, and operational-field-stripped reports.
- Operational IDs, timestamps, durations, ZIP/absolute paths, task-specific mapping/candidate/chunk IDs, and adapter input-mode labels are excluded from semantic hashes.
- Registered executions persist `fingerprints.json` and include both fingerprint groups in the execution snapshot; inline responses return them directly.

## Equivalence evidence

- Dataset: `topic5_runtime_equivalence` v1; SHA `1f7dc37ea31beb11a52dfaa01ba4c5ec4d74ee0f0461caca4d0a2fcb1578426f`.
- Evaluated engine commit: `185ba08c742fe8277fd741917625ea8922cafa8c`.
- Cases: announcement, event notice, general, meeting, and policy documents.
- Result: 5/5 passed; `inline_registered_semantic_equivalence = 1.0`; no failed cases.
- Claim boundary: public Topic 5 fixtures and reports with operational identifiers excluded.

## Verification

- Inline/registered/strict-option/fingerprint focused run: 77 passed.
- Wider runtime/status/assertion run: 92 passed.
- Equivalence/options/evaluator run: 11 passed.
- Backend Ruff and changed-script Ruff clean; diff check clean.
- Equivalence evidence commit: `513c2c57`.
