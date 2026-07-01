# Real-world UIR Dataset

## Purpose

The real-world UIR dataset tests SchemaPack Agent against traceable public
documents rather than synthetic inputs alone. It does not expand the production
runtime boundary: the product still starts from UIR input.

## Distribution

Current committed distribution:

```text
general_doc: 3
meeting_doc: 3
policy_doc: 5
procurement_doc: 5
total: 16
```

The dataset includes official public HTML pages and text-layer PDFs. Scanned
documents and OCR workflows remain outside the toolchain.

## Source Manifest And Cached Sources

The source manifest is:

```text
examples/real_world/sources/source_manifest.json
```

The collector downloads bounded public sources into an ignored local cache and
records source URL, source site, retrieval timestamp, source format, SHA-256,
and extraction method. Remove the cache at any time and rebuild it from the
manifest.

Sources must be public official material that is accessible without login,
payment, CAPTCHA, or anti-bot bypass. Private records, copied mirrors,
news/social posts, paid material, and personal-information-heavy sources are
excluded.

## Deterministic Extraction And Validation

From `F:\p2`, run:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

Outputs include:

- `examples/real_world/reports/extraction_report.{json,md}`
- `examples/real_world/reports/validation_report.{json,md}`
- generated UIR JSON files under `examples/real_world/uir/`

Validation checks the strict `UIRDocument` model, filename/doc_id alignment,
document type, HTTP(S) source URL, traceability metadata, SHA-256 shape, block
minimums, unique block IDs, non-empty text blocks, parseable tables, mojibake
markers, privacy patterns, assisted-candidate evidence, and review-required
flags for low-confidence candidates.

## Gold Labels, Badcases, And Retrieval Queries

Additional evaluation labels live under `examples/real_world/gold/`:

- `mapping_gold.jsonl`: 16 source-backed mapping rows with source paths,
  expected mappings, review-required items, and embedded badcases.
- `real_world_badcases.jsonl`: deterministic flattened badcase view.
- `retrieval_queries.jsonl`: 32 retrieval queries, two per real UIR, with
  relevant source block IDs.

The retrieval evaluator is deterministic and lightweight. It measures chunk
ranking evidence, not a full RAG/vector-search service.

## API-Backed Evaluation

Start the backend from `F:\p2`:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Run the real-world evaluators from another `F:\p2` terminal:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_knowledge_loop_real_world.py --base-url http://127.0.0.1:8000 --timeout 60
```

Offline report commands:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
```

If API-key authentication is enabled, pass the API key at runtime where the
script supports it. Keys are sent as headers and must not appear in reports.

## Current Evaluation Results

Current committed real-world evidence records:

- dataset size: 16;
- imports: 16/16;
- task executions: 16/16;
- package verification: 16/16;
- real-world mapping badcase violations: 0;
- real-world mapping recall: `0.42592592592592593`;
- procurement required coverage: 1.000;
- generic required coverage in the procurement comparison: 0.333;
- content retrieval query count: 32;
- content retrieval `Recall@3`: 1.000.

Strict validation currently passes for the five `procurement_doc` samples. The
other 11 samples (`general_doc` 0/3, `meeting_doc` 0/3, `policy_doc` 0/5)
remain review-required due to unmapped or ambiguous fields and are not claimed
as field-valid.

Primary reports:

- `reports/real_world_eval_report.{json,md}`
- `reports/real_world_mapping_eval_report.{json,md}`
- `reports/procurement_doc_eval_report.{json,md}`
- `reports/content_organization_retrieval_eval.{json,md}`
- `reports/knowledge_loop_eval_report.{json,md}`
- `reports/real_world_knowledge_loop_report.{json,md}`

## Limitations

- HTML layout heuristics cannot perfectly isolate every government content
  template.
- PDF heading detection is conservative and depends on available font metadata.
- Complex merged-cell tables are flattened into field/value rows.
- The collector is intentionally small-scale and sequential.
- No LLM is required for deterministic generation.
- Procurement schema aliases require continued real-sample review.
- Gold labels are coursework-scale evaluation labels, not an enterprise
  benchmark.
- OCR, scanned PDFs, image parsing, full RAG/vector search, and model training
  remain outside the implemented dataset/evaluator boundary.

## 2026-07 Dataset Expansion

The manifest now covers 30 UIR documents across general, meeting, policy, and
procurement schemas. Mapping gold, badcases, retrieval queries, and content
organization gold reference those UIR block IDs. The current API-backed run
reports 30 imports, 30 executions, and 30 verifier-passing packages.
