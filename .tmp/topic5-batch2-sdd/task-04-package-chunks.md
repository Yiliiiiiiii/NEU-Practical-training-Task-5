# Task 4: Independent Atomic Packages and Full Chunk Coverage

## Goal

Make package finalization non-circular and atomic, and prevent Topic 11 or internal output from silently dropping canonical content.

## Package contract

- `manifest.json` covers all semantic/report artifacts except itself, `verifier_report.json`, and the ZIP.
- `verifier_report.json` records the exact manifest hash it verified.
- `OutputPackageMetadata` records manifest hash, verifier-report hash, and final ZIP hash.
- The API returns exactly the verifier report stored in the package; no first/second-pass mismatch.
- The verifier independently reloads `canonical.json`, `content.json`, `content.md`, `chunks.jsonl`, `metadata.json`, and the precomputed consistency report, then reruns `ArtifactConsistencyService` from disk. It must reject content tampering even when manifest hashes are recomputed and the stale consistency report says passed.
- Build under `packages/.tmp/<package-id>-<random>/`; only atomically rename a successfully verified final directory. On any content/manifest/verifier/ZIP/final-rename failure, clean temp artifacts, leave no downloadable partial ZIP, and preserve an existing valid package.
- JSON/text writes use temporary file, fsync where practical, and atomic replace. ZIP entries are sorted, normalized, traversal-safe, and deterministically timestamped where practical.

## Chunk coverage

Add metrics and validation for `chunk_source_validity`, `canonical_block_coverage`, `nonempty_block_coverage`, `protected_block_integrity`, `duplicate_content_ratio`, `unexplained_chunk_text_count`, and unknown source count. Defaults require 100% non-empty/protected block coverage and zero unexplained/unknown sources. An exclusion is valid only with exact `block_id`, non-empty `exclusion_reason`, and `rule_id` in deterministic configuration.

Both Topic 11 adapter validation and packaged artifact consistency must reject an ordinary non-empty paragraph being dropped. Preserve protected block text/integrity.

## Tests

Use TDD for stale consistency after rehashed tampering, stored/returned verifier identity, all five fault stages, prior package preservation, ZIP traversal safety/determinism, ordinary block omission, exclusions, duplicates, unexplained text, and unknown sources. Run affected package/chunk/golden tests and Ruff. Report to `.tmp/topic5-batch2-sdd/task-04-report.md`.
