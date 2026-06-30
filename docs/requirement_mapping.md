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
| Real-world mapping evidence | 16 real UIR files are scored against source-backed mapping gold, review-required expectations, badcases, and package verification. | `reports/real_world_mapping_eval_report.md` |
| Procurement specialization | Dedicated procurement schema/template is compared against generic mapping for required coverage, gold recall, badcases, and package pass rate. | `reports/procurement_doc_eval_report.md` |
| Content retrieval evidence | 32 query labels evaluate lightweight chunk ranking across strategies and document types. | `reports/content_organization_retrieval_eval.md` |
| Knowledge-loop evidence | Review approval, candidate acceptance, draft/active pack behavior, snapshot invariants, and badcase counts are evaluated. | `reports/knowledge_loop_eval_report.md` |
| Frontend demo | Workbench supports import, task execution, reports, review, knowledge, and ZIP download. | `frontend/src` |
| Deployment | Docker Compose profile packages backend, frontend, storage, and SQLite volumes. | `docker-compose.yml`, `docs/deployment.md` |

## Explicit Non-Goals

- Raw source parsing for PDF, Word, Excel, images, OCR, or scanned files.
- Full RAG/vector database implementation.
- Full entity linking or universal data cleaning.
- Autonomous production rule activation by LLM output.
- Authentication, tenancy, audit logging, and production access control.

## Topic 5 Deepening Caveats

- Retrieval evaluator is lightweight and is not a full RAG system.
- Procurement schema is v1 and aliases require continued real-sample review.
- Gold labels are coursework-scale evaluation labels, not an enterprise benchmark.
