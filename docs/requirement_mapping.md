# Topic 5 Requirement Mapping

This document maps topic 5 requirements to the current SchemaPack Agent
implementation.

| Requirement Area | Implementation | Evidence |
| --- | --- | --- |
| UIR as governed input | Document import persists UIR JSON and metadata. | `POST /api/v1/documents/import`, `DocumentService` |
| Schema-driven conversion | Schema catalog loads governed target schemas with versions and status. | `GET /api/v1/schemas`, `CatalogGovernanceService` |
| Mapping template control | Template catalog validates aliases, regex, enum maps, defaults, and transforms against schema fields. | `TemplateService`, `CatalogGovernanceService` |
| Source field extraction | Candidate extraction reads metadata, table rows, and block hints. | `CandidateService` |
| Deterministic semantic mapping | Mapping uses exact, alias, regex, type, fuzzy, and review-required fallback strategies. | `MappingService`, mapping report |
| Human review loop | Review records can be approved/rejected and converted into knowledge candidates. | `ReviewService`, Review API |
| Knowledge growth | Accepted candidates can become draft/active knowledge packs; only active packs affect new tasks. | `KnowledgeService`, `EffectiveTemplateService` |
| Safe LLM posture | LLM fallback has disabled, stub, and OpenAI-compatible adapters; it is disabled by default and always review-required. | `LLMFallbackService` |
| Field transformation | Transform rules normalize dates, numbers, enums, defaults, and projected fields. | `TransformService`, transform report |
| Canonical output | Converted data is persisted with schema/task/source metadata. | `CanonicalService`, `canonical.json` |
| Human-readable output | Markdown rendering is included in every package. | `content.md` |
| Machine-readable output | Structured JSON and JSONL chunks are included in every package. | `content.json`, `chunks.jsonl` |
| Content organization | Chunks include summaries, keywords, tags, source links, and organization traces. | `ChunkOrganizerService`, `content_organization_report.json` |
| Validation | Required fields and artifact consistency are validated. | `ValidationService`, `validation_report.json` |
| Packaging | Output ZIP includes manifest, reports, chunks, Markdown, and JSON. | `PackageService` |
| Reproducibility | Manifest entries include byte size, SHA-256, media type, and role. | `ManifestService`, `manifest.json` |
| Package verification | Verifier checks required files, checksums, JSON, JSONL, Markdown, and chunk fields. | `PackageVerifierService`, `verifier_report.json` |
| Downstream usability | Smoke scripts validate package ingestion and export training-corpus JSONL. | `scripts/smoke_rag_ingest.py`, `scripts/export_training_corpus.py` |
| Evaluation | Production-like evaluator checks gold cases, badcases, package validation, and downstream smoke. | `scripts/eval_production_like.py` |
| Frontend demo | Workbench supports import, task execution, reports, review, knowledge, and ZIP download. | `frontend/src` |
| Deployment | Docker Compose profile packages backend, frontend, storage, and SQLite volumes. | `docker-compose.yml`, `docs/deployment.md` |

## Explicit Non-Goals

- Raw source parsing for PDF, Word, Excel, images, OCR, or scanned files.
- Full RAG/vector database implementation.
- Full entity linking or universal data cleaning.
- Autonomous production rule activation by LLM output.
- Authentication, tenancy, audit logging, and production access control.
