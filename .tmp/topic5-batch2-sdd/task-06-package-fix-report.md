# Task 6 Package Review Fix

## Findings confirmed

The package reviewer findings were reproduced before implementation:

- Rehashing `metadata.json.task_id`, `canonical.json.doc_id`, or a chunk ID allowed strict verification to pass because the semantic consistency checks did not bind exact package inputs.
- Strict verification did not require all contract artifacts and allowed `transform_report.json` to remain on disk without manifest coverage.
- Recreating the same package ID moved the valid final directory away before installing its replacement, creating a visibility gap and a destructive rollback path.
- ZIP creation and verifier hashing followed external symlinks/reparse points.
- A failed verifier result returned a non-empty path to a ZIP that was intentionally not finalized.

## RED evidence

Focused command covered the three operational tamper variants, incomplete manifest, immutable package recreation, verifier and ZIP symlinks, and failed ZIP-path semantics.

Result: `8 failed`.

## Fixes

- Packaged `ArtifactConsistencyReport` now binds exact bytes for `canonical.json`, `content.json`, `content.md`, `chunks.jsonl`, and `metadata.json` through per-file SHA-256 values and a deterministic aggregate fingerprint.
- Independent disk recomputation calculates the same binding, injects it into the recomputed report, and rejects any mismatch with `artifact_input_binding_mismatch`.
- The stored verifier report remains bound to the exact manifest hash; re-verification now checks that trust anchor and rejects a changed manifest.
- Verifier checks expose the exact precomputed consistency-report SHA-256 identity.
- Strict mode requires canonical, transform, and artifact-consistency reports in addition to the base package contract and feature-declared files. Every non-finalization file on disk must be manifest-covered.
- Package tree verification and ZIP creation reject symlinks and Windows reparse points, verify resolved paths remain under the package root, open regular files with `O_NOFOLLOW` where supported, and recheck link state after reads.
- Existing package IDs are immutable. A verified candidate cannot move or replace an existing final directory; it fails without touching the old downloadable package. Initial publication uses `os.rename`, not destructive `os.replace`.
- Verifier failure returns `zip_path=None`; inline and registered status remain `failed` and no partial ZIP is published.

## GREEN evidence

- Focused reviewer probes: `8 passed`.
- Package/API/golden/downstream/registered matrix: `96 passed`.
- Ruff: clean.
- OpenAPI: current, 65 paths.
- `git diff --check`: clean.

## Cross-platform note

Symlink tests execute when the host allows link creation and skip only when Windows policy/privileges prohibit it. Reparse-point detection uses `st_file_attributes` in addition to POSIX symlink mode.
