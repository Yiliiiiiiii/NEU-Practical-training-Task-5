# Developer Guide

## Project Structure

- `backend/app/api/v1/`: FastAPI routes for documents, catalogs, tasks, reviews,
  knowledge, evaluation reports, and audit logs.
- `backend/app/schemas/`: Pydantic contracts for UIR, catalog records, task
  execution, reports, package metadata, reviews, and knowledge packs.
- `backend/app/services/`: deterministic conversion, catalog, review,
  knowledge, package, audit, and retention services.
- `backend/app/services/task_execution_service.py`: orchestration for the full
  UIR-to-package pipeline.
- `backend/app/db/models.py`: SQLAlchemy tables initialized for tests and local
  runtime databases.
- `frontend/src/`: React/Vite operator workbench.
- `examples/production_like/` and `examples/real_world/`: reproducible
  evaluation fixtures and UIR datasets.
- `scripts/`: verification, OpenAPI export, evaluators, report builders, and
  downstream package consumers.
- `docs/` and `reports/`: current operating guides and generated evidence.

## Main Pipeline And Ownership Boundaries

The current execution pipeline is:

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical Model -> Render -> Content Organization
-> Validation -> Manifest -> ZIP -> Package Verification
```

`backend/app/services/task_execution_service.py` owns pipeline orchestration. It
loads the imported UIR, resolves the requested schema/template through the
catalog, captures immutable task snapshots, runs mapping and transformation,
builds canonical and rendered artifacts, organizes chunks, validates outputs,
generates the manifest, writes the ZIP package, and verifies package contents.

Keep new runtime behavior inside the relevant service boundary rather than in
the API route layer. API routes should validate requests, call services, and
return structured responses; conversion decisions should remain inside services
and reports so tasks stay reproducible.

## Catalog Governance And Snapshots

Schemas and mapping templates are catalog-managed. Version activation and
archival must preserve historical reproducibility:

- new task executions resolve active schema/template versions unless the caller
  explicitly requests a version;
- each task stores the resolved schema/template snapshot before execution;
- referenced versions are protected from destructive lifecycle transitions;
- archived versions should not be used for new task executions.

When adding or changing catalog fixtures, keep schema fields, aliases, regex
rules, enum maps, defaults, and transform targets consistent. Re-run the
OpenAPI export and the unified verification gate after route or schema changes.

## Mapping, Review, And Knowledge Growth

`MappingService` should keep deterministic strategy order and explain every
decision with confidence, confidence tier, evidence, risk flags,
`badcase_filter`, and `review_required_reason` where applicable. Optional LLM
fallback suggestions must remain review-required; they are not allowed to
auto-accept mappings.

Review-derived knowledge candidates flow into draft knowledge packs. Active
packs are selected through the effective-template path so future tasks can use
approved aliases while preserving old task snapshots and badcase protections.
When changing this loop, verify both snapshot preservation and badcase
violation counts in the knowledge-loop reports.

## Frontend Workbench

The React/Vite workbench in `frontend/src/App.tsx` is a local operator console
for UIR import, task creation/execution, report inspection, mapping evidence,
review actions, candidate decisions, knowledge-pack activation, audit log reads,
content organization controls, chunk previews, and package download.

Keep controls close to the workflow they affect and preserve the development
proxy contract: frontend `/api` requests are proxied to the local backend.

## Package And Chunk Changes

When changing package roles, required files, media types, or checksum rules,
update these together:

- `docs/package_spec.md`
- `ManifestService`
- `PackageService`
- `PackageVerifierService`
- downstream smoke/export scripts where package shape changes affect consumers

Content organization changes should preserve compatibility when task options
omit `content_organization`. Chunks should keep source links, title paths,
quality tags, stable report summary keys, and parent-child metadata when that
strategy is enabled.

## Default Local Gate

From the repository root, the default local verification gate is:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

The current verified baseline is 203 backend tests, Ruff clean, frontend
production build successful, and 32 exported OpenAPI paths.

For smaller loops, run the pieces directly:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .

cd ..\frontend
npm ci
npm run build
```

## Report Regeneration

Start the backend before API-backed evaluators:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From another repository-root terminal, regenerate production-like and real-world
evidence:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_like.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_knowledge_loop_real_world.py --base-url http://127.0.0.1:8000 --timeout 60
```

Regenerate the non-procurement recall evidence:

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

If the API-backed evaluator returns import errors, keep the report as failed
evidence and diagnose the backend/API path before claiming recall targets. Do
not delete required gold fields, disable badcase filters, or treat zero missing
counts from failed imports as success.

Regenerate offline retrieval, knowledge-loop, LLM fallback, and acceptance
evidence:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_chunk_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_llm_fallback_modes.py
backend\.venv\Scripts\python.exe scripts\build_acceptance_report.py
```

The LLM fallback evaluator covers disabled, deterministic stub, and provider
failure safety modes without network by default. Do not run an
OpenAI-compatible network mode unless an operator supplies credentials and
explicitly requests that invocation.

## Common Issues

- `.env`: use `.env.example` for local development and
  `.env.production.example` for the container profile. Keep
  `LLM_FALLBACK_ENABLED=false` unless explicitly testing fallback behavior.
- SQLite state: backend tests create isolated pytest databases. Local runs may
  use `backend/schemapack.db` or the configured `DATABASE_URL`; remove or reset
  that database when catalog state is intentionally being rebuilt.
- Frontend dependencies: use `npm ci` after checkout or whenever
  `frontend/package-lock.json` changes. Avoid mixing `npm install` lockfile
  updates into documentation-only changes.
- Occupied API ports: local backend and Compose both use port `8000`; stop the
  existing process/container or choose another port before starting Uvicorn.
- OpenAPI drift: run `scripts/export_openapi.py` or the unified gate after API
  route or schema changes.
- Secrets: configure LLM and API keys only through environment variables. Task
  options, execution snapshots, reports, and audit metadata must remain
  redacted.
