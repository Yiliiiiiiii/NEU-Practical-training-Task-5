# Task 10 Report: Replay, Errors, Resource Limits, and Regex Safety

## Implementation

- Core commit: `348794fe5ca593989047d8bb07a097f60fdd6630`.
- Execution snapshots now contain replay contract 1.0, engine version, input-component fingerprints, and semantic artifact hashes.
- `scripts/replay_topic5_snapshot.py` accepts a snapshot path or path-safe task ID, runs the pure engine without package/task mutation, and reports semantic, conversion-contract, Schema-version, and engine-version differences.
- `Topic5Error` contains error code, stage, path, message, retryability, details, and trace ID. Topic 5 resource failures return this contract without stack traces.
- Configurable limits cover request bytes, UIR blocks, per-block text, assets, entities, target fields, mapping rules, regex length, chunks, output bytes, ZIP bytes, and existing Topic 11 timeout.
- Input limits run before candidate extraction. Output/chunk limits run before packaging. ZIP limits are enforced in the atomic temporary package directory before final rename.
- Regex rules reject backreferences, lookbehind, conditionals, named backreferences, nested repetition, and oversized patterns at contract validation time. SchemaPack negative pairs receive the same validation.
- Storage JSON/text writes now flush and fsync the temporary file before atomic replacement; package writes already use the same atomic pattern.

## Replay evidence

- Dataset: `topic5_replay` v1, public announcement request.
- Evaluated commit: `348794fe5ca593989047d8bb07a097f60fdd6630`.
- Exact same-snapshot replay: semantic match 1.0.
- Changed Schema version: explicit `target_schema_hash` difference.
- Changed engine version: explicit engine-version difference.
- Three cases passed; version difference detection rate 1.0.

## Verification

- Replay/error/resource/regex/ZIP atomicity focused tests: 6 passed before evidence freeze.
- Full Task 10 compatibility run covering inline, registered, package fault injection, SchemaPack validation, and storage atomicity: 110 passed.
- Targeted regression after compatibility fixes: 23 passed.
- Backend Ruff, replay/runtime scripts Ruff, OpenAPI drift check, and diff check passed after regeneration.
- Replay evidence commit: `6f4fbdf7`.
