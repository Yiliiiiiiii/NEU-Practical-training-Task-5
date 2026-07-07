# Phase C Strict Semantic Template Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute Phase C by unifying report semantics, improving strict semantic mapping for the existing 35 non-procurement samples, adding safe review/knowledge evidence tooling, and only then expanding toward 50 samples when gates allow.

**Architecture:** Keep the API-backed evaluators as the source of truth, add run metadata and a consistency checker around their outputs, and make targeted source-backed candidate/ranking/normalization improvements without weakening schemas or badcase filters. Review/knowledge automation remains conservative: Codex may export evidence and apply explicit human decisions, but must not auto-approve low-confidence or risky reviews or activate packs.

**Tech Stack:** Python, FastAPI service layer, SQLite-backed local evaluation, pytest, ruff, existing real-world UIR/gold/badcase fixtures.

---

### Task 1: Sprint 0 report metadata and consistency checker

**状态**
- [ ] 任务完成

**Dependencies:** None  
**Parallelizable:** Yes

**Files:**
- Modify: `scripts/eval_non_procurement_mapping.py`
- Modify: `scripts/analyze_semantic_mapping_quality.py`
- Modify: `scripts/analyze_strict_validation_failures.py`
- Create: `scripts/check_phase_c_report_consistency.py`
- Create: `backend/tests/test_phase_c_report_consistency.py`

- [ ] Add failing tests for run metadata and consistency comparison.
- [ ] Implement shared report metadata fields: `run_id`, `generated_at`, `git_branch`, `git_commit`, `packages_root`, `gold_path`, `badcases_path`, `dataset_size`, `report_version`.
- [ ] Implement `scripts/check_phase_c_report_consistency.py` to compare mapping, semantic-quality, and strict-validation reports.
- [ ] Verify with targeted pytest and ruff.
- [ ] Commit Sprint 0.

### Task 2: Sprint 1 strict semantic fixes for the 35-sample set

**状态**
- [ ] 任务完成

**Dependencies:** Task 1  
**Parallelizable:** No (metrics depend on the unified report path)

**Files:**
- Modify: `backend/app/services/transform_service.py`
- Modify: `backend/app/services/candidate_service.py`
- Modify: `backend/app/services/mapping_service.py`
- Modify: `backend/tests/test_candidate_service_non_procurement.py`
- Modify: `backend/tests/test_mapping_service_evidence_ranking.py`
- Create: `backend/tests/test_transform_doc_type_normalizer.py`

- [ ] Add RED tests for `policy_doc.doc_type` enum normalization.
- [ ] Add RED tests for safe policy publish/effective date extraction and forbidden evidence rejection.
- [ ] Add RED tests for meeting date/organizer/topics extraction and general service-object/application-conditions ranking.
- [ ] Implement minimal normalizer/extraction/ranking changes.
- [ ] Verify targeted tests, badcase tests, and non-procurement evaluator.
- [ ] Commit Sprint 1.

### Task 3: Sprint 2 safe template and forbidden-pair hardening

**状态**
- [ ] 任务完成

**Dependencies:** Task 2  
**Parallelizable:** No (depends on observed Sprint 1 gaps)

**Files:**
- Modify: `examples/production_like/mapping_templates/general_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/meeting_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/policy_doc_base_v1.json`
- Modify: `backend/app/services/mapping_service.py`
- Modify: `backend/tests/test_non_procurement_templates.py`
- Modify: `backend/tests/test_non_procurement_badcases.py`

- [ ] Add tests for safe exact/conditional aliases and forbidden pairs.
- [ ] Add only source-backed aliases/regex rules that do not weaken badcase safety.
- [ ] Run template/badcase tests and 35-sample evaluator.
- [ ] Commit Sprint 2.

### Task 4: Sprint 3 review evidence and manual-decision tooling

**状态**
- [ ] 任务完成

**Dependencies:** Task 1  
**Parallelizable:** Yes

**Files:**
- Create: `scripts/build_review_evidence_pack.py`
- Create: `scripts/apply_manual_review_decisions.py`
- Create: tests under `backend/tests/` for evidence export and manual apply safety.

- [ ] Add tests that no review is changed without an explicit manual decision.
- [ ] Implement evidence pack export with risk flags, source excerpts, badcase state, and Codex suggestion.
- [ ] Implement manual decision apply with `operator="human"` required for approve.
- [ ] Generate review evidence and impact reports without activating a pack.
- [ ] Commit Sprint 3.

### Task 5: Sprint 4 expansion gate and sample growth

**状态**
- [ ] 任务完成

**Dependencies:** Task 1, Task 2, Task 3  
**Parallelizable:** No (must wait for 35-sample gates)

**Files:**
- Modify: `examples/real_world/sources/source_manifest.json`
- Modify/Create: `examples/real_world/uir/{general,meeting,policy}/*.json`
- Modify: `examples/real_world/gold/mapping_gold.jsonl`
- Modify: `examples/real_world/gold/real_world_badcases.jsonl`
- Modify/Create: real-world extraction/validation reports as required.

- [ ] Confirm pre-expansion gates: average recall >= 0.72, strict pass >= 28/35, badcase 0, llm auto accepted 0, consistency passed.
- [ ] If gates pass, add five complex real samples per non-procurement doc type using official public sources.
- [ ] Add source-backed gold labels and badcases for each new sample.
- [ ] Run expanded evaluators and Phase C gates.
- [ ] Commit dataset expansion.

### Task 6: Final verification and handoff

**状态**
- [ ] 任务完成

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5  
**Parallelizable:** No

**Files:**
- Modify: `reports/evaluation_center/current_metrics.json`
- Modify: `reports/evaluation_center/regression_gates.json`
- Generated ignored reports under `reports/`.

- [ ] Run `python scripts/verify_all.py --check-openapi`.
- [ ] Run API-backed evaluators on an isolated database.
- [ ] Update regression gates with current Phase C metrics; mark expanded gates planned if expansion is not executed.
- [ ] Check git status and commit remaining tracked changes.
- [ ] Report metrics, residual gaps, and safety constraints.

---

**Execution Mode:** inline
