# Topic 5 Hard-Gap Batch 1 Result

Date: 2026-07-10

## Outcome

The hard-gap batch 1 acceptance gate concludes `passed`. The implementation remains
inside the Topic 5 boundary: normalized UIR to schema-governed deterministic artifacts,
reports, lineage, and Package 1.1. No raw-file parser, OCR, embedding/vector store, RAG,
Topic 6 quality score, LLM judge, or publication router was added.

## Delivered

- Strict metadata templates now control document metadata with safe resolution and traces.
- Content, management, and local quality tags are SchemaPack-configurable.
- Upstream entities pass through without invented IDs; heuristic inference is opt-in only.
- One deterministic extractive document summary is shared by JSON, Markdown, reports, and package metadata.
- Chunking has an offline internal provider and a replaceable, validated Topic 11 HTTP contract.
- Markdown has deterministic document/summary/structured-data/block markers and block hashes.
- Cross-artifact consistency validates JSON, Markdown, summary, metadata, chunks, parents, sources, and entity relevance.
- Feature-aware packages require manifested metadata/consistency reports and include the verifier report in the final manifest.
- Lineage covers metadata, summary sentences, tag traces, entity tags, Markdown blocks, structured fields, and chunks.
- Production field operations execute a safe allowlist; unsupported and unsafe paths are rejected.

## Evidence

| Evidence | Result |
| --- | ---: |
| Field-operation cases | 119 |
| Field-operation accuracy | 1.000 |
| Rename / merge / split accuracy | 1.000 / 1.000 / 1.000 |
| Unsafe operation acceptance count | 0 |
| Schema-localization cases | 40 |
| Stage / path / error-code accuracy | 1.000 / 1.000 / 1.000 |
| Content tag F1 | 0.900 |
| Management / quality tag F1 | 1.000 / 1.000 |
| Gate conclusion | passed |

Machine reports:

- `docs/交接/evidence/hard_gap_batch_1/operations/field_operations.json`
- `docs/交接/evidence/hard_gap_batch_1/operations/schema_localization.json`
- `docs/交接/evidence/hard_gap_batch_1/operations/hard_gap_batch_1_gate.json`

Reproduction:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_topic5_field_operations.py
backend\.venv\Scripts\python.exe scripts\eval_topic5_schema_localization.py
backend\.venv\Scripts\python.exe scripts\check_topic5_hard_gap_batch_1_gate.py
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Set-Location frontend
npm.cmd test
```

## Commits

| Workstream | Commit |
| --- | --- |
| Baseline | `911d5d8a` |
| Contracts | `037c9340` |
| Metadata templates | `db846e61` |
| Configurable/local tags | `0ee15c7b` |
| Entity passthrough and summary | `6faf1ef2` |
| Topic 11 provider | `df822cf0` |
| Artifact consistency | `e052701a` |
| Field operations and localization datasets | `29ead02a` |
| Extended lineage, golden packages, and public docs | `0d039e45` |
| Unsafe operation hardening | `783a8530` |

The final documentation/evidence commit is intentionally recorded by Git history after
this file is committed; embedding its own hash would be self-referential.
