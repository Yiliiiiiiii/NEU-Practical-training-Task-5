# Topic 5 Phase 3 SchemaPack Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute `docs/guildline/topic5_phase3_schemapack_contract_and_output_assertions.md` against the accepted Phase 2 branch and satisfy every Phase 3 acceptance check.

**Architecture:** Pydantic models are the runtime source of truth for manifests, assertion definitions, and reports; committed JSON Schemas are generated from those models. Reusable services load manifest-referenced assets, resolve a deliberately small JSON-path subset, validate cross-file contracts, and evaluate deterministic assertions. Existing inline conversion and Package 1.1 stay backward compatible, while registered task execution persists assertion evidence atomically.

**Tech Stack:** Python 3.13, Pydantic 2, PyYAML safe loading, pytest, FastAPI/OpenAPI, existing Package 1.1 services.

## Global Constraints

- `schema_pack.yaml`, `output_assertions.yaml`, `ConversionAssertionService`, and `conversion_assertion_report.json` are the canonical names.
- Assertions are deterministic only; no quality score, grade, semantic judgment, LLM call, or publication/routing recommendation may be added.
- Assertions remain optional for legacy requests and Package 1.1.
- Asset paths must be relative regular files contained by the selected SchemaPack directory.
- Aggregate mapping thresholds are hard failures; per-schema required-missing and badcase violations are hard failures; per-schema precision/recall below `0.85` are warnings in Phase 3.
- Repair thresholds are `0.82` for auto acceptance and `0.62` for review-required candidates.
- The normative requirements, interfaces, fixtures, and acceptance matrix remain the 2,898-line user-supplied execution document; this delta plan records repository-specific execution units without duplicating it.

---

### Task 1: Complete Phase 2 carry-over fixes

**Files:**
- Modify: `scripts/validate_schema_pack.py`
- Modify: `scripts/eval_topic5_standard_uir_mapping.py`
- Modify: `scripts/check_topic5_mapping_quality_gate.py`
- Modify: `backend/app/services/mapping_repair_service.py`
- Modify: `backend/tests/test_schema_pack_contract_validation.py`
- Modify: `backend/tests/test_topic5_standard_uir_eval.py`
- Modify: `backend/tests/test_mapping_repair_service.py`
- Update generated mapping reports and claim-boundary documents named in normative sections 1.2, 1.3, and 1.5.

**Interfaces:**
- Produces mapping metrics `conversion_success_rate`, `package_verifier_pass_rate`, and `package_verified_count`.
- Produces repair report fields `accepted_repair_fields`, `review_repair_fields`, and `unrepaired_fields`.

- [ ] Add one failing regression test for each carry-over behavior, run the targeted test, and confirm the expected failure.
- [ ] Implement regex exception handling, truthful package verification, per-schema gate policy, and three-band repair behavior with the smallest compatible changes.
- [ ] Run the three targeted test modules and confirm they pass.

### Task 2: Add strict SchemaPack and assertion contracts

**Files:**
- Create: `backend/app/schemas/schema_pack_contract.py`
- Create: `backend/app/schemas/conversion_assertions.py`
- Create: `backend/app/schemas/conversion_assertion_report.py`
- Create/replace generated: `schema_packs/schema_pack_contract.schema.json`
- Create generated: `schema_packs/output_assertions_contract.schema.json`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_schema_pack_service.py`
- Test: `backend/tests/test_schema_pack_contract_validation.py`

**Interfaces:**
- Produces `SchemaPackManifest`, `ConversionAssertionConfig`, `ConversionAssertionReport`, strict semantic-version validation, unique assertion IDs, operator-parameter validation, and safe asset-path validation.

- [ ] Write contract tests for a valid manifest plus invalid semver, unknown fields, duplicate IDs, unsafe paths, invalid JSON paths, regex, severity, operator, and parameters; confirm RED.
- [ ] Implement strict models and generated JSON Schema exports; add pinned PyYAML and use `yaml.safe_load` only.
- [ ] Run the contract tests and confirm GREEN.

### Task 3: Implement reusable loading, path resolution, assertions, and validation

**Files:**
- Modify: `backend/app/services/schema_pack_service.py`
- Create: `backend/app/services/json_path_service.py`
- Create: `backend/app/services/conversion_assertion_service.py`
- Create: `backend/app/services/schema_pack_contract_validator.py`
- Refactor: `scripts/validate_schema_pack.py`
- Test: `backend/tests/test_schema_pack_service.py`
- Test: `backend/tests/test_json_path_service.py`
- Test: `backend/tests/test_conversion_assertion_service.py`
- Test: `backend/tests/test_schema_pack_contract_validation.py`

**Interfaces:**
- Consumes the Task 2 models.
- Produces manifest-only asset loading, `PathResolution`, all 13 required deterministic operators, bounded issue previews, deterministic result ordering, evidence enrichment, and reusable layered contract validation.

- [ ] Write and run failing service tests covering the complete normative test matrix.
- [ ] Implement the minimal services and thin CLI wrapper.
- [ ] Run all four targeted modules and confirm GREEN.

### Task 4: Migrate example packs and regression fixtures

**Files:**
- Create manifests, assertion definitions, `examples/`, and `badcases/` under `schema_packs/examples/announcement_doc/` and `schema_packs/examples/event_notice_doc/`.
- Modify: `backend/tests/test_topic5_inline_schema_pack.py`

**Interfaces:**
- Produces two fully valid packs with stable positive expected content/assertion fixtures and badcases that name exact failed assertion IDs.

- [ ] Add failing fixture-presence and contract-validation tests.
- [ ] Add manifests, assertions, positive examples, badcases, and negative-pair fixtures without encoding fixtures into implementation logic.
- [ ] Validate both packs and confirm the intended positive/badcase behavior.

### Task 5: Integrate assertions and preserve Package 1.1

**Files:**
- Modify: `backend/app/schemas/topic5_convert.py`
- Modify: `backend/app/services/topic5_conversion_service.py`
- Modify: `backend/app/services/task_execution_service.py`
- Modify: `backend/app/services/storage_service.py`
- Modify: `backend/app/services/package_service.py`
- Modify as needed: `backend/app/services/manifest_service.py`
- Test: `backend/tests/test_topic5_conversion_assertion_integration.py`
- Test: `backend/tests/test_package_1_1_assertion_report_compatibility.py`

**Interfaces:**
- Consumes optional inline/manifest assertion configs.
- Produces optional response/report artifact, request-over-manifest-over-application option precedence, warning/completed, error/review-required, strict/failed semantics, atomic task persistence, and optional checksummed package inclusion.

- [ ] Add failing integration and package compatibility tests for every normative branch.
- [ ] Implement optional assertion evaluation after schema validation and before package creation; persist via atomic storage writes.
- [ ] Run targeted integration/package tests and confirm legacy fixtures remain GREEN.

### Task 6: Add evaluator, Phase 3 gate, documentation, and evidence

**Files:**
- Create: `scripts/eval_schema_pack_contracts.py`
- Create: `scripts/check_schema_pack_contract_gate.py`
- Create/update tests: `backend/tests/test_schema_pack_contract_eval.py`
- Create/update all documents and generated evidence listed in normative sections 21 and 25.

**Interfaces:**
- Produces deterministic single/all-pack JSON and Markdown evaluation, a Phase 3 gate that always writes evidence, and exact Topic 5/Topic 6/Topic 11 boundary documentation.

- [ ] Write failing evaluator/gate tests for positive examples, expected badcases, unexpected behavior, stable ordering, report creation, and exit semantics.
- [ ] Implement evaluator and gate without scores, grades, or route recommendations.
- [ ] Update documents, regenerate OpenAPI and reports, and scan for forbidden overclaims.
- [ ] Run the two pack validators, all-pack evaluator, inline demos, Phase 3 gate, Phase 2 mapping gate with `--verify-package`, alignment gate, `scripts/verify_all.py --check-openapi`, frontend tests, and a line-by-line Phase 3 acceptance audit.

## Plan Self-Review

- Spec coverage: Tasks 1-6 cover normative implementation order steps 1-14, acceptance sections 26.1-26.7, and every required evidence artifact.
- Placeholder scan: no `TBD`, deferred implementation, or undefined neighboring interface remains; detailed model fields and operator semantics are intentionally referenced to the user-supplied normative document.
- Type consistency: the plan uses the document's canonical class, field, metric, option, and artifact names throughout.
