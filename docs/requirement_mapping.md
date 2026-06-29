# Topic 5 Requirement Mapping

This document maps topic 5 requirements to the current SchemaPack Agent
implementation.

| Requirement Area | Implementation | Evidence |
| --- | --- | --- |
| UIR as governed input | Document import persists UIR JSON and metadata. | `POST /api/v1/documents/import`, `DocumentService` |
| Schema-driven conversion | Schema catalog loads governed target schemas with versions and status. | `GET /api/v1/schemas`, `CatalogGovernanceService` |
| Mapping template control | Template catalog validates aliases, regex, enum maps, defaults, and transforms against schema fields. | `TemplateService`, `CatalogGovernanceService` |
| Source field extraction | Candidate extraction reads metadata, table rows, and block hints. | `CandidateService` |
| Deterministic semantic mapping | Mapping uses exact, alias, regex, type, fuzzy, and review-required fallback strategies with confidence tiers, structured evidence, risk flags, and badcase filters. | `MappingService`, mapping report |
| Human review loop | Review records can be approved/rejected and include mapping evidence, risk flags, confidence, and review-required reasons before becoming knowledge candidates. | `ReviewService`, Review API |
| Knowledge growth | Accepted candidates can become draft/active knowledge packs; only active packs affect new tasks. | `KnowledgeService`, `EffectiveTemplateService` |
| Safe LLM posture | LLM fallback has disabled, stub, and OpenAI-compatible adapters; it is disabled by default, always review-required, timeout-bounded, retry-bounded, capped per task, warning-based on non-strict failure, and secret-redacted. | `LLMFallbackService`, `MappingService`, `redact_sensitive_values` |
| Field transformation | Transform rules normalize dates, numbers, enums, defaults, and projected fields. | `TransformService`, transform report |
| Canonical output | Converted data is persisted with schema/task/source metadata. | `CanonicalService`, `canonical.json` |
| Human-readable output | Markdown rendering is included in every package. | `content.md` |
| Machine-readable output | Structured JSON and JSONL chunks are included in every package. | `content.json`, `chunks.jsonl` |
| Content organization | Chunks include configurable strategies, parent-child metadata, summaries, keywords, tags, source links, quality flags, and organization traces. | `ChunkOrganizerService`, `content_organization_report.json` |
| Validation | Required fields and artifact consistency are validated. | `ValidationService`, `validation_report.json` |
| Packaging | Output ZIP includes manifest, metadata, reports, chunks, Markdown, and JSON. | `PackageService`, `docs/package_spec.md` |
| Reproducibility | Manifest entries include byte size, SHA-256, media type, and role. | `ManifestService`, `manifest.json` |
| Package verification | Verifier checks required files, checksums, JSON, JSONL, Markdown, chunk fields, and strict package-spec roles/media types when enabled. | `PackageVerifierService`, `verifier_report.json` |
| Downstream usability | Smoke scripts validate package ingestion and export training-corpus JSONL. | `scripts/smoke_rag_ingest.py`, `scripts/export_training_corpus.py` |
| Evaluation | Production-like evaluator checks gold cases, badcases, package validation, and downstream smoke. | `scripts/eval_production_like.py` |
| Frontend demo | Workbench supports import, task execution, reports, review, knowledge, and ZIP download. | `frontend/src` |
| Deployment | Docker Compose profile packages backend, frontend, storage, and SQLite volumes. | `docker-compose.yml`, `docs/deployment.md` |
| Dedicated procurement mapping | Procurement real-world samples route to `procurement_doc` and `procurement_doc_base_v1`, never silently to `general_doc`. | `examples/production_like/schemas/procurement_doc_v1.json`, `scripts/eval_real_world_uir.py` |
| Real-world knowledge loop | Approved aliases activate only through review-derived knowledge packs; rejected/badcase candidates remain blocked. | `reports/real_world_knowledge_loop_report.json` |
| Retrieval evidence | Chunk retrieval reports Recall@1/3/5, MRR, nDCG@5, source-link coverage, table integrity, average tokens, and chunk count. | `reports/chunk_retrieval_eval_report.json` |
| Frontend evidence panels | Mapping, validation, chunk, manifest, and knowledge-loop evidence render through focused React panels. | `frontend/src/components/*EvidencePanel.tsx` |
| LLM safety evaluation | Disabled/stub/provider-error modes verify review-only suggestions, badcase blocking, and secret redaction without network. | `reports/llm_fallback_eval_report.json` |

## Explicit Non-Goals

- Raw source parsing for PDF, Word, Excel, images, OCR, or scanned files.
- Full RAG/vector database implementation.
- Full entity linking or universal data cleaning.
- Autonomous production rule activation by LLM output.
- Authentication, tenancy, audit logging, and production access control.
