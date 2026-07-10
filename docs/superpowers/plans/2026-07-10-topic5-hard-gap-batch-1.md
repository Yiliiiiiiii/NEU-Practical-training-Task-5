# Topic 5 Hard-Gap Batch 1 Implementation Plan

> **For agentic workers:** Execute inline only. The governing execution specification forbids multi-agent orchestration. Use test-first cycles and keep every workstream independently testable.

**Goal:** Close the first-batch Topic 5 hard gaps while preserving deterministic conversion, Package 1.1 compatibility, legacy requests, and the Topic 5 responsibility boundary.

**Architecture:** Keep `CanonicalModel` as the semantic source of truth. Add strict configuration/report models and pure services for metadata rendering, document summaries, chunk-provider resolution, and artifact consistency; call the same services from inline and registered execution. Package feature declarations make new artifacts mandatory only for new packages, leaving legacy verification intact.

**Tech Stack:** Python 3.13, Pydantic 2, FastAPI, SQLAlchemy, pytest, Ruff, JSON Schema, YAML, TypeScript/Vite/Vitest.

## Global Constraints

- Start from normalized UIR JSON; do not add source-file parsing, OCR, cleaning, entity linking, embeddings, RAG, quality scoring, or publication routing.
- Keep `POST /api/v1/topic5/convert` and `/convert/package` compatible.
- Keep `mapping_rules` preferred and `mapping_template` as the backward-compatible alias.
- LLM output remains report-only/review-required and cannot activate production configuration.
- New configuration is strict, deterministic, non-executable, replayable, and secret-safe.
- Follow red-green-refactor for production behavior changes.

---

### Task 0: Baseline and contract inventory

**Files:**
- Create: `docs/交接/evidence/hard_gap_batch_1/baseline/*`
- Create: `docs/superpowers/plans/2026-07-10-topic5-hard-gap-batch-1.md`

**Produces:** Baseline commit/environment, full and focused test logs, OpenAPI path count, existing gate summaries, and pre-existing warnings.

- [x] Run `backend/.venv/Scripts/python.exe scripts/verify_all.py --check-openapi` and save output.
- [x] Run focused backend tests and `frontend/npm.cmd test`; save output.
- [x] Record mapping/package gate state without changing their denominator or expected results.
- [ ] Commit only baseline evidence and this execution plan.

### Task 1: Strict batch contracts

**Files:**
- Create: `backend/app/schemas/metadata_template.py`
- Create: `backend/app/schemas/document_summary.py`
- Create: `backend/app/schemas/chunk_provider.py`
- Create: `backend/app/schemas/artifact_consistency.py`
- Modify: `backend/app/schemas/topic5_convert.py`, `uir.py`, and `content_organization.py`
- Create: `contracts/topic11_chunk_request.schema.json`, `contracts/topic11_chunk_response.schema.json`
- Test: `backend/tests/test_topic5_hard_gap_contracts.py`

**Interfaces:** `MetadataTemplateConfig` validates safe sources and typed fields; `UIREntity` preserves upstream identity; content options own tag/summary/provider configuration; consistency/provider reports are strict.

- [ ] Write valid-legacy and invalid/unsafe contract tests, then verify RED.
- [ ] Implement the minimum strict models and JSON schemas, then verify GREEN and Ruff.
- [ ] Commit the independently passing contract layer.

### Task 2: Metadata template engine

**Files:**
- Create: `backend/app/services/metadata_template_service.py`
- Modify: canonical, render, inline execution, registered execution, package, and verifier services.
- Test: `backend/tests/test_metadata_template_service.py`, `test_topic5_metadata_integration.py`

**Interface:** `MetadataTemplateService.render(*, uir, transformed_fields, template, system_context) -> MetadataRenderResult`.

- [ ] Add failing resolution/default/type/missing/unsafe/two-template/equivalence/package/legacy tests.
- [ ] Implement safe deterministic rendering and exact issues.
- [ ] Thread one result through canonical, JSON, response, reports, package, verifier, and status.
- [ ] Run focused/integration tests and commit.

### Task 3: Configuration-driven tags and local quality scope

**Files:**
- Modify: `backend/app/services/chunk_organizer_service.py`, SchemaPack `content_org.yaml`, and benchmark configs.
- Test: `backend/tests/test_topic5_tag_rules.py`, `test_topic5_chunk_quality_localization.py`

**Interfaces:** content rules use audited term/title/block predicates; management rules use whitelisted metadata paths and one `{value}`; quality rules select built-in facts and produce scope/evidence traces.

- [ ] Add failing configuration, migration, no-rules, determinism, malformed-rule, and issue-localization tests.
- [ ] Remove schema-family tag tables and operational identifiers from management tags.
- [ ] Localize issues through canonical source blocks and retain global flags at document scope.
- [ ] Run focused tests/evaluation and commit each reviewable change.

### Task 4: Entity passthrough and extractive document summary

**Files:**
- Modify: UIR/canonical schemas, chunk organizer, render, both execution services, and package service.
- Create: `backend/app/services/document_summary_service.py`
- Test: `backend/tests/test_topic5_entity_passthrough.py`, `test_document_summary_service.py`

**Interfaces:** entity assignment prioritizes block intersection and never synthesizes IDs; `DocumentSummaryService.build(...)` selects exact normalized source substrings with sentence traces.

- [ ] Add failing linked/unlinked/NIL/relevance/determinism/legacy entity tests.
- [ ] Remove default field-name inference and implement passthrough.
- [ ] Add failing section/fallback/dedupe/limits/empty/table/faithfulness/disabled/renderer tests.
- [ ] Implement one shared summary object; run tests and commit.

### Task 5: Replaceable Topic 11 provider

**Files:**
- Create: `backend/app/services/chunk_providers/{base,internal,topic11_http,resolver}.py`
- Modify: `backend/app/config.py` and both execution services.
- Test: `backend/tests/test_topic11_chunk_provider.py`

**Interfaces:** versioned request/response contracts; resolver returns chunks and a sanitized trace; invalid external output falls back or raises in strict mode.

- [x] Add failing internal/valid mock/timeout/HTTP/schema/block/entity/hallucination/strict/config/offline/secret tests.
- [x] Implement runtime-only networking and full external-output validation.
- [x] Run tests and commit.

### Task 6: Canonical cross-artifact consistency

**Files:**
- Create: `backend/app/services/artifact_consistency_service.py`
- Modify: render, both execution, package, manifest, and verifier services.
- Test: `backend/tests/test_artifact_consistency_service.py`, `test_topic5_package_features.py`

**Interface:** `ArtifactConsistencyService.verify(*, canonical, structured_json, markdown, chunks, document_summary) -> ArtifactConsistencyReport`.

- [x] Add failing JSON/Markdown/block/chunk/summary/metadata tampering and legacy tests.
- [x] Add deterministic Markdown markers and consistency verification.
- [x] Add feature-dependent reports, roles, checksums, and verifier requirements.
- [x] Run negative/package tests and commit.

### Task 7: Expanded deterministic evidence and gate

**Files:**
- Create: at least 110 field-operation and 40 localization cases under `eval/`.
- Create: `scripts/eval_topic5_field_operations.py`, `eval_topic5_schema_localization.py`, `check_topic5_hard_gap_batch_1_gate.py`.
- Test: `backend/tests/test_topic5_hard_gap_evaluators.py`
- Create: `docs/交接/evidence/hard_gap_batch_1/operations/*`

- [ ] Add failing evaluator/gate tests proving fixed denominators and thresholds.
- [ ] Add fixtures/evaluators against production services/contracts.
- [ ] Run evaluators and gate; commit datasets/scripts/reports.

### Task 8: Documentation, OpenAPI, golden artifacts, and final verification

**Files:** Update public API/package/lineage/SchemaPack docs and handoff docs; create `docs/交接/topic5_hard_gap_batch_1_result.md`; regenerate `docs/openapi.json` and final evidence.

- [ ] Add/refresh announcement and event-notice golden tests and three-run semantic hashes.
- [ ] Run full backend/Ruff/frontend/OpenAPI/SchemaPack/inline/evaluator/gate commands.
- [ ] Review scope, secrets, compatibility, evidence accuracy, and untracked user files.
- [ ] Commit documentation/evidence and record all commit SHAs.
