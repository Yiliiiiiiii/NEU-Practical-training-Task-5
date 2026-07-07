# Phase D/E/F DeepSeek Review Judge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.executing-plans or direct serial execution. Do not spawn Codex subagents unless the user explicitly requests delegation; the “Review Judge Sub-Agent” in this plan is a product feature/script, not a Codex worker.

**Goal:** Improve non-procurement semantic mapping toward Phase D targets, add safe DeepSeek-assisted review evidence, and create the Phase F shadow/blind-set scaffolding without weakening safety gates.

**Architecture:** Keep deterministic candidate extraction and safety gates as the source of truth. DeepSeek is used only for report-only suggestions or review assistance; Review Judge decisions remain auditable and cannot bypass badcase, source-evidence, or high-risk-field checks.

**Tech Stack:** FastAPI backend, Pydantic schemas, existing mapping/review services, Python evaluator scripts, JSON/Markdown reports.

---

### Task 1: Branch, secret handling, and baseline

**Status**
- [ ] Completed

**Dependencies:** None
**Parallelizable:** No (establishes safe execution context)

**Files:**
- Read: `backend/app/config.py`
- Read: `backend/app/services/deepseek_client.py`
- Read: `backend/app/services/llm_fallback_service.py`
- Generate: `reports/phase_d_baseline_non_procurement_mapping_eval_report.json`
- Generate: `reports/phase_d_baseline_non_procurement_mapping_eval_report.md`

- [ ] Confirm no tracked dirty files before work.
- [ ] Create branch `codex/phase-d-deepseek-review-judge`.
- [ ] Use `DEEPSEEK_API_KEY` only as a process environment variable; never write it to tracked files or reports.
- [ ] Run `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- [ ] Start backend and run Phase D baseline evaluator.

### Task 2: UIR quality gate

**Status**
- [ ] Completed

**Dependencies:** Task 1
**Parallelizable:** No (feeds later mapping policy)

**Files:**
- Create: `backend/app/schemas/uir_quality_gate.py`
- Create: `backend/app/services/uir_quality_gate_service.py`
- Create: `scripts/eval_uir_quality_gate.py`
- Test: `backend/tests/test_uir_quality_gate_service.py`
- Generate: `reports/uir_quality_gate_eval_report.json`
- Generate: `reports/uir_quality_gate_eval_report.md`

- [ ] Implement pass/review/reject/unsupported quality gate with traceable issues.
- [ ] Keep supported doc type and source-evidence checks explicit.
- [ ] Verify real-world UIRs pass or produce reviewable issues, not silent acceptance.

### Task 3: Field extractor registry and Phase D semantic hardening

**Status**
- [ ] Completed

**Dependencies:** Task 2
**Parallelizable:** No (touches mapping core)

**Files:**
- Create: `backend/app/services/field_extractors/base.py`
- Create: `backend/app/services/field_extractors/policy_extractors.py`
- Create: `backend/app/services/field_extractors/meeting_extractors.py`
- Create: `backend/app/services/field_extractors/general_extractors.py`
- Modify: `backend/app/services/candidate_service.py`
- Test: `backend/tests/test_policy_field_extractors.py`
- Test: `backend/tests/test_meeting_field_extractors.py`
- Test: `backend/tests/test_general_field_extractors.py`

- [ ] Extract safe policy fields: publish_date, issuer, effective_date, policy_measures, target_audience.
- [ ] Extract safe meeting fields: meeting_number, topics, organizer, attendees, meeting_date.
- [ ] Improve general_doc ranking for application_conditions/contact/service_object.
- [ ] Preserve forbidden pairs and keep high-risk ambiguity review-required.

### Task 4: Conditional template and evidence ranking

**Status**
- [ ] Completed

**Dependencies:** Task 3
**Parallelizable:** No (changes ranking semantics)

**Files:**
- Modify: mapping/ranking services identified during exploration
- Test: `backend/tests/test_conditional_template_aliases.py`
- Test: `backend/tests/test_evidence_ranking.py`

- [ ] Add doc-type-specific positive and negative evidence contexts.
- [ ] Add traceable score breakdown fields where reports already expose ranking traces.
- [ ] Ensure LLM support cannot make an LLM-only candidate auto-accepted.

### Task 5: Review Judge dry-run and guarded apply

**Status**
- [ ] Completed

**Dependencies:** Task 1
**Parallelizable:** No (review safety first)

**Files:**
- Create: `backend/app/schemas/review_judge.py`
- Create: `backend/app/services/review_judge_prompt.py`
- Create: `scripts/run_review_judge_subagent.py`
- Test: `backend/tests/test_review_judge_subagent.py`
- Generate: `reports/review_judge_subagent_report.json`
- Generate: `reports/review_judge_subagent_report.md`
- Generate: `reports/ai_review_apply_report.json`
- Generate: `reports/ai_review_apply_report.md`

- [ ] Emit `reviewer_type = "ai_review_subagent"` only.
- [ ] Reject or keep pending badcase/forbidden/source-untraceable items.
- [ ] Keep `apply-with-human-override` disabled unless `--confirmed-by` is present.

### Task 6: DeepSeek smoke, ablation, and secret audit

**Status**
- [ ] Completed

**Dependencies:** Task 1, Task 5
**Parallelizable:** No (uses external provider and secret controls)

**Files:**
- Create: `scripts/eval_deepseek_provider_smoke.py`
- Create: `scripts/eval_deepseek_ablation.py`
- Test: `backend/tests/test_deepseek_provider_safety.py`
- Test: `backend/tests/test_secret_redaction.py`
- Generate: `reports/deepseek_provider_smoke_report.json`
- Generate: `reports/deepseek_provider_smoke_report.md`
- Generate: `reports/deepseek_ablation_report.json`
- Generate: `reports/deepseek_ablation_report.md`
- Generate: `reports/secret_redaction_audit_report.json`
- Generate: `reports/secret_redaction_audit_report.md`

- [ ] Call DeepSeek only through configured environment variables.
- [ ] Record configured/succeeded/failed/parse metrics without secrets.
- [ ] Confirm auto_accepted_count remains 0.
- [ ] Scan reports/docs/diffs for secret patterns and raw-key leakage.

### Task 7: Phase D reports and consistency

**Status**
- [ ] Completed

**Dependencies:** Task 3, Task 4, Task 6
**Parallelizable:** No (final Phase D evidence)

**Files:**
- Generate: `reports/phase_d_non_procurement_mapping_eval_report.json`
- Generate: `reports/phase_d_non_procurement_mapping_eval_report.md`
- Generate: `reports/phase_d_semantic_mapping_quality_report.json`
- Generate: `reports/phase_d_semantic_mapping_quality_report.md`
- Generate: `reports/phase_d_strict_validation_failure_analysis.json`
- Generate: `reports/phase_d_strict_validation_failure_analysis.md`
- Generate: `reports/phase_d_report_consistency.json`
- Generate: `reports/phase_d_report_consistency.md`

- [ ] Run non-procurement evaluator.
- [ ] Run semantic quality analysis scoped to the 50-doc Phase D report.
- [ ] Run strict validation analysis scoped to the same doc ids.
- [ ] Run report consistency gate.

### Task 8: Production shadow and blind-set scaffolding

**Status**
- [ ] Completed

**Dependencies:** Task 7
**Parallelizable:** No (must not tune on blind split)

**Files:**
- Create: `examples/production_shadow/manifest.json`
- Create: `scripts/eval_production_shadow_mapping.py`
- Generate: `reports/production_shadow_dataset_manifest.json`
- Generate: `reports/production_shadow_dataset_plan.md`
- Generate: `reports/production_shadow_eval_report.json`
- Generate: `reports/production_shadow_eval_report.md`
- Generate: `reports/blind_set_eval_report.json`
- Generate: `reports/blind_set_eval_report.md`

- [ ] Create warmup/blind split structure.
- [ ] If no real production UIRs exist, write a plan and do not claim blind 0.85.
- [ ] Produce blind-set report with honest status.

### Task 9: Handoff, verification, and commit

**Status**
- [ ] Completed

**Dependencies:** Task 8
**Parallelizable:** No (final aggregation)

**Files:**
- Create: `docs/phase_d_e_f_deepseek_review_subagent_handoff.md`

- [ ] Run unit tests for new services/scripts.
- [ ] Run `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- [ ] Confirm badcase violations = 0, llm_auto_accepted_count = 0, secret leaks = 0.
- [ ] Write handoff with exact achieved metrics and any remaining gaps.
- [ ] Commit only relevant tracked changes; leave user-local files untouched.

---

**Execution Mode:** serial
