# Phase 10 Acceptance Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the acceptance-ready verifier, replay, evaluation, LLM fallback, content organization, and delivery evidence baseline for SchemaPack Agent.

**Architecture:** Add pure verifier/evaluation modules and keep business orchestration in services. Mapping fallback remains opt-in and auditable. Package completion uses the independent verifier contract before publishing.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, httpx, pytest, pytest-cov, React/Vitest existing gates.

---

### Task 1: External Package Verifier

**Files:**
- Create: `backend/app/verifiers/package_verifier.py`
- Create: `backend/app/tools/package_verifier.py`
- Modify: `backend/app/services/package_service.py`
- Test: `backend/tests/test_phase10_package_verifier.py`

- [ ] Write failing tests for accepting a valid generated ZIP and rejecting unsafe paths, extra entries, manifest self-reference, missing entries, byte mismatch, SHA mismatch, invalid JSON, and JSON payloads above the configured byte limit.
- [ ] Implement `verify_package_zip(zip_path: Path, max_json_bytes: int = 5_000_000) -> PackageVerifierReport`.
- [ ] Replace `PackageService._verify_zip_payload` use with the external verifier module and save `tasks/{task_id}/package_verifier_report.json` outside the ZIP.
- [ ] Add CLI entrypoint `python -m app.tools.package_verifier <zip>` returning JSON and non-zero exit on failure.
- [ ] Run verifier tests and commit.

### Task 2: LLM Fallback

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/clients/llm_client.py`
- Modify: `backend/app/services/mapping_service.py`
- Modify: `backend/app/api/v1/mappings.py`
- Test: `backend/tests/test_phase10_llm_fallback.py`

- [ ] Write failing tests for disabled mode, mock mode, openai-compatible HTTP parsing, failed HTTP degradation, and mapping report audit fields.
- [ ] Add settings for base URL, API key, model, prompt version, and timeout.
- [ ] Implement `LLMClient.from_settings()` and keep `suggest_mappings()` backward compatible for existing tests.
- [ ] Convert suggestions into review-required `llm_fallback` mappings only for unmapped targets and unused candidates.
- [ ] Record model, prompt version, latency, suggestion count, failure reason, and `llm_enabled` in mapping reports.
- [ ] Run mapping/LLM tests and commit.

### Task 3: Replay And Config Snapshot

**Files:**
- Modify: `backend/app/schemas/api.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/services/package_service.py`
- Test: `backend/tests/test_phase10_replay_snapshot.py`

- [ ] Write failing tests for replaying a completed parent, rejecting missing mappings, preserving `parent_task_id`, copying candidates/mappings with new IDs, and not calling LLM by default.
- [ ] Add `TaskReplayRequest` and `TaskReplayResponse`.
- [ ] Implement `TaskService.replay_task()`.
- [ ] Add `POST /api/v1/tasks/{task_id}/replay`.
- [ ] Expand `config_snapshot.json` to include `snapshot_version`, parent task, schema/template refs, confirmed mapping IDs, model audit, prompt version, and created time while preserving legacy fields.
- [ ] Run replay/snapshot tests and commit.

### Task 4: Frozen Evaluation Runner

**Files:**
- Create: `examples/eval/eval_cases.json`
- Create: `examples/eval/README.md`
- Create: `backend/app/evaluation/mapping_evaluator.py`
- Create: `backend/app/tools/evaluate_mappings.py`
- Test: `backend/tests/test_phase10_evaluation.py`

- [ ] Write failing tests for duplicate gold rejection, precision/recall/F1 math, confidence bucket accuracy, and fixture size requirements.
- [ ] Add a frozen fixture with 30 cases and 150 gold mappings across general, policy, and table-like records.
- [ ] Implement the evaluator using `MappingEngine` and the frozen fixture.
- [ ] Add CLI `python -m app.tools.evaluate_mappings examples/eval/eval_cases.json --json-out docs/reports/evaluation_report.json --md-out docs/reports/evaluation_report.md`.
- [ ] Run evaluator tests and commit.

### Task 5: Content Organization And Consumer Smoke

**Files:**
- Modify: `backend/app/schemas/content.py`
- Modify: `backend/app/renderers/json_renderer.py`
- Modify: `backend/app/engines/chunk_engine.py`
- Create: `backend/app/tools/consume_package.py`
- Test: `backend/tests/test_phase10_content_consumer.py`

- [ ] Write failing tests that rendered content has summary, keywords, three label tiers, upstream entities, chunk summaries, chunk keywords, and non-empty labels.
- [ ] Implement deterministic local heuristics for labels and entity tags.
- [ ] Add consumer CLI that reads a package ZIP and prints content field count, chunk count, and source block coverage.
- [ ] Run content and consumer tests and commit.

### Task 6: API Contract, Docs, Reports, And Final Gates

**Files:**
- Modify: `backend/tests/test_api_contract_matrix.py`
- Modify: `README.md`
- Create: `docs/api_contract.md`
- Create: `docs/package_protocol.md`
- Create: `docs/deployment.md`
- Create: `docs/reports/badcase_report.md`
- Create: `docs/reports/technical_report.md`
- Create: `scripts/demo.ps1`
- Generate: `docs/openapi.json`

- [ ] Update the API route inventory for replay and package verifier report.
- [ ] Generate frozen OpenAPI JSON from `app.main:create_app`.
- [ ] Write delivery documents with exact commands and acceptance evidence boundaries.
- [ ] Run backend coverage gate, ruff, frontend coverage/lint/build, package verifier CLI, evaluation CLI, consumer CLI, and three-run stability smoke.
- [ ] Commit final docs and report.
