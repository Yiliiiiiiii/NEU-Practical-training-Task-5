# SchemaPack Agent Final Handoff Status

## Integrated Repository State

- Current branch: `main`.
- Verification baseline: 2026-06-30.
- Unified verification command: `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- Verified result: 202 backend tests passed, Ruff clean, frontend production build successful, and 32 OpenAPI paths exported to [`docs/openapi.json`](openapi.json).
- Core production boundary: UIR input to schema-driven package output.

The implemented processing line is:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

## Implemented Capability Matrix

| Area | Current capability | Evidence |
| --- | --- | --- |
| Schema/template catalogs | Catalog/governance coverage includes schemas, schema versions, mapping templates, template versions, and effective knowledge-pack selection, with status transitions, referenced-version protection, and immutable task snapshots. | [`docs/developer_guide.md`](developer_guide.md) |
| Document and task APIs | UIR import, document list/detail, task create/list/detail, explicit execution, report retrieval, package metadata, and package download. | [`docs/openapi.json`](openapi.json) |
| Mapping and transform | Deterministic field candidate extraction, exact/alias/regex/type/fuzzy matching, evidence, confidence tiers, risk flags, review-required reasons, badcase filtering, projection, normalization, enum maps, and defaults. | [`reports/real_world_mapping_eval_report.md`](../reports/real_world_mapping_eval_report.md) |
| Rendering and packages | Canonical model build, JSON/Markdown/chunk rendering, deterministic content organization, validation, manifest generation, ZIP creation, and strict package verification. | [`docs/package_spec.md`](package_spec.md) |
| Human review and knowledge | Review approval/rejection, knowledge candidates, draft/active/archived packs, effective-template resolution, metrics, snapshot preservation, and badcase protections. | [`reports/knowledge_loop_eval_report.md`](../reports/knowledge_loop_eval_report.md) |
| Optional LLM fallback | Disabled by default, deterministic stub and OpenAI-compatible modes, review-only suggestions, bounded retries/timeouts, suggestion caps, redacted reports, provider warning handling, and strict-mode override. | [`reports/llm_fallback_eval_report.md`](../reports/llm_fallback_eval_report.md) |
| Frontend workbench | Import, task creation, execution, mapping evidence, validation, content organization controls, chunk preview, raw reports, review/knowledge actions, audit panel, and package download. | [`docs/demo_workflow.md`](demo_workflow.md) |
| Deployment | Backend/frontend Dockerfiles, Nginx proxying, Docker Compose volumes, startup database initialization, API-key auth option, audit logs, and retention cleanup. | [`docs/deployment.md`](deployment.md) |
| Downstream consumption | Package ZIP/directory smoke ingest and training-corpus JSONL export. | [`docs/package_spec.md`](package_spec.md) |

## API And Frontend Surface

- The OpenAPI snapshot exports 32 paths in [`docs/openapi.json`](openapi.json). Use that file and [`docs/openapi_workflow.md`](openapi_workflow.md) as the API inventory instead of duplicating endpoint lists here.
- The frontend is a React/Vite workbench for the full demo path: sample UIR import, task creation, execution, report inspection, review decisions, knowledge activation, content organization settings, enriched chunk preview, and package download.
- The local frontend development server proxies `/api` to `http://127.0.0.1:8000`.
- The container profile serves the frontend through Nginx and proxies backend API calls under the same local origin.

## Catalogs, Data, And Packages

- Catalog/governance types are implemented for schemas, schema versions, mapping templates, template versions, and effective knowledge-pack selection.
- Seeded document families are `contract_doc`, `general_doc`, `meeting_doc`, `policy_doc`, and `procurement_doc`.
- The catalog baseline contains 5 schemas and 5 mapping templates.
- The real-world UIR dataset contains 16 JSON files:
  - 3 `general_doc`
  - 3 `meeting_doc`
  - 5 `policy_doc`
  - 5 `procurement_doc`
- Real-world execution evidence records 16/16 imports, 16/16 executions, and 16/16 verifier-passing packages in [`reports/real_world_eval_report.md`](../reports/real_world_eval_report.md).
- Real-world package outputs are stored under `reports/real_world_packages/`; production-like evaluator package outputs are stored under `reports/packages/`.
- Generated packages include structured content, Markdown content, chunks, metadata, mapping/transform/validation/canonical/content-organization/verifier reports, manifest, and checksums as described in [`docs/package_spec.md`](package_spec.md).

## Evaluation Evidence

- Unified verification: 202 backend tests passed, Ruff clean, frontend production build successful, and 32 OpenAPI paths exported by `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- Real-world pipeline: 16/16 documents import, execute, and produce verifier-passing packages. See [`reports/real_world_eval_report.md`](../reports/real_world_eval_report.md).
- Honest strict-validation split: all five `procurement_doc` samples pass strict validation; the other 11 real-world samples remain review-required and are not claimed as field-valid (`general_doc` 0/3, `meeting_doc` 0/3, `policy_doc` 0/5 strict passes).
- Real-world mapping: mapping recall is `0.42592592592592593`, package pass rate is 1.000, and badcase violations are 0. See [`reports/real_world_mapping_eval_report.md`](../reports/real_world_mapping_eval_report.md).
- Procurement comparison: required coverage is 1.000 for `procurement_doc` versus 0.333 for the generic `general_doc` schema, with zero badcase violations. See [`reports/procurement_doc_eval_report.md`](../reports/procurement_doc_eval_report.md).
- Content retrieval: the 32-query report records `Recall@3 = 1.000`. See [`reports/content_organization_retrieval_eval.md`](../reports/content_organization_retrieval_eval.md).
- Knowledge-loop reports: both [`reports/knowledge_loop_eval_report.md`](../reports/knowledge_loop_eval_report.md) and [`reports/real_world_knowledge_loop_report.md`](../reports/real_world_knowledge_loop_report.md) preserve old snapshots and record zero badcase violations.
- LLM fallback: [`reports/llm_fallback_eval_report.md`](../reports/llm_fallback_eval_report.md) records `auto_accepted_count = 0`, `secret_redaction_passed = true`, and two review-required suggestions.
- Acceptance and auxiliary evidence are recorded in [`reports/acceptance_report.md`](../reports/acceptance_report.md), [`reports/chunk_retrieval_eval_report.md`](../reports/chunk_retrieval_eval_report.md), and [`docs/requirement_mapping.md`](requirement_mapping.md).

## Reproduction Commands

Run the repository-wide baseline from the repository root:

```powershell
git branch --show-current
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Run the backend locally for API-backed evaluations:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From another repository-root terminal, regenerate the real-world and evaluation reports:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_knowledge_loop_real_world.py --base-url http://127.0.0.1:8000 --timeout 60
```

Run the offline report generators from the repository root:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_chunk_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_llm_fallback_modes.py
```

Run the container demo:

```powershell
docker compose up --build
```

Run the frontend development server:

```powershell
cd frontend
npm ci
npm run dev
```

## Known Boundaries

- Production input is UIR. Raw PDF, Word, Excel, image, scanned document, and OCR parsing are not production runtime features.
- The real-world source collection and UIR-building scripts are offline dataset tooling, not API-bound ingestion services.
- The 11 non-procurement real-world samples produce verifier-passing packages but remain review-required for strict field validity.
- Retrieval evaluation is deterministic chunk-ranking evidence, not a full RAG service.
- Optional LLM fallback is a review-only suggestion path; it does not activate mappings without human/governed review.
- The project does not implement SSO, tenant-aware authorization, TLS termination, hosted credential provisioning, enterprise model monitoring, full quality scoring, model training, or autonomous production rule activation.

## Productionization Directions

- Add authenticated operator review screens, role-aware workflows, and tenant-aware authorization before multi-tenant use.
- Add SSO/TLS integration, hosted credential management, model/provider evaluation, and monitoring before enabling network LLM fallback in production.
- Extend regression datasets through the existing gold-label, badcase, review, and snapshot-preservation checks.
- Publish generated API clients if downstream consumers require strongly typed integrations.
- Keep procurement specialization and future domain catalogs honest by separating verifier-passing packages from strict field-valid claims.

## Final Verification On 2026-06-30

The current `main` baseline is:

- `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`
- Backend pytest: 202 passed.
- Ruff: clean.
- Frontend production build: successful.
- OpenAPI export: 32 paths written to [`docs/openapi.json`](openapi.json).
- Real-world UIR pipeline: 16 imports, 16 task executions, and 16 package verifications.
- Strict validation: `procurement_doc` 5/5 passes; `general_doc` 0/3, `meeting_doc` 0/3, and `policy_doc` 0/5 remain review-required.
- Knowledge-loop safety: snapshot preservation true and badcase violations 0 in both knowledge-loop reports.
