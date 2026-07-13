# Task 6 Report: Independent Atomic Packages and Full Chunk Coverage

## Architecture audit and root causes

### Package finalization

- `PackageService` wrote directly into the final `packages/pkg_<task>` directory, so any exception could expose a partial package and overwrite an earlier valid package in place.
- The first verifier report was written, then included in a rebuilt manifest, and a second verifier result was returned without rewriting the stored report. This was circular and allowed the stored and returned verifier results to diverge.
- `PackageVerifierService` trusted the precomputed artifact-consistency report after checksum validation. Rehashing a tampered `content.json` therefore bypassed semantic consistency verification.
- JSON, text, and ZIP writes were direct non-atomic writes; ZIP entry metadata was filesystem-derived and manifest paths were not traversal-validated.
- `OutputPackageMetadata` only exposed the ZIP hash and did not bind the manifest and stored verifier report.

### Chunk coverage

- Artifact consistency validated only whether each chunk cited known source blocks; it never required each canonical non-empty block to appear in a chunk.
- Topic 11 validation required protected blocks but allowed an ordinary paragraph to disappear silently.
- Protected blocks only needed a reference, not exact text preservation.
- Unknown sources and non-derivable text produced issues but no explicit acceptance metrics; duplicates, block coverage, and exclusions had no contract.

## TDD evidence

### Phase B RED then GREEN

- RED command: `python -m pytest backend/tests/test_artifact_consistency_service.py backend/tests/test_topic11_chunk_provider.py -q`
- RED result: `7 failed, 32 passed` for missing metrics, ordinary block omission, exclusions, duplicate/unexplained text, Topic 11 omission, and protected integrity.
- GREEN/final affected command: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_artifact_consistency_service.py backend/tests/test_topic11_chunk_provider.py backend/tests/test_chunk_organizer_service.py -q`
- Result: `58 passed`.
- Ruff: clean.
- Commit: `116a734c fix: require complete canonical block coverage in chunks`.

### Phase A RED then GREEN

- RED cases proved that the manifest included `verifier_report.json`, rehashed content tampering passed with a stale consistency report, and package metadata lacked manifest/verifier/ZIP hashes.
- Initial focused result: `3 failed`.
- Added fault injection for content write, manifest write, verifier execution, ZIP creation, and final directory rename; prior valid-package preservation; stored/returned verifier identity; deterministic safe ZIP entries; and manifest traversal rejection.
- Final package/API/golden/task/downstream command covered 89 tests and passed.

## Implemented contracts

- Manifest covers semantic and report artifacts only; it excludes itself, `verifier_report.json`, and `standard_package.zip`.
- Stored verifier report includes the exact `manifest_sha256` it verified and is the same model returned by the API.
- Output package metadata records `manifest_sha256`, `verifier_report_sha256`, and `zip_sha256` while preserving the legacy `sha256` ZIP alias.
- Verifier reloads canonical, structured JSON, Markdown, chunks, metadata, organization config, and the stored consistency report, reruns `ArtifactConsistencyService`, and rejects a stale or failing recomputation.
- Package builds occur under `packages/.tmp/<package-id>-<random>` and only a verified package directory is finalized. Failure cleans the temporary directory and does not replace an existing valid package.
- JSON/text files use temporary files, flush/fsync where supported, and `os.replace`. ZIP entries are sorted, relative, normalized, traversal-checked, fixed-timestamp, and fixed-mode.
- Artifact consistency now reports `chunk_source_validity`, `canonical_block_coverage`, `nonempty_block_coverage`, `protected_block_integrity`, `duplicate_content_ratio`, `unexplained_chunk_text_count`, and `unknown_source_count`.
- Non-empty canonical blocks require chunk coverage unless an exact configured exclusion has `block_id`, non-empty `exclusion_reason`, and non-empty `rule_id`.
- Topic 11 rejects missing ordinary non-empty blocks and requires exact protected-block text preservation.

## Final verification

- `89 passed` across conversion artifact, Package 1.1 compatibility, procurement, golden packages, inline package API, registered task API, and downstream contract/export tests.
- `58 passed` across artifact consistency, Topic 11 provider, and chunk organizer tests.
- Ruff clean for all changed Python files.
- `scripts/export_openapi.py --check`: current, 65 paths.
- `git diff --check`: clean.

## Scope and limitations

- No mapping/runtime/replay/resource-limit/downstream feature work was introduced.
- `fsync` is best effort on Windows where a read-only ZIP descriptor may reject it; the ZIP is still closed and atomically replaced.
- Directory replacement preserves an existing package through a backup-and-rollback sequence because cross-platform atomic replacement of a non-empty directory is not universally available.
