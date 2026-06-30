# Topic 5 Requirement Mapping

This document maps Topic 5 requirements to the current SchemaPack Agent
implementation and committed evidence on `main`.

| Requirement | Current implementation | Evidence |
| --- | --- | --- |
| Standardization | UIR import, schema/template snapshots, deterministic mapping, transform, canonical model, structured JSON, Markdown, and package output. | `mapping_report.json`, `transform_report.json`, `canonical.json`, `content.json`, `content.md`, [`docs/package_spec.md`](package_spec.md) |
| Intelligent organization | Deterministic chunk strategies, summaries, keywords, content/management/quality tags, protected table/list/code chunks, parent-child metadata, and source links. | `content_organization_report.json`, `chunks.jsonl`, [`reports/content_organization_retrieval_eval.md`](../reports/content_organization_retrieval_eval.md) |
| Specialized conversion | Five seeded document catalogs/families, including dedicated `procurement_doc` schema and `procurement_doc_base_v1` template for procurement samples. | [`reports/procurement_doc_eval_report.md`](../reports/procurement_doc_eval_report.md), [`docs/real_world_uir_dataset.md`](real_world_uir_dataset.md) |
| Evaluation | Production-like evaluator plus 16-document real-world import, execution, package, mapping, procurement, retrieval, and knowledge-loop runs. | [`reports/production_like_eval_report.md`](../reports/production_like_eval_report.md), [`reports/real_world_eval_report.md`](../reports/real_world_eval_report.md), committed JSON/Markdown report pairs under `reports/` |
| Continuous improvement | Review records, review-derived knowledge candidates, accepted/rejected candidate states, draft/active/archived knowledge packs, and effective-template resolution. | [`reports/knowledge_loop_eval_report.md`](../reports/knowledge_loop_eval_report.md), [`reports/real_world_knowledge_loop_report.md`](../reports/real_world_knowledge_loop_report.md), Review and Knowledge APIs |
| Safety and traceability | Mapping evidence, confidence tiers, review-required reasons, badcase filters, immutable task snapshots, manifest hashes, package verifier output, optional API-key auth, audit logs, and LLM secret redaction. | [`docs/api_usage_examples.md`](api_usage_examples.md), [`docs/final_handoff_status.md`](final_handoff_status.md), `manifest.json`, `verifier_report.json`, [`reports/llm_fallback_eval_report.md`](../reports/llm_fallback_eval_report.md) |

## Current Evidence Summary

- Unified verification: `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`
  records 202 backend tests, Ruff clean, frontend production build success, and
  32 exported OpenAPI paths.
- Real-world pipeline: 16/16 imports, 16/16 executions, and 16/16
  verifier-passing packages.
- Strict validation: `procurement_doc` passes 5/5; `general_doc` 0/3,
  `meeting_doc` 0/3, and `policy_doc` 0/5 remain review-required.
- Procurement specialization: required coverage is 1.000 for
  `procurement_doc` versus 0.333 for the generic schema.
- Retrieval: 32-query content retrieval report records `Recall@3 = 1.000`.
- Knowledge loop: both knowledge-loop reports preserve snapshots and record
  zero badcase violations.
- LLM safety: fallback suggestions remain review-required, `auto_accepted_count`
  is 0, and secret redaction passes.

## Implemented Boundary

The implemented runtime line is:

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical Model -> Render -> Content Organization
-> Validation -> Manifest -> ZIP -> Package Verification
```

The project implements optional API-key authentication, task/package audit logs,
review governance, knowledge-pack activation, and local/container deployment
profiles. These are lightweight project controls, not enterprise identity or
tenant platforms.

## Explicit Non-Goals

- OCR, scanned document recognition, and raw PDF/Word/Excel/image parsing in
  the production runtime.
- Full RAG/vector search service or online retrieval backend.
- Model training, fine-tuning, or autonomous production rule activation from LLM
  output.
- Enterprise SSO, tenant-aware authorization, TLS termination, managed secret
  storage, hosted credential provisioning, or model/provider monitoring.

## Caveats For Reviewers

- Package verification proves package structure, hashes, required artifacts,
  parseability, and traceability. It does not claim every target field passed
  strict semantic validation.
- The retrieval evaluator is deterministic and lightweight. It supports
  evidence for chunk organization, not a production RAG system.
- Gold labels and badcases are coursework-scale evaluation assets, not an
  enterprise benchmark.
