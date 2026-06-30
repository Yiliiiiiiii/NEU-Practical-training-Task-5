# SchemaPack Agent

## Current Status

Current verified baseline (2026-06-30): `main`, 202 backend tests, Ruff clean, frontend production build successful, and 32 exported OpenAPI paths.

SchemaPack Agent is a UIR-first system for turning normalized document structure into schema-governed, verifier-checked output packages. The verified production boundary starts at UIR input and ends at package ZIP output.

## Implemented Capabilities

The implemented processing line is:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

- Catalog governance for schemas, schema versions, mapping templates, template versions, and effective knowledge-pack selection.
- Seeded document catalog families for `contract_doc`, `general_doc`, `meeting_doc`, `policy_doc`, and `procurement_doc`.
- UIR document import, task creation/list/detail, explicit execution, report retrieval, package metadata, and package download APIs.
- Deterministic mapping with exact, alias, regex, type, and fuzzy strategies; confidence tiers; source evidence; risk flags; review-required reasons; badcase filters; and optional review-only LLM suggestions.
- Transform, canonical model, structured JSON, Markdown, chunk rendering, validation, manifest generation, package ZIP creation, and strict package verification.
- Human review and knowledge-loop services for pending reviews, candidate decisions, draft/active/archived knowledge packs, effective template resolution, metrics, snapshot preservation, and badcase protection.
- React/Vite workbench for import, task creation, execution, mapping evidence, validation, content organization, knowledge actions, raw report inspection, and package download.
- Local container deployment with backend/frontend Dockerfiles, Nginx API proxying, persistent volumes, startup database initialization, optional API-key auth, audit logs, and retention cleanup.
- Downstream package smoke checks and training-corpus JSONL export tooling.

## Verified Evidence

- Unified verification is recorded for `main`: `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` produced 202 backend tests passed, Ruff clean, frontend production build successful, and 32 OpenAPI paths exported to [`docs/openapi.json`](docs/openapi.json). Use [`docs/openapi_workflow.md`](docs/openapi_workflow.md) and [`docs/openapi.json`](docs/openapi.json) for the API inventory instead of copying the 32-path list here.
- The real-world pipeline records 16/16 documents importing, 16/16 task executions completing, and 16/16 packages passing verification. See [`reports/real_world_eval_report.md`](reports/real_world_eval_report.md) and [`reports/real_world_eval_report.json`](reports/real_world_eval_report.json).
- Strict validation passes for the five `procurement_doc` samples. The other 11 real-world samples remain review-required and are not claimed as field-valid: `general_doc` 0/3, `meeting_doc` 0/3, and `policy_doc` 0/5 strict passes.
- The real-world mapping report records package pass rate 1.000, mapping recall `0.42592592592592593`, and zero badcase violations. See [`reports/real_world_mapping_eval_report.md`](reports/real_world_mapping_eval_report.md) and [`reports/real_world_mapping_eval_report.json`](reports/real_world_mapping_eval_report.json).
- The procurement comparison records required coverage of 1.000 for `procurement_doc` versus 0.333 for the generic `general_doc` schema. See [`reports/procurement_doc_eval_report.md`](reports/procurement_doc_eval_report.md) and [`reports/procurement_doc_eval_report.json`](reports/procurement_doc_eval_report.json).
- The 32-query retrieval report records `Recall@3 = 1.000`. See [`reports/content_organization_retrieval_eval.md`](reports/content_organization_retrieval_eval.md) and [`reports/content_organization_retrieval_eval.json`](reports/content_organization_retrieval_eval.json).
- Both knowledge-loop reports preserve snapshots and record zero badcase violations. See [`reports/real_world_knowledge_loop_report.md`](reports/real_world_knowledge_loop_report.md), [`reports/real_world_knowledge_loop_report.json`](reports/real_world_knowledge_loop_report.json), [`reports/knowledge_loop_eval_report.md`](reports/knowledge_loop_eval_report.md), and [`reports/knowledge_loop_eval_report.json`](reports/knowledge_loop_eval_report.json).
- The LLM fallback report records `auto_accepted_count = 0`, successful secret redaction, and two review-required suggestions. See [`reports/llm_fallback_eval_report.md`](reports/llm_fallback_eval_report.md) and [`reports/llm_fallback_eval_report.json`](reports/llm_fallback_eval_report.json).

## Quick Start

Run the verified repository baseline from the repository root:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Start the backend locally:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local workbench:

```text
http://127.0.0.1:5173/
```

For the container profile:

```powershell
docker compose up --build
```

Open the containerized workbench:

```text
http://127.0.0.1:8080/
```

## Unified Verification

The authoritative verification command is:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected verified baseline for 2026-06-30:

- Backend pytest: 202 passed.
- Ruff: clean.
- Frontend production build: successful.
- OpenAPI export: 32 paths written to [`docs/openapi.json`](docs/openapi.json).

## Documentation Map

- Final handoff status: [`docs/final_handoff_status.md`](docs/final_handoff_status.md)
- Demo workflow: [`docs/demo_workflow.md`](docs/demo_workflow.md)
- Final demo script: [`docs/final_demo_script.md`](docs/final_demo_script.md)
- Developer guide: [`docs/developer_guide.md`](docs/developer_guide.md)
- Deployment guide: [`docs/deployment.md`](docs/deployment.md)
- API workflow and snapshot: [`docs/openapi_workflow.md`](docs/openapi_workflow.md), [`docs/openapi.json`](docs/openapi.json)
- API examples: [`docs/api_usage_examples.md`](docs/api_usage_examples.md)
- Requirement mapping: [`docs/requirement_mapping.md`](docs/requirement_mapping.md)
- Badcase analysis: [`docs/badcase_analysis.md`](docs/badcase_analysis.md)
- Package specification: [`docs/package_spec.md`](docs/package_spec.md)
- Real-world UIR dataset guide: [`docs/real_world_uir_dataset.md`](docs/real_world_uir_dataset.md)
- Real-world knowledge-loop guide: [`docs/real_world_knowledge_loop.md`](docs/real_world_knowledge_loop.md)

## Production Boundaries

- Production input is UIR. Raw PDF, Word, Excel, image, scan, and OCR parsing are outside the production runtime boundary.
- Real-world source collection and UIR-building scripts are offline dataset tooling, not runtime ingestion services.
- Non-procurement real-world samples produce verifier-passing packages but remain review-required for strict field validity.
- Optional LLM fallback is a suggestion source only. It never auto-accepts mappings, and provider failures become warnings/review items unless strict failure is explicitly requested.
- Retrieval and mapping evaluations are deterministic project evidence, not a full RAG service, model-training pipeline, hosted credential service, SSO/TLS stack, tenant system, or enterprise model-monitoring platform.
