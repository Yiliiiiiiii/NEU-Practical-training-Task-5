# SchemaPack Three-Track Deepening Implementation Plan

> **Historical plan:** Preserved as an execution record. Current status: [`../../project_status.md`](../../交接/project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the official real-world UIR dataset to at least 45 documents, raise non-procurement mapping recall to at least 0.55 without badcase regressions, and prove the governed Human Review → Knowledge Pack lifecycle with deterministic reports.

**Architecture:** Keep the production boundary `UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`. Extend the existing offline collector/builder, candidate and template rules, and persisted review/knowledge workflow; do not add OCR, RAG, training, or automatic LLM rule activation. Every production behavior change follows red-green-refactor and every metric comes from a fresh evaluator run.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, pytest, JSON/JSONL catalogs, PowerShell, TypeScript/Vite.

---

## File Map

- Modify `examples/real_world/sources/source_manifest.json`: add at least 15 traceable official-public non-procurement sources.
- Create `examples/real_world/uir/general/*.json`, `meeting/*.json`, and `policy/*.json`: generated strict UIR documents.
- Modify `examples/real_world/gold/mapping_gold.jsonl`: add one document-level gold row per new UIR.
- Modify `examples/real_world/gold/real_world_badcases.jsonl`: add document-linked non-procurement confusion cases.
- Modify `examples/real_world/gold/retrieval_queries.jsonl`: add at least one traceable query per new UIR.
- Modify `examples/real_world/review_fixtures/next_phase_review_decisions.jsonl`: cover approved, rejected, and blocked cases.
- Modify `backend/tests/test_real_world_uir_tools.py`: enforce 45-document distribution and cross-file traceability.
- Modify `backend/app/services/candidate_service.py`: only evidence-backed extraction gaps found after dataset expansion.
- Modify `examples/production_like/mapping_templates/{general,meeting,policy}_doc_base_v1.json`: low-risk aliases and explicit regexes.
- Modify `backend/app/services/mapping_service.py`: only if a demonstrated review/risk policy gap remains after extraction/template fixes.
- Modify `backend/app/services/review_knowledge_workflow_service.py`: block rejected/badcase candidates and preserve lifecycle invariants where current behavior is incomplete.
- Modify `scripts/eval_real_world_knowledge_loop.py` and `scripts/eval_review_knowledge_growth.py`: emit the required before/after and lifecycle fields.
- Modify focused tests under `backend/tests/` for each behavior change.
- Regenerate reports under `examples/real_world/reports/` and `reports/`.
- Update the delivery documents named in the execution guide.

### Task 1: Freeze Phase 0 Evidence

**Files:**
- Create `reports/baseline_before_deepening.json`
- Create `reports/baseline_before_deepening.md`

- [ ] Run `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`; require exit `0`.
- [ ] Start the API on `127.0.0.1:8000` in a hidden process and wait for `/health`.
- [ ] Run the real-world UIR, real-world mapping, and non-procurement evaluators exactly as listed in the execution guide.
- [ ] Build the JSON report from generated artifacts with these keys:

```json
{
  "dataset_size": 30,
  "import_pass_count": 30,
  "execution_pass_count": 30,
  "package_verify_pass_count": 30,
  "real_world_mapping_recall": 0.48847926267281105,
  "non_procurement_average_recall": 0.4211309523809524,
  "review_required_count": 149,
  "required_missing_count": 12,
  "badcase_violation_count": 0
}
```

- [ ] Render the same values to Markdown with command provenance and UTC generation time.
- [ ] Parse the JSON with `ConvertFrom-Json` and stop if generated evaluator values differ without being recorded.

### Task 2: Expand and Validate the Official Dataset

**Files:**
- Modify `examples/real_world/sources/source_manifest.json`
- Modify `backend/tests/test_real_world_uir_tools.py`
- Create generated UIR files under `examples/real_world/uir/`

- [ ] Add a failing dataset test requiring:

```python
assert len(items) >= 45
assert counts["general_doc"] >= 10
assert counts["meeting_doc"] >= 10
assert counts["policy_doc"] >= 15
assert counts["procurement_doc"] >= 10
```

- [ ] Run `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_real_world_uir_tools.py -q` and confirm failure on the 30-item dataset.
- [ ] Add at least 15 unique `planned` manifest items from official HTML or text-layer PDF sources. Each item must contain `source_id`, `doc_type`, `title`, `source_url`, `source_site`, `source_format`, `retrieval_method`, `status`, `license_note`, and `notes`.
- [ ] Run the collector for the new source IDs, then the UIR builder for the same IDs.
- [ ] Reject sources that return login/CAPTCHA pages, scanned/image-only PDFs, content-type mismatches, or empty extraction; replace them with compliant official sources.
- [ ] Run `backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py` and require all accepted documents to pass.
- [ ] Re-run the focused dataset test and require it to pass.

### Task 3: Add Gold, Badcases, Retrieval Queries, and Review Fixtures

**Files:**
- Modify `examples/real_world/gold/mapping_gold.jsonl`
- Modify `examples/real_world/gold/real_world_badcases.jsonl`
- Modify `examples/real_world/gold/retrieval_queries.jsonl`
- Modify `examples/real_world/review_fixtures/next_phase_review_decisions.jsonl`
- Modify `backend/tests/test_real_world_uir_tools.py`

- [ ] Add failing cross-file tests asserting every new `doc_id` has a gold row and retrieval query, every referenced block ID exists in the UIR, and all JSONL rows parse.
- [ ] Confirm the tests fail because the generated UIRs are not yet labeled.
- [ ] Add document-level gold rows using the existing evaluator contract (`expected_mappings` and `expected_review_required`) with real source paths and block IDs.
- [ ] Add non-procurement badcases for at least these forbidden pairs when present in source evidence:

```python
{
    ("联系人", "issuer"),
    ("发布日期", "effective_date"),
    ("标题年份", "publish_date"),
    ("办理地点", "department"),
    ("服务对象", "application_conditions"),
    ("发布时间", "meeting_date"),
    ("会议主题", "decisions"),
}
```

- [ ] Add at least one retrieval query per new document with non-empty `relevant_source_block_ids`.
- [ ] Add approved, rejected, and blocked review fixtures tied to real document evidence.
- [ ] Run the focused cross-file and badcase tests and require them to pass.

### Task 4: Improve Non-Procurement Mapping with TDD

**Files:**
- Modify `backend/tests/test_candidate_service_non_procurement.py`
- Modify `backend/tests/test_non_procurement_templates.py`
- Modify `backend/tests/test_mapping_service.py` or the closest existing focused mapping test
- Modify `backend/app/services/candidate_service.py`
- Modify the three non-procurement template JSON files
- Modify `backend/app/services/mapping_service.py` only if required

- [ ] Run the expanded non-procurement evaluator and gap analyzer to produce a fresh ranked gap list.
- [ ] For each selected high-frequency, low-risk gap, write one focused failing test using a real label/value/block shape from the expanded dataset.
- [ ] Confirm each test fails for the intended missing candidate, alias, regex, or review-policy behavior.
- [ ] Implement the smallest domain-scoped extraction or template rule; keep ambiguous/fuzzy candidates review-only.
- [ ] Add a paired badcase assertion proving the new rule cannot auto-accept the nearest dangerous source/target pair.
- [ ] Re-run focused tests after every rule group.
- [ ] Re-run the evaluator until either all targets are met or no further evidence-backed low-risk fix remains:

```text
average recall >= 0.55
review-required <= 120
required missing <= 6
badcase violations = 0
all packages verify
```

### Task 5: Complete the Review/Knowledge Lifecycle Contract with TDD

**Files:**
- Modify `backend/tests/test_review_knowledge_api.py`
- Modify `backend/tests/test_review_knowledge_growth.py`
- Modify `backend/tests/test_real_world_knowledge_loop.py`
- Modify `backend/app/services/review_knowledge_workflow_service.py`
- Modify `scripts/eval_real_world_knowledge_loop.py`
- Modify `scripts/eval_review_knowledge_growth.py`

- [ ] Add failing tests named for the required invariants:

```python
test_review_generates_candidates
test_approved_candidate_can_enter_draft_pack
test_rejected_candidate_never_activates
test_badcase_candidate_blocked_before_activation
test_draft_pack_does_not_affect_effective_template
test_active_pack_affects_future_task
test_old_task_snapshot_unchanged_after_pack_activation
test_effective_template_resolution_is_deterministic
test_knowledge_metrics_report_counts
```

- [ ] Confirm failures are caused by missing lifecycle guards or report fields, not test setup.
- [ ] Prevent rejected or blocked candidates from entering pack items and prevent packs containing invalid items from activation.
- [ ] Keep draft packs excluded from effective template resolution and active packs scoped to future task resolution.
- [ ] Extend both evaluators to report:

```json
{
  "before_mapping_counts": {},
  "after_mapping_counts": {},
  "review_required_before": 0,
  "review_required_after": 0,
  "activated_aliases": [],
  "rejected_candidates_count": 0,
  "badcase_blocked_count": 0,
  "draft_pack_no_effect": true,
  "active_pack_effect": true,
  "old_snapshot_unchanged": true,
  "badcase_violations": 0
}
```

- [ ] Run all three focused test files and both evaluators; require lifecycle booleans to be true and violations to be zero.

### Task 6: Regenerate Reports and Documentation

**Files:**
- Regenerate all report pairs listed in the execution guide.
- Modify `README.md`
- Modify `docs/real_world_uir_dataset.md`
- Modify `docs/non_procurement_mapping_improvement_plan.md`
- Modify `docs/real_world_knowledge_loop.md`
- Modify `docs/交接/badcase_analysis.md`
- Modify `docs/交接/requirement_mapping.md`
- Modify `docs/交接/final_handoff_status.md`
- Modify `docs/交接/final_demo_script.md`
- Create or modify `reports/non_procurement_acceptance_report.md`

- [ ] Derive every stated metric from the fresh JSON reports.
- [ ] State unmet thresholds explicitly and list remaining per-field gaps.
- [ ] Preserve the distinction between package verification, field semantics, strict validation, deterministic retrieval evidence, and full RAG.
- [ ] State that OCR, model training, automatic LLM activation, and enterprise multi-tenancy/SSO are not implemented.

### Task 7: Full Acceptance Verification

**Files:**
- No manual production changes.

- [ ] Run `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- [ ] Start a fresh backend and run all real-world UIR/mapping/non-procurement evaluators.
- [ ] Run the non-procurement gap analyzer.
- [ ] Run both knowledge-loop evaluators.
- [ ] Run `scripts/eval_content_organization_retrieval.py`.
- [ ] Run `scripts/verify_downstream_contract.py` against `reports/real_world_packages`.
- [ ] Read every exit code and fresh report summary before claiming completion.
- [ ] Compare the final result line-by-line with the Definition of Done in `docs/guildline/SchemaPack_Agent_三项深化执行文档.md`.
