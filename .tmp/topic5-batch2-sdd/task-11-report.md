# Task 11 Report: Performance, Concurrency, Faults, and Downstream Exports

## Implementation

- Verified downstream export commit: `7daa9902`.
- Reliability evaluator and frozen fixture commit: `7fb7e762471338340dfb84452f22e188d6c4fb29`.
- Verified packages now provide deterministic flat business JSON, flat/nested-aware CSV, RAG JSONL, and training JSONL exports.
- All exporters reject checksum-invalid or unverified packages. ZIP consumption rejects traversal and symlink entries.
- Source links, entity tags, document IDs, Schema versions, and template versions are preserved. CSV serializes nested fields as canonical JSON and reports their paths.
- Performance fixtures cover 10, 100, 1,000, and 10,000 mixed UIR blocks with headings, paragraphs, lists, tables, entities, metadata, and candidate labels.
- The pure conversion engine records candidate extraction, mapping, transform, metadata, canonical, render, chunk, validation, verification, and total stage durations.

## Evidence

- Performance: 4/4 fixtures passed on Windows 11, Python 3.13.5, 16 logical CPUs. The 10,000-block fixture measured 38,521.327 ms total and 248,084,557 peak Python-allocation bytes. The 1,000-to-10,000 duration ratio was 12.145 for a 10x input increase; no quadratic blow-up was detected.
- Concurrency: 10/10 HTTP package requests reached terminal status, package verification rate was 1.0, task/package IDs were unique, identical inputs had identical semantic hashes, distinct groups stayed isolated, and request configuration was not mutated.
- Package faults: content, manifest, verifier, ZIP, and final-rename injections all reported the expected stage. Partial final-package survival and temporary cleanup failures were both 0. An existing verified package retained the same ZIP hash after a conflicting replacement attempt.
- Downstream: 16/16 verified-package exports passed across announcement, event notice, nested/array, and larger fixtures. Invalid-checksum acceptance was 0; source-link, entity-tag, version, Unicode, and deterministic-output checks passed.

## Verification

- Focused Task 11 and compatibility tests: 43 passed.
- Backend and changed-script Ruff checks passed.
- Performance claims are limited to the recorded host; no absolute production SLO is claimed.
- External blind mapping remains `not_run`; no production-blind 0.85 claim is made.
