# Phase B+ Semantic Quality and Review Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Phase B+ semantic mapping quality, strict normalization, controlled review assistant, reporting, and regression gates defined in `docs/guildline/Phase_B_plus_Codex_Review_执行文档.md`.

**Architecture:** Extend the existing UIR → CandidateService → MappingService → TransformService → ValidationService pipeline without changing its production input boundary. Candidate metadata and mapping ranking remain deterministic and source-backed; unsafe/ambiguous decisions remain pending or blocked. Evaluation runs use an isolated SQLite database and storage root so historical active knowledge packs cannot contaminate the baseline or final evidence.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, pytest, httpx, Ruff, React/Vite.

---

### Task 1: Freeze a clean Phase B+ baseline

**状态**
- [x] 任务完成

**Dependencies:** None
**Parallelizable:** No (all later metric comparisons depend on this baseline)

**Files:**
- Create: `reports/phase_bplus_baseline_non_procurement_mapping_eval_report.json`
- Create: `reports/phase_bplus_baseline_non_procurement_mapping_eval_report.md`
- Create: `reports/phase_bplus_baseline_non_procurement_gap_analysis.json`
- Create: `reports/phase_bplus_baseline_non_procurement_gap_analysis.md`
- Create: `reports/evaluation_center/current_metrics.phase_bplus_baseline.json`
- Create: `reports/evaluation_center/regression_gates.phase_bplus_baseline.json`

- [x] Start a backend with isolated `DATABASE_URL` and `STORAGE_ROOT`.
- [x] Run `scripts/eval_non_procurement_mapping.py` and record the clean summary.
- [x] Run `scripts/analyze_non_procurement_gaps.py`.
- [x] Freeze the Evaluation Center inputs.
- [x] Record the discovered historical-database contamination without changing `schemapack.db`.

### Task 2: Add the semantic mapping quality analyzer

**状态**
- [ ] 任务完成

**Dependencies:** Task 1
**Parallelizable:** Yes

**Files:**
- Create: `scripts/analyze_semantic_mapping_quality.py`
- Create: `backend/tests/test_analyze_semantic_mapping_quality.py`

- [ ] Write failing tests for `candidate_not_extracted`, `transform_invalid`, forbidden-pair safety, badcase counts, and Markdown sections.
- [ ] Run `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_analyze_semantic_mapping_quality.py -q` and confirm the missing module/behavior fails.
- [ ] Implement package discovery by reusing the safe ZIP/package readers and scoring helpers from `analyze_non_procurement_gaps.py`.
- [ ] Normalize every gap into one of the eight required Phase B+ gap types and produce summary, grouped counts, ranked fixes, unsafe candidates, strict failures, and gold-label suspicions.
- [ ] Render the required Markdown sections and CLI arguments.
- [ ] Re-run the focused tests and Ruff on the script.

### Task 3: Enhance traceable non-procurement candidates

**状态**
- [ ] 任务完成

**Dependencies:** Task 1
**Parallelizable:** Yes

**Files:**
- Modify: `backend/app/schemas/mapping.py`
- Modify: `backend/app/services/candidate_service.py`
- Modify: `backend/tests/test_candidate_service_non_procurement.py`

- [ ] Add failing tests for meeting topics/date/number, policy issuer/publish date, and general application conditions/service object, including all prohibited negative cases.
- [ ] Confirm the new tests fail for missing candidate metadata or extraction behavior.
- [ ] Add backward-compatible `target_hints`, `evidence_type`, `confidence_hint`, and `quality_flags` fields to `FieldCandidate`.
- [ ] Extend focused section, key-value, opening-sentence, numbered-heading, metadata, and signature extraction while preserving `source_path` and `source_blocks`.
- [ ] Assign medium/low confidence to ambiguous publisher, issuer, date, and agenda evidence; never promote the forbidden labels.
- [ ] Re-run candidate tests and the clean non-procurement evaluator.

### Task 4: Add evidence-aware ranking and forbidden guards

**状态**
- [ ] 任务完成

**Dependencies:** Task 3
**Parallelizable:** No (ranking consumes the new candidate evidence)

**Files:**
- Modify: `backend/app/schemas/mapping.py`
- Modify: `backend/app/services/mapping_service.py`
- Create: `backend/tests/test_mapping_service_evidence_ranking.py`
- Create: `backend/tests/test_mapping_service_badcase_guards.py`

- [ ] Write failing tests for safe high-evidence acceptance, medium issuer review, all ten forbidden pairs, LLM-only pending behavior, and `ranking_trace`.
- [ ] Confirm the tests fail because ranking traces and complete guards are absent.
- [ ] Implement the documented weighted components and risk penalty with deterministic scores.
- [ ] Rank eligible candidates per target instead of accepting the first label match.
- [ ] Emit `ranking_trace` and `rejected_candidates` on every decision where candidates were considered.
- [ ] Force forbidden pairs to blocked/rejected decision context and keep LLM/fuzzy medium-low mappings out of accepted mappings.
- [ ] Re-run focused tests, existing mapping tests, and the clean evaluator.

### Task 5: Improve transforms and strict validation evidence

**状态**
- [ ] 任务完成

**Dependencies:** Task 3, Task 4
**Parallelizable:** No (validation classifies transformed mapping outputs)

**Files:**
- Modify: `backend/app/schemas/reports.py`
- Modify: `backend/app/services/transform_service.py`
- Modify: `backend/app/services/validation_service.py`
- Modify: `scripts/analyze_strict_validation_failures.py`
- Create: `backend/tests/test_transform_non_procurement_dates.py`
- Create: `backend/tests/test_transform_non_procurement_lists.py`
- Create: `backend/tests/test_validation_strict_non_procurement.py`

- [ ] Write failing tests for Arabic/Chinese dates (including time-of-day suffixes), ordered list splitting, organization prefix cleanup, and all strict failure classes.
- [ ] Confirm failures are caused by unsupported normalization/report fields.
- [ ] Implement `zh_date_normalizer_v2` with real calendar validation.
- [ ] Implement ordered list normalization for the documented fields and conservative review flags for uncertain splits.
- [ ] Implement lightweight organization-label cleanup without entity linking.
- [ ] Extend report models with backward-compatible `schema_valid`, `strict_semantic_valid`, `failure_type`, source value, and suggested normalized value fields.
- [ ] Update the strict analyzer classification and Markdown output.
- [ ] Re-run focused and existing artifact/package tests.

### Task 6: Implement the controlled Codex Review Assistant

**状态**
- [ ] 任务完成

**Dependencies:** Task 4, Task 5
**Parallelizable:** No (assistant decisions depend on final mapping evidence)

**Files:**
- Create: `scripts/codex_review_assistant.py`
- Create: `backend/tests/test_codex_review_assistant_decisions.py`
- Create: `backend/tests/test_codex_review_assistant_api_safety.py`

- [ ] Write failing decision tests for safe approve, forbidden reject, and every required keep-pending condition.
- [ ] Write failing API tests proving dry-run/export-only do not mutate reviews, apply-safe honors both limits, retries isolated failures, and emits reports.
- [ ] Implement current-API compatibility by joining review records with their task mapping reports.
- [ ] Implement pure decision functions with an explicit safe allowlist and the ten forbidden pairs.
- [ ] Implement `dry-run`, `apply-safe`, and `export-only`, filters, API key, retry/error recording, JSON, and Markdown outputs.
- [ ] Send the required decision request bodies and never create knowledge candidates for rejected or keep-pending items.
- [ ] Re-run focused tests and generate dry-run/apply-safe reports against an isolated Phase B+ database.

### Task 7: Close the knowledge, metrics, and final evidence loop

**状态**
- [ ] 任务完成

**Dependencies:** Task 2, Task 3, Task 4, Task 5, Task 6
**Parallelizable:** No (final reports must reflect all implementation changes)

**Files:**
- Modify: `reports/evaluation_center/current_metrics.json`
- Modify: `reports/evaluation_center/regression_gates.json`
- Create: all final Phase B+ reports listed in the execution document
- Modify: relevant handoff/developer documentation only for verified results

- [ ] Run the clean final dataset evaluator and refresh `reports/real_world_packages`.
- [ ] Run semantic and strict analyzers on the refreshed packages.
- [ ] Run Review Assistant dry-run, inspect at least 20 suggestions, then run apply-safe with the documented caps.
- [ ] Run knowledge-loop evaluators and verify draft-no-effect, future-task-only active effect, unchanged old snapshots, no rejected activation, and zero badcase violations.
- [ ] Populate actual metric values and add the seven Phase B+ gates without weakening existing gates.
- [ ] Run backend tests, Ruff, frontend tests/build, OpenAPI export/check, all Phase B+ evaluators, and `verify_all.py --check-openapi`.
- [ ] Update documentation with only observed metrics and list every unmet Definition-of-Done item as a remaining issue.

---

**Execution Mode:** serial
