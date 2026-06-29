# Real-world UIR Dataset

## Purpose

This dataset tests SchemaPack Agent against traceable, publicly accessible documents rather
than synthetic inputs alone. It does not change the product boundary: the production
conversion pipeline still begins with UIR.

## Source scope

Sources must be official public webpages or official attachments that:

- are accessible without login, payment, CAPTCHA, or anti-bot bypass;
- contain policy, procurement, meeting, contract, or public service information;
- do not primarily contain personal information;
- can be cited with a stable source URL and source site;
- permit coursework evaluation use as public official material.

News-media long-form articles, social posts, private records, paid material, and copied
third-party mirrors are excluded.

## Supported formats

- HTML pages, extracted with BeautifulSoup and lxml.
- PDFs with a usable text layer, extracted with PyMuPDF.
- DOCX files, extracted with python-docx.
- UTF-8 TXT files as a small compatibility format.

Scanned PDFs, images, encrypted documents, and pages requiring authentication are not
supported. Image-only PDFs are marked `unsupported_scanned_pdf`; OCR is intentionally
outside this toolchain.

## UIR generation

The source manifest drives four deterministic stages:

```text
official URL
  -> bounded local download and SHA-256
  -> format-specific text/table extraction
  -> current-schema UIR assembly
  -> structural/privacy validation
  -> existing SchemaPack HTTP API and package verifier
```

The existing strict `UIRDocument` model uses `doc_id` rather than a new `uir_id`. Source
traceability is stored under `metadata`:

- `source_url`
- `source_site`
- `retrieved_at`
- `source_format`
- `source_sha256`
- `extraction_method`
- `doc_type` and `domain`

Each UIR also sets `source.source_type` to `real_world_public_document`. Heading, paragraph,
list, and table blocks use the existing `UIRBlock` shape. PDF page numbers are retained in
`source_anchor`; HTML and DOCX structure details stay in `attributes`. To avoid embedding
an entire long publication, generated UIR files retain at most 250 blocks and record
`extracted_block_count` plus `extraction_truncated` in metadata.

## Quality and privacy validation

`scripts/validate_real_world_uir.py` verifies:

- valid JSON accepted by the existing Pydantic UIR schema;
- matching filename and `doc_id`;
- a supported document type and valid HTTP(S) source URL;
- required traceability metadata and a lowercase 64-character SHA-256;
- at least three blocks, unique block IDs, non-empty text blocks, and parseable table rows;
- absence of common mojibake markers;
- absence of likely mobile numbers, identity-card numbers, personal email addresses, and
  bank-card numbers;
- evidence on assisted field candidates;
- `review_required=true` for low-confidence candidates.

Rejected files are moved only within `examples/real_world/uir/_rejected/`, and every
finding is written to JSON and Markdown reports.

## Dataset scale and distribution

The minimum release contains 16 validated UIR files:

| Document type | Minimum |
| --- | ---: |
| `policy_doc` | 5 |
| `procurement_doc` | 5 |
| `meeting_doc` | 3 |
| `general_doc` | 3 |

The first gate is five pilot documents: three HTML pages and two text-layer PDFs. Expansion
to 16 happens only after all pilots import and execute and at least four pilot packages pass
verification.

Natural badcases are selected to cover ambiguous dates, multiple amounts, similar
organizations/roles, irregular heading hierarchy, and complex tables. These remain
evaluation inputs, not automatically accepted gold truth.

The current dataset contains 16 validated sources: 5 policy, 5 procurement, 3 meeting,
and 3 general documents. Thirteen sources are HTML pages and three are text-layer PDFs.
The latest live HTTP evaluation imported and executed all 16 samples, and all 16 generated
packages passed the package verifier. Eleven downstream schema validations still report
missing or ambiguous target fields; these are retained as real-world mapping badcases and
review evidence rather than silently filled.

## Evaluation catalog routing

Each supported document type uses an explicit versioned entry in
`scripts/eval_real_world_uir.py`'s `DOCUMENT_CATALOG`. Procurement samples use
`procurement_doc` schema `1.0.0` with `procurement_doc_base_v1` template `1.0.0`; they
never route through `general_doc`.

The evaluator checks that the configured local schema and template fixtures exist before
importing a sample. A missing entry is reported as `catalog_status=missing_configuration`,
and a missing schema or template file is reported as `catalog_status=missing_fixture`.
Either condition fails that sample with a visible error. There is no silent catalog
fallback.

## Reproduction

Install backend dependencies:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Collect and build the cache-driven dataset:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

The raw cache is ignored by Git. Remove it at any time and rerun collection from
`examples/real_world/sources/source_manifest.json`.

Run the backend and evaluate through the real API:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000
```

If API-key authentication is enabled, pass `--api-key` at runtime. The key is sent in the
request header and is never included in reports.

Outputs:

- `examples/real_world/reports/extraction_report.{json,md}`
- `examples/real_world/reports/validation_report.{json,md}`
- `reports/real_world_eval_report.{json,md}`
- ignored local packages under `reports/real_world_packages/`

## Current limitations

- HTML layout heuristics cannot perfectly isolate every government content template.
- PDF heading detection is conservative and depends on available font metadata.
- Complex merged-cell tables are flattened into field/value rows.
- The collector is intentionally small-scale and sequential.
- No LLM is required for deterministic generation. If an assisted candidate is added
  manually, evidence, confidence, reason, and review state remain mandatory.

Future work may add reviewed domain-specific aliases, more contract samples, and
additional deterministic table normalization. OCR remains outside the main scope.

## Follow-up evaluation artifacts

The 2026-06-29 follow-up adds deterministic real-world evaluation artifacts:

- `examples/real_world/review_fixtures/procurement_review_decisions.jsonl`
- `examples/real_world/retrieval_queries.jsonl`
- `reports/real_world_knowledge_loop_report.{json,md}`
- `reports/chunk_retrieval_eval_report.{json,md}`

The knowledge-loop report keeps old snapshots immutable and records
`badcase_violation_count=0`. The retrieval report uses production chunk
organization services and no vector database or LLM.
