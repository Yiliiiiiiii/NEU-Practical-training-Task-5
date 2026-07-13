# Topic 5 Batch 2 Task 4 Review Fix Report

Status: DONE

## Review findings addressed

- Separated actual legacy-input provenance from compatibility serialization. Default and nested-only configurations omit the deprecated alias when serialized and do not acquire a warning after revalidation. Actual legacy input retains provenance across serialization boundaries and emits the deterministic report warning.
- Made nested `summary.chunk_mode` the sole runtime and serialization source of truth. The deprecated `summary_mode` API is derived from nested state, and `model_copy(update=...)` cannot make the compatibility alias diverge or invent legacy provenance.
- Preserved real task IDs throughout organizer and internal chunk construction. Document-summary semantic chunk references now normalize only the volatile task namespace to the stable document namespace, so full inline semantic output is deterministic without reverting chunk construction to `doc_id`.
- Versioned the Topic 11 request shape explicitly as `1.1`, synchronized the runtime request model and JSON Schema identity/constant, rejected `1.0` payloads using the `1.1` shape, and enforced non-empty runtime `task_id`.
- Migrated bundled inline examples to nested summary configuration.

## TDD evidence

Focused RED command:

`cd backend; .venv/Scripts/python.exe -m pytest tests/test_chunk_organizer_service.py tests/test_topic11_chunk_provider.py tests/test_topic5_convert_api.py -q`

Result before implementation: 8 failed, 65 passed. Failures covered false legacy provenance after default/nested roundtrip, `model_copy` divergence, request versioning, empty task ID acceptance, full inline document-summary nondeterminism, and nested inline false warning.

Focused GREEN result: 73 passed. Additional default-inline and reverse `model_copy` provenance assertions were then added.

## Final verification

Affected content organization, document summary, artifact consistency, chunk, Topic 11, Topic 11 contracts, SchemaPack, inline, full Topic 5 convert API, and registered execution suites:

`$env:PYTHONPATH='backend;.'; .\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chunk_organizer_service.py backend/tests/test_document_summary_service.py backend/tests/test_artifact_consistency_service.py backend/tests/test_content_organization_retrieval_eval.py backend/tests/test_chunk_retrieval_eval.py backend/tests/test_topic11_chunk_provider.py backend/tests/test_topic5_hard_gap_contracts.py backend/tests/test_schema_pack_service.py backend/tests/test_schema_pack_contract_validation.py backend/tests/test_schema_pack_contract_gate.py backend/tests/test_schema_pack_contract_eval.py backend/tests/test_schemapack_client.py backend/tests/test_schemapack_cli.py backend/tests/test_topic5_inline_schema_pack.py backend/tests/test_topic5_convert_api.py backend/tests/test_task_execution_api.py -q`

Result: 216 passed in 26.00s.

Ruff: `cd backend; .venv/Scripts/ruff.exe check .` — all checks passed.

`git diff --check` passed.

## Scope review

- No transform heuristics, package finalization, or shared/full engine changes.
- No `.tmp`, `docs/guildline`, or user files staged.
