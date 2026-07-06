# SchemaPack Agent Service Migration Plan

> **Historical migration record:** Detailed module gaps and “later” steps below
> describe earlier checkpoints. The current implementation has progressed
> through the maturity roadmap; use [`project_status.md`](project_status.md) for
> current capabilities and boundaries.

## 1. Purpose

This document is now a historical migration plan plus completion record for the
Phase 1 through Phase 22 follow-up work. It originally recorded the Phase 1 audit for
migrating the current
`scripts/eval_production_like.py` deterministic evaluation harness into a real
backend service layer. The goal is to preserve the existing production-like
dataset and report behavior while moving conversion responsibilities into
`backend/app/services/` and keeping the evaluator focused on orchestration and
metrics.

Phase 15 has now implemented the core service pipeline, an explicit task execute
endpoint, evaluator migration to the real service layer, and the first
Review/Knowledge/EffectiveTemplate service loop, plus a deterministic
LLMFallbackService stub. Follow-up work adds an optional OpenAI-compatible LLM
fallback adapter, a minimal React/Vite frontend workbench, and the read APIs
needed by that UI. OpenAPI and demo workflow docs are now exported.

## 2. Current Checkout Summary

The current checkout has moved beyond the handoff baseline and implements the
planned migration phases plus follow-up work through Phase 22.

Implemented:

- FastAPI app skeleton with `/health`.
- Environment settings in `backend/app/config.py`.
- SQLite / SQLAlchemy metadata in `backend/app/db/models.py`.
- Pydantic v2 contracts under `backend/app/schemas/`.
- Runtime `StorageService`.
- `DocumentService` for UIR import/list/detail storage.
- `TaskService` for conversion task creation/list/detail metadata.
- API routes for documents and tasks.
- Demo examples under `examples/demo/`.
- Production-like dataset under `examples/production_like/`.
- `scripts/eval_production_like.py`, a deterministic harness that generates
  production-like reports and package-like artifacts.
- Baseline tests, including production-like fixture and evaluator tests.

Remaining production hardening not implemented:

- Hosted model credentials, model evaluation, and production LLM operations.
- Persistent production hardening beyond the local container profile.

## 3. Existing Modules

### Backend Services

| File | Current responsibility | Migration note |
| --- | --- | --- |
| `backend/app/services/storage_service.py` | Safe file resolution, JSON/text read/write, SHA-256. | Reuse for schema/template file registry and package outputs. |
| `backend/app/services/document_service.py` | Import UIR into storage and DB; list/read documents. | Reuse as task execution input source. |
| `backend/app/services/task_service.py` | Create/list/read task metadata; compute input hash. | Extend later or compose with `TaskExecutionService`; do not overload it with all pipeline logic. |

### Pydantic Contracts

| File | Useful contracts |
| --- | --- |
| `backend/app/schemas/uir.py` | `UIRDocument`, `UIRBlock`, `UIRAsset`, source anchors. |
| `backend/app/schemas/target_schema.py` | `TargetSchema`, `TargetField`. |
| `backend/app/schemas/mapping_template.py` | `MappingTemplate`, `RegexRule`. |
| `backend/app/schemas/transform.py` | `TransformRule`. |
| `backend/app/schemas/mapping.py` | `FieldCandidate`, `FieldMapping`, `SourceField`. |
| `backend/app/schemas/reports.py` | `MappingReport`, `ValidationReport`, `ConsistencyReport`, `ConversionTrace`. |
| `backend/app/schemas/canonical.py` | `CanonicalModel`, `CanonicalField`, `CanonicalBlock`, `CanonicalAsset`. |
| `backend/app/schemas/package.py` | `Manifest`, `ManifestFile`, `OutputPackageMetadata`. |
| `backend/app/schemas/review.py` | `ReviewRecord`. |
| `backend/app/schemas/run_snapshot.py` | `ExecutionSnapshot`. |
| `backend/app/schemas/output_profile.py` | `OutputProfile`. |

### API Routes

| Route file | Exposed endpoints | Current behavior |
| --- | --- | --- |
| `backend/app/api/v1/documents.py` | `POST /documents/import`, `GET /documents`, `GET /documents/{doc_id}` | Imports and reads UIR data. |
| `backend/app/api/v1/schemas.py` | `GET /schemas`, `GET /schemas/{schema_id}` | Lists and reads file-backed schemas. |
| `backend/app/api/v1/templates.py` | `GET /templates`, `GET /templates/{template_id}` | Lists and reads file-backed templates. |
| `backend/app/api/v1/tasks.py` | `POST /tasks`, `GET /tasks`, `GET /tasks/{task_id}`, `POST /tasks/{task_id}/execute`, report/package endpoints | Creates, reads, executes conversion tasks, and exposes generated artifacts. |
| `backend/app/api/v1/router.py` | Includes documents, schemas, templates, and tasks routers. | No knowledge or evaluation routes yet. |

### Database Tables Already Declared

`backend/app/db/models.py` already declares tables for many future services:

- `target_schemas`
- `mapping_templates`
- `field_candidates`
- `field_mappings`
- `transform_traces`
- `canonical_models`
- `validation_reports`
- `consistency_reports`
- `output_packages`
- `package_files`
- `review_records`

The table declarations are useful for later persistence, but the first service
implementation pass should stay file-backed or storage-backed where possible to
avoid coupling all pipeline work to a database migration story.

## 4. Production-like Dataset Status

`examples/production_like/` currently contains:

- 4 target schemas:
  - `policy_doc_v1.json`
  - `contract_doc_v1.json`
  - `meeting_doc_v1.json`
  - `general_doc_v1.json`
- 4 base mapping templates:
  - `policy_doc_base_v1.json`
  - `contract_doc_base_v1.json`
  - `meeting_doc_base_v1.json`
  - `general_doc_base_v1.json`
- 15 synthetic UIR cases across 4 domains.
- Machine-readable expectations:
  - `mapping_gold_cases.jsonl`
  - `badcases.jsonl`
  - `package_expectations.json`
  - `chunk_expectations.json`

The dataset is suitable as the service migration regression suite. It should not
be expanded until the service layer can reproduce the current report behavior.

## 5. Harness Responsibilities To Migrate

The current evaluator owns responsibilities that should move into services.

| Current evaluator logic | Current functions/classes | Target service |
| --- | --- | --- |
| Dataset file loading and expectation loading | `DatasetCase`, `load_json`, `load_jsonl`, `load_dataset` | Keep mostly in evaluator; schema/template loading moves to `SchemaService` and `TemplateService`. |
| Candidate extraction from metadata/tables/block hints | `SourceCandidate`, `extract_candidates`, `infer_type`, `sanitize` | `CandidateService`. |
| Effective template merge from active aliases | `resolve_effective_template`, `derive_active_aliases` | `EffectiveTemplateService`; `derive_active_aliases` later replaced by `KnowledgeService` pack activation. |
| Mapping strategy orchestration | `run_case`, `find_confirmed_mapping`, `find_review_mapping`, `find_regex_mappings`, `should_review`, `is_type_compatible`, `mapping_dict`, `average` | `MappingService`, using `CandidateService` output and an effective template. |
| Required field mapping errors | Required-field logic inside `run_case` | `MappingService` records unmapped required fields; `ValidationService` validates final data. |
| Validation report creation | `run_case` creates `ValidationReport` directly | `ValidationService`. |
| Canonical model construction | `build_canonical`, `sha256_bytes` for block hashes | `CanonicalService`. |
| Markdown rendering | `render_markdown` | `RenderService`. |
| Chunk building | `build_chunks` | `RenderService`, with heading-aware chunker. |
| Package file writing, manifest creation, zip creation | `create_packages`, `media_type`, `role`, `sha256_file`, `write_json` | `ManifestService`, `PackageService`. |
| Manifest checksum verification | `verify_manifest` | `PackageVerifierService`. |
| Phase metrics | `summarize_phase`, `rate` | Keep in evaluator or move to optional `EvaluationService`. |
| Gold/badcase expectation checks | `count_gold_passes`, `has_mapping_or_review`, `count_badcase_violations`, `evaluate_badcases` | Keep in evaluator or optional `EvaluationService`; these are evaluation concerns, not conversion services. |
| Report JSON/Markdown generation | `build_report`, `dataset_summary`, `write_markdown_report`, `metric_table` | Keep in evaluator or optional `EvaluationService`. |
| Simulated draft/active pack behavior | `phase_draft`, `active_aliases`, `draft_pending_pack_effective`, `old_run_snapshot_unchanged` in `run_evaluation` | `ReviewService`, `KnowledgeService`, `EffectiveTemplateService`; evaluator should only trigger the loop and compute metrics. |

## 6. Target Service Interfaces

These are intentionally minimal and aligned with existing contracts.

### SchemaService

Inputs:

- Dataset/root directory or storage root.
- `schema_id`, optional `version`.
- `TargetSchema` objects for validation.

Outputs:

- `TargetSchema`.
- Required fields list.
- Field lookup by id/name.
- Validation errors as exceptions or structured issue lists.

Minimum scope:

- File-backed registry over `examples/production_like/schemas/`.
- `load_schema(schema_id, version=None)`.
- `list_schemas()`.
- `validate_schema(schema)`.
- `get_required_fields(schema)`.
- `get_field(schema, field_name)`.

### TemplateService

Inputs:

- Dataset/root directory or storage root.
- `template_id`, optional `version`.
- Target `TargetSchema` for referential validation.

Outputs:

- `MappingTemplate`.
- Validation result.

Minimum scope:

- File-backed registry over `examples/production_like/mapping_templates/`.
- Validate aliases, regex rules, enum maps, defaults, and transform targets
  against schema fields.

### CandidateService

Inputs:

- `UIRDocument`.
- Task/doc ids for stable candidate ids.

Outputs:

- `list[FieldCandidate]`.

Minimum scope:

- Extract metadata candidates.
- Extract table row candidates from `UIRBlock.attributes.rows`.
- Extract block candidates from `UIRBlock.attributes.field_name`.
- Preserve `source_path`, `source_name`, `value_sample`, inferred type, and
  `source_blocks`.

### MappingService

Inputs:

- `UIRDocument`.
- `TargetSchema`.
- effective `MappingTemplate`.
- Candidate list.
- Runtime options, including LLM disabled/stub/OpenAI-compatible mode.

Outputs:

- `MappingReport`.
- Mapping decisions as `FieldMapping`-compatible dicts.
- Review-required items.
- Unmapped required fields.

Minimum scope:

- Strategies in order: exact, alias, regex, type, fuzzy, optional LLM suggestion, review/failed.
- Deterministic conflict and badcase-safe behavior.
- Stable mapping report structure compatible with the current evaluator metrics.

### TransformService

Inputs:

- `UIRDocument`.
- `TargetSchema`.
- effective `MappingTemplate`.
- Mapping decisions.

Outputs:

- Structured data dict.
- Transform trace/report.
- Warnings/errors.

Minimum scope:

- Rename/copy mapped values.
- Date normalization.
- Basic numeric normalization.
- Enum map.
- Defaults when explicit.
- Regex extraction when declared.
- No complex Chinese money parser in the first pass; record warning/candidate.

### CanonicalService

Inputs:

- `UIRDocument`.
- `TargetSchema`.
- Transformed data.
- Mapping/transform summaries.
- Execution snapshot.

Outputs:

- `CanonicalModel`.

Minimum scope:

- Preserve schema-aligned fields.
- Preserve blocks and source block ids.
- Preserve assets if present.
- Include doc metadata and execution snapshot references in `doc_meta`.

### RenderService

Inputs:

- `CanonicalModel`.
- Render options such as chunk size.

Outputs:

- Structured JSON payload.
- Markdown text.
- Chunks JSONL rows.

Minimum scope:

- Headings, paragraphs, lists, and conservative table text.
- Heading-aware chunks with non-empty text, title path, and source block ids.

### ValidationService

Inputs:

- `TargetSchema`.
- Structured data.
- Rendered outputs and chunks.

Outputs:

- `ValidationReport`.
- Optional `ConsistencyReport`.

Minimum scope:

- Required, type, enum, date, number, array, object checks.
- Optional missing fields are valid.
- Render output checks: JSON non-empty, Markdown non-empty, chunks non-empty,
  chunk source back-links valid.

### ManifestService

Inputs:

- Package file metadata.
- Task/schema/template/snapshot metadata.

Outputs:

- `Manifest`.

Minimum scope:

- File path, byte size, SHA-256, media type, role.
- Task id, doc id, schema/template ids and versions, output profile, generator,
  config snapshot.

### PackageService

Inputs:

- Rendered outputs.
- Mapping/transform/validation reports.
- Manifest metadata.
- Output directory.

Outputs:

- Package directory.
- ZIP path.
- `OutputPackageMetadata`.

Minimum scope:

- Write `structured.json`, `document.md`, `chunks.jsonl`,
  `mapping_report.json`, `transform_report.json`, `validation_report.json`,
  `manifest.json`, `verifier_report.json`.
- Create ZIP.

### PackageVerifierService

Inputs:

- Package directory or ZIP path.
- Manifest.

Outputs:

- Verifier report dict or `ConsistencyReport`.

Minimum scope:

- Required files exist.
- Manifest SHA-256 values match.
- Structured JSON and chunks parse.
- Markdown non-empty.

### TaskExecutionService

Inputs:

- Task id or task record.
- Optional execution options.

Outputs:

- Updated task status.
- Stored reports/package metadata.

Minimum scope:

- Explicit `execute_task(task_id)` pipeline:
  1. read UIR,
  2. load schema/template,
  3. resolve effective template,
  4. extract candidates,
  5. map,
  6. transform,
  7. build canonical,
  8. render,
  9. validate,
  10. package,
  11. update task state and paths.

### ReviewService

Inputs:

- Mapping report.
- Simulated or human review decisions.

Outputs:

- `ReviewRecord` items.

Minimum scope:

- Generate review items from `review_required_items`.
- Store or return simulated approvals for evaluator use.

### KnowledgeService

Inputs:

- Review records.
- Failed/unmapped mapping items.
- Badcase expectation rows.

Outputs:

- Learning candidates.
- Draft knowledge packs.
- Active knowledge packs.
- Metrics.

Minimum scope:

- Stable support for alias, gold mapping, and badcase candidates.
- Draft pack creation from approved candidates.
- Activation without modifying base template files.

### EffectiveTemplateService

Inputs:

- Base `MappingTemplate`.
- Active knowledge packs.
- Task overrides.

Outputs:

- Effective `MappingTemplate`.
- Resolution metadata for snapshot/report.

Minimum scope:

- Only active packs apply.
- Draft/pending packs do not apply.
- Deterministic ordering.
- Effective template stored in task snapshot.

### EvaluationService

Inputs:

- Production-like dataset cases and expectations.
- Pipeline result records.

Outputs:

- Metrics and report payloads.

Minimum scope:

- Optional. Keep metrics in `scripts/eval_production_like.py` initially unless
  report generation grows too large.

## 7. API Additions

Add APIs only after corresponding services exist and tests are green.

Suggested minimal route sequence:

1. Schema/template read APIs:
   - `GET /api/v1/schemas`
   - `GET /api/v1/schemas/{schema_id}`
   - `GET /api/v1/templates`
   - `GET /api/v1/templates/{template_id}`
2. Task execution and reports:
   - `POST /api/v1/tasks/{task_id}/execute`
   - `GET /api/v1/tasks/{task_id}/reports/mapping`
   - `GET /api/v1/tasks/{task_id}/reports/validation`
   - `GET /api/v1/tasks/{task_id}/package`
   - `GET /api/v1/tasks/{task_id}/package/download`
3. Knowledge loop:
   - `GET /api/v1/knowledge/candidates`
   - `POST /api/v1/knowledge/candidates/{candidate_id}/approve`
   - `POST /api/v1/knowledge/candidates/{candidate_id}/reject`
   - `POST /api/v1/knowledge/packs`
   - `POST /api/v1/knowledge/packs/{pack_id}/activate`
   - `GET /api/v1/knowledge/packs`
   - `GET /api/v1/knowledge/metrics`
4. Optional evaluation API:
   - `POST /api/v1/evaluation/production-like`
   - `GET /api/v1/evaluation/production-like/latest`

Do not add full CRUD until the file-backed registry and pipeline services are
stable.

## 8. Test Plan

Add tests in the same lightweight pytest style used by the current backend.

### Phase 2 Tests

- `test_schema_service_loads_production_like_schemas`.
- `test_schema_service_rejects_duplicate_field_names`.
- `test_schema_service_reports_required_fields`.
- `test_template_service_loads_production_like_templates`.
- `test_template_service_rejects_unknown_alias_target`.
- `test_template_service_rejects_unknown_regex_target`.
- `test_template_service_rejects_unknown_transform_target`.

### Phase 3 Tests

- Metadata extraction for policy/contract/meeting/general UIR.
- Table row extraction preserves `source_path`.
- Block `field_name` extraction preserves `source_blocks`.
- Missing metadata or empty blocks do not crash.

### Phase 4 Tests

- exact mapping.
- alias mapping.
- regex mapping.
- type mapping.
- fuzzy mapping enters review when confidence is low.
- conflict mapping enters review.
- badcase source is not high-confidence accepted.
- unmapped required fields are recorded.
- LLM fallback suggestions do not auto-accept.

### Phase 5-9 Tests

- Transform rename/date/number/enum/default/regex extraction.
- Transform failure records warning/error.
- Canonical model preserves data and source block ids.
- Markdown headings/lists/tables render.
- Chunks are non-empty and source-linked.
- Required missing field is validation error.
- Optional missing field is valid.
- Manifest SHA-256 matches file bytes.
- ZIP opens and contains required files.
- Verifier fails when a required file is missing.

### Phase 10-12 Tests

- Task execute success path.
- Task execute missing schema/template failure.
- Task execute review-required path.
- Package paths are stored and retrievable.
- Review records generated from mapping report.
- Alias/gold/badcase candidates derived.
- Pending candidate and draft pack do not affect mapping.
- Active pack affects effective template.
- Old task snapshot does not mutate after pack activation.

### Evaluator Regression Tests

- `python scripts/eval_production_like.py` succeeds.
- Report JSON/Markdown generated.
- Report states production services are called after Phase 11.
- `package_success_rate` remains 1.0 or failures are explained.
- `badcase_violation_count` remains 0.
- Before/after metrics remain explainable.

## 9. Phased Implementation Order

1. Keep this migration plan as the Phase 1 baseline.
2. Implement `SchemaService` and `TemplateService`.
3. Implement `CandidateService`.
4. Implement `MappingService`.
5. Implement `TransformService`.
6. Implement `CanonicalService`.
7. Implement `RenderService`.
8. Implement `ValidationService`.
9. Implement `ManifestService`, `PackageService`, and
   `PackageVerifierService`.
10. Implement `TaskExecutionService` and explicit execute endpoint.
11. Refactor `scripts/eval_production_like.py` so conversion calls the real
    service layer.
12. Implement `ReviewService`, `KnowledgeService`, and
    `EffectiveTemplateService`.
13. Add LLM fallback interface/stub.
14. Add minimal frontend only after backend pipeline is stable.
15. Update README, OpenAPI docs, reports, and project status documents.

## 10. Minimum Phase Boundaries

Each phase should be independently useful and testable:

- Phase 2 enables reusable schema/template loading without touching evaluator
  behavior.
- Phase 3 enables field candidate extraction without mapping.
- Phase 4 enables real mapping reports while evaluator can still own rendering
  and packaging.
- Phase 5-9 produce real conversion artifacts and packages.
- Phase 10 exposes pipeline execution through task semantics.
- Phase 11 is the evaluator migration point.
- Phase 12 replaces simulated active aliases with real review/knowledge/effective
  template behavior.

## 11. Current Risks And Uncertainty

- The current evaluator contains some mojibake text in heuristic token strings
  when displayed through PowerShell. Production services should keep source files
  UTF-8 and add tests using readable Chinese fixture strings.
- The database schema includes future tables, but there are no persistence
  services for candidates, mappings, reports, packages, or reviews. Early phases
  should avoid over-coupling to DB writes until service contracts settle.
- `MappingReport.summary` is currently a flexible dict. This is convenient but
  can drift. Future tests should lock the keys used by evaluator metrics.
- `TaskService.create_task` does not validate schema/template existence. This is
  acceptable for the current baseline but should be addressed once
  SchemaService/TemplateService exist.
- The frontend source tree is intentionally minimal and demo-oriented. It should
  not be treated as a complete production workflow or deployment package yet.
- Existing package artifacts under `reports/packages/` are generated by the
  harness, not by production services. They should not be treated as proof of a
  real package layer after this plan.
- Knowledge pack persistence is not modeled yet; the current service layer keeps
  the pack workflow deterministic and in memory for evaluator and API-adjacent
  use.
- `docs/openapi.json` is generated by `scripts/export_openapi.py`; rerun it
  whenever API routes or schemas change.

## 12. Immediate Next Step

The migration phases and follow-up development plan are now implemented through
Phase 22. Completed follow-up work includes database-backed knowledge workflows,
catalog governance, downstream package smoke tests, training-corpus export,
optional OpenAI-compatible LLM fallback, frontend display enhancements, final
delivery documents, and a local container deployment profile. Next work should
be planned as production hardening, such as authenticated operator controls,
artifact retention/audit logging, OpenAPI client publication, hosted model
operations, or production access controls.

Run backend tests, lint, and the production-like evaluator after the phase.
