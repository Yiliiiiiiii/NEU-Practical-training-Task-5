# Project Docs Chinese Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert current project-facing documentation copy to Chinese while preserving professional terms, commands, paths, metrics, API names, and generated-data identifiers.

**Architecture:** Update manually maintained public/hand-off documentation first. Keep historical guideline/spec/plan archives and generated reports out of this batch unless they are current acceptance evidence.

**Tech Stack:** Markdown documentation.

---

### Task 1: Localize public entry documents

**状态**
- [ ] 任务完成

**Dependencies:** None
**Parallelizable:** No

**Files:**
- Modify: `README.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/deployment.md`
- Modify: `docs/demo_workflow.md`
- Modify: `docs/final_demo_script.md`

- [ ] Translate ordinary prose into Chinese.
- [ ] Preserve commands, paths, endpoint names, and professional terms.

### Task 2: Localize handoff and requirement documents

**状态**
- [ ] 任务完成

**Dependencies:** Task 1
**Parallelizable:** No

**Files:**
- Modify: `docs/final_handoff_status.md`
- Modify: `docs/requirement_mapping.md`
- Modify: `docs/package_spec.md`
- Modify: `docs/real_world_uir_dataset.md`
- Modify: `docs/badcase_analysis.md`

- [ ] Translate review-facing explanations and status notes.
- [ ] Keep metric values and evidence links unchanged.

### Task 3: Localize current non-procurement evidence docs

**状态**
- [ ] 任务完成

**Dependencies:** Task 2
**Parallelizable:** No

**Files:**
- Modify: `docs/non_procurement_mapping_improvement_plan.md`
- Modify: `reports/non_procurement_acceptance_report.md`
- Modify: `reports/non_procurement_schema_adjustments.md`

- [ ] Translate acceptance language honestly.
- [ ] Keep failed/open gates explicit.

### Task 4: Verify

**状态**
- [ ] 任务完成

**Dependencies:** Task 3
**Parallelizable:** No

**Files:**
- Test: modified Markdown files

- [ ] Run `git diff --check`.
- [ ] Scan modified docs for obvious English ordinary-language headings that should have been translated.

---

**Execution Mode:** inline
