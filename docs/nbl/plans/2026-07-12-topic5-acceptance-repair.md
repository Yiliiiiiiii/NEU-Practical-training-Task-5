# Topic 5 Acceptance Repair Implementation Plan

> **For agentic workers:** Execute serially in the current isolated worktree. Subagents are explicitly disabled by user instruction.

**Goal:** Restore clean-checkout reproducibility and close the remaining Topic 5 acceptance evidence gaps.

**Architecture:** Preserve the existing conversion engine and evaluator boundaries. Repair repository normalization, make verification failure-tolerant, strengthen only the missing assignment gates, then regenerate exact-head evidence and documentation.

**Tech Stack:** Python 3.13, FastAPI/Pydantic, pytest, JSON evaluators, GitHub Actions, Markdown.

---

### Task 1: Cross-platform frozen assets

**Dependencies:** None
**Parallelizable:** No (establishes the reproducible baseline)

**Files:** `.gitattributes`, frozen mapping/replay assets, clean-checkout tests.

- [ ] Add LF attributes for frozen text/JSON/JSONL/YAML assets.
- [ ] Add a test that checks Git-blob and worktree hash behavior independent of CRLF conversion.
- [ ] Refresh only stale replay/hash artifacts from their builders.
- [ ] Run the seven previously failing backend tests and require all to pass.

### Task 2: Verification failure reporting

**Dependencies:** Task 1
**Parallelizable:** No (uses the repaired baseline)

**Files:** `scripts/run_topic5_batch_2_verification.py`, `backend/tests/test_topic5_batch_2_verification_runner.py`.

- [ ] Add a failing-command regression test where `final_gate.json` is absent.
- [ ] Make the runner preserve the command failure, synthesize a failed final-gate result, and always write the summary.
- [ ] Verify the focused runner tests.

### Task 3: Assignment-aligned tag gate

**Dependencies:** Task 1
**Parallelizable:** No (changes frozen acceptance evidence)

**Files:** tag evaluator, final gate, tag gold/evidence, evaluator tests.

- [ ] Add content label accuracy and explicit management scope/trace/unknown-tag metrics.
- [ ] Add failing tests for accuracy below 0.85 and tag-governance regressions.
- [ ] Update the gate and refresh evaluator evidence.
- [ ] Verify focused tag and final-gate tests.

### Task 4: LLM difficult-mapping evidence

**Dependencies:** Task 1
**Parallelizable:** No (must use stable mapping fixtures)

**Files:** new evaluator/fixture or existing LLM evaluator, gate, tests, evidence report.

- [ ] Add deterministic ambiguous mapping cases that require the LLM fallback path.
- [ ] Measure suggestion coverage, confidence bounds, evidence presence, and review-only enforcement.
- [ ] Add the report to the verification runner and final gate.
- [ ] Verify focused LLM evaluator tests.

### Task 5: Exact-head documentation

**Dependencies:** Tasks 2, 3, 4
**Parallelizable:** No (documents measured results)

**Files:** status generator, handoff status, requirement mapping, capability matrix, README references.

- [ ] Add the required missing report reference.
- [ ] Add a per-capability implementation/data/performance/cost matrix.
- [ ] Regenerate status from exact-head evidence and remove stale claims.
- [ ] Run documentation consistency tests.

### Task 6: Full verification

**Dependencies:** Tasks 1-5
**Parallelizable:** No (final integration gate)

- [ ] Run backend tests, Ruff, frontend tests/build, OpenAPI drift, SchemaPack gate, all Topic 5 evaluators, and final gate.
- [ ] Repeat from a clean temporary clone with simulated GitHub Actions environment.
- [ ] Confirm the original `main` worktree and user-owned untracked files are unchanged.

---

**Execution Mode:** serial in the main agent, overriding the skill's subagent recommendation because the user explicitly prohibited subagents.
