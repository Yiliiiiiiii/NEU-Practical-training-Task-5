# SchemaPack Agent Final Handoff Status

Topic 5 follow-up Phases 23 through 28 are implemented in this checkout.

## Current Implemented Capabilities

- Core UIR-to-schema conversion service layer:
  - file-backed schema/template loading
  - database-backed schema/template catalog governance
  - seeded fixture versions with draft/active/archived status
  - referenced-version protection and immutable task snapshots
  - field candidate extraction
  - deterministic mapping with confidence tiers, structured evidence, risk
    flags, badcase filters, and review-required reasons
  - transform
  - canonical model build
  - render to structured JSON, Markdown, and chunks
  - configurable deterministic chunk organization with summaries, keywords,
    tags, entity-tag placeholders, source links, protected table/list/code
    blocks, and optional parent-child chunks
  - validation
  - manifest generation
  - package ZIP creation, `metadata.json`, package spec roles, and strict
    package verification
- Task APIs:
  - document import/list/detail
  - schema/template catalog reads, creation, activation, and archival
  - task create/list/detail
  - explicit task execution
  - task report reads
  - package metadata and ZIP download
- Production-like evaluator:
  - conversion artifacts are generated through real service layer components
  - before/after metrics are retained
  - badcase checks are retained
  - package validation is retained
  - downstream package smoke summary is retained
- Downstream package consumption:
  - manifest checksum validation for package directories and ZIP files
  - `chunks.jsonl` ingestion smoke test with simple keyword matching
  - training-corpus JSONL export with granularity filters, tags, source links,
    schema, and template metadata
- Human-gated mapping knowledge growth loop:
  - review-derived alias candidates
  - draft knowledge packs
  - active knowledge packs
  - effective template resolution
  - badcase filtering
  - database-backed review and knowledge APIs
- Optional LLM fallback adapter:
  - disabled by default
  - deterministic stub mode for tests and demos
  - OpenAI-compatible adapter mode for configured deployments
  - always review-required
  - records model, latency, prompt hash, response hash, confidence, and reason
  - bounded timeout and retries
  - per-task suggestion cap
  - non-strict provider failures recorded as mapping warnings
  - explicit task-level `strict_llm` override
  - non-sensitive execution snapshot and recursive secret redaction
  - badcase filtering
- Minimal React/Vite frontend workbench:
  - sample UIR import
  - task creation
  - task execution
  - mapping and validation report inspection
  - mapping evidence, confidence, and risk flag inspection
  - content organization report inspection
  - content organization strategy controls
  - enriched chunk preview with quality flags and parent-child metadata
  - collapsible raw JSON report inspection
  - review approve/reject controls
  - knowledge candidate acceptance and pack activation controls
  - package ZIP download
- Deployment packaging:
  - backend Dockerfile with startup database initialization
  - frontend Dockerfile with Nginx static serving and API proxying
  - Docker Compose profile with persistent storage/database volumes
  - production environment example with LLM fallback disabled
- Lightweight governance:
  - optional API key authentication for `/api/v1/*`
  - audit logs for task execution and package downloads
  - audit log query API and frontend panel
  - safe retention cleanup script with dry-run default
- Documentation:
  - `docs/openapi.json`
  - `docs/openapi_workflow.md`
  - `docs/developer_guide.md`
  - `docs/demo_workflow.md`
  - `docs/deployment.md`
  - `docs/final_demo_script.md`
  - `docs/requirement_mapping.md`
  - `docs/badcase_analysis.md`
- `docs/api_usage_examples.md`
- `docs/service_migration_plan.md`
- `docs/package_spec.md`
- Engineering maintenance:
  - `scripts/verify_all.py`
  - `.github/workflows/ci.yml`

## Current Not Implemented Capabilities

- Authorization, tenancy, SSO/TLS integration, and advanced operator controls.
- Hosted credential provisioning, model evaluation, and enterprise LLM
  monitoring.
- Raw source parsing for PDF, Word, Excel, images, OCR outputs, or scanned files.

## How To Run Tests

From the backend directory:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

From the frontend directory:

```powershell
cd frontend
npm run build
```

Deployment packaging smoke checks are included in the backend pytest suite.

## How To Run The Evaluator

From the repository root:

```powershell
python scripts\eval_production_like.py
```

Expected current summary:

```text
production-like eval complete: 15 cases, gold=1.0, badcase=1.0
```

Evaluator outputs:

- `reports/production_like_eval_report.json`
- `reports/production_like_eval_report.md`
- `reports/packages/`

## How To Start The Demo

Container profile:

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080/
```

Local development profile:

Start the backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Demo path:

```text
Sample UIR -> Import -> Create Task -> Execute -> Reports -> ZIP download
```

## How To Verify Package ZIP

Option 1: Use the evaluator report.

- Run `python scripts\eval_production_like.py`.
- Open `reports/production_like_eval_report.json`.
- Confirm `package_validation.phase_a` and `package_validation.phase_b` entries have `passed: true`.

Option 2: Inspect a generated package manually.

```powershell
@'
import json
import zipfile
from pathlib import Path

report = json.loads(Path("reports/production_like_eval_report.json").read_text(encoding="utf-8"))
first = report["package_validation"]["phase_b"][0]
zip_path = Path(first["zip_path"])
print(zip_path, zip_path.is_file())
with zipfile.ZipFile(zip_path) as archive:
    print(sorted(archive.namelist()))
'@ | python -
```

Expected package files include:

- `content.json`
- `content.md`
- `chunks.jsonl`
- `metadata.json`
- `content_organization_report.json`
- `mapping_report.json`
- `transform_report.json`
- `validation_report.json`
- `canonical.json`
- `manifest.json`
- `verifier_report.json`

## How To Smoke Test Downstream Consumption

From the repository root, after running the evaluator:

```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "鍒跺害 绠＄悊"
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl
```

## Topic 5 Boundaries

SchemaPack Agent starts from UIR input. It does not parse or OCR raw PDF, Word,
Excel, image, scan, or other source files.

The implemented scope is:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

The project does not include cleaning, normalization, entity linking, full
quality scoring, full RAG, model training, or autonomous production rule
activation.

## Productionization Directions

- Add authenticated operator review screens.
- Add hosted credential provisioning, provider/model evaluation, and enterprise
  monitoring if enabling the optional OpenAI-compatible adapter.
- Add SSO, tenant-aware authorization, TLS termination, and advanced operator
  controls when moving beyond the current API-key deployment profile.
- Add generated client publication if downstream consumers require it.
- Expand regression datasets while preserving gold and badcase checks.

