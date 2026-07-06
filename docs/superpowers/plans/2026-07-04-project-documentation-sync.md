# Project Documentation Sync Implementation Plan

> **Execution record:** The synchronized result is summarized in [`../../project_status.md`](../../交接/project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize all project documentation with the verified implementation while preserving historical requirements and generated evaluation evidence.

**Architecture:** Treat code, OpenAPI, catalogs, current reports, and fresh verification output as sources of truth. Update living documentation directly, add implementation-status notices to historical specifications and plans, and leave generated report metrics unchanged unless their generators are rerun.

**Tech Stack:** Markdown, PowerShell, Python JSON inspection, pytest, Ruff, Vitest, Vite, OpenAPI.

---

### Task 1: Build The Documentation Truth Matrix

**Files:**
- Inspect: `README.md`
- Inspect: `docs/**/*.md`
- Inspect: `reports/**/*.md`
- Inspect: `examples/**/README.md`
- Inspect: `sdk/python/README.md`
- Inspect: `templates/adapter_plugin/README.md`

- [x] Inventory all Markdown files and classify them as living guides, historical plans/specifications, or generated reports.
- [x] Read verified facts from `docs/openapi.json`, current catalogs, evaluation metrics, and fresh test output.
- [x] Scan for stale test counts, obsolete capability gaps, invalid endpoint statements, and missing local links.

### Task 2: Synchronize Living Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/交接/acceptance_report.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/demo_workflow.md`
- Modify: `docs/deployment.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/external_uir_integration.md`
- Modify: `docs/交接/final_demo_script.md`
- Modify: `docs/交接/final_handoff_status.md`
- Modify: `docs/openapi_workflow.md`
- Modify: `docs/交接/requirement_mapping.md`
- Modify: `docs/user_web_workbench_guide.md`
- Review and update other living documents only where the audit finds a factual mismatch.

- [x] Replace obsolete baselines with 491 backend tests, 15 frontend tests, Ruff clean, frontend build success, and 58 OpenAPI paths.
- [x] Describe Phases 1-8 as implemented, with webhook explicitly recorded as the optional Phase 7 item not implemented.
- [x] Align External UIR, draft governance, review workbench, evaluation center, downstream contracts, CLI/SDK/scaffold, and optional raw upstream instructions with actual commands and boundaries.
- [x] Keep raw documents offline and optional; keep OCR outside the project runtime.

### Task 3: Mark Historical Documents Without Rewriting History

**Files:**
- Modify where needed: `docs/guildline/*.md`
- Modify where needed: `docs/nbl/{plans,specs}/*.md`
- Modify where needed: `docs/superpowers/{plans,specs}/*.md`

- [x] Add a short status notice to historical documents that contain now-obsolete “current state” claims.
- [x] Link status notices to `README.md` and `docs/交接/final_handoff_status.md`.
- [x] Preserve original requirements, proposed APIs, acceptance targets, and unchecked implementation checklists as historical records.

### Task 4: Validate Generated Reports And Auxiliary READMEs

**Files:**
- Review: `reports/*.md`
- Review: `examples/**/*.md`
- Review: `sdk/python/README.md`
- Review: `templates/adapter_plugin/README.md`

- [x] Confirm generated Markdown reports agree with their JSON counterparts and do not rewrite historical metrics.
- [x] Update SDK, adapter scaffold, and example READMEs for actual paths and safety boundaries.
- [x] Validate all relative Markdown links and referenced repository files.

### Task 5: Verify The Synchronized Repository

**Files:**
- Verify: all changed Markdown files

- [x] Run stale-claim scans and ensure obsolete statements remain only inside clearly marked historical documents.
- [x] Run a local Markdown-link and referenced-path audit.
- [x] Run `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`.
- [x] Run `npm.cmd test` in `frontend`.
- [x] Run regression gates and report the final synchronized baseline.
