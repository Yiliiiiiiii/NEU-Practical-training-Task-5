# Task 1: Measured Batch 1 Evaluators, Verification Runner, and CI

## Goal

Replace Batch 1 test-pass proxy metrics with declared case-level evaluators and add a cross-platform evidence runner/CI foundation. Stay strictly within Topic 5.

## Required deliverables

1. Create real evaluators and versioned fixtures for:
   - metadata template effectiveness and issue localization;
   - document-summary faithfulness, source coverage, and new-fact violations;
   - artifact consistency, Markdown block coverage, chunk/source coverage, tampering detection;
   - entity passthrough coverage and invented IDs;
   - Topic 11 fallback, invalid-output acceptance, secret leakage, and legacy compatibility.
2. Preferred paths:
   - `scripts/eval_topic5_metadata_contract.py`
   - `scripts/eval_topic5_summary_faithfulness.py`
   - `scripts/eval_topic5_artifact_consistency.py`
   - `scripts/eval_topic5_entity_passthrough.py`
   - `scripts/eval_topic5_topic11_adapter.py`
   - `eval/topic5_metadata_contract/v2/`
   - `eval/topic5_summary_faithfulness/v2/`
   - `eval/topic5_artifact_consistency/v2/`
   - `eval/topic5_entity_passthrough/v2/`
   - `eval/topic5_topic11_adapter/v2/`
3. Every evaluator report must contain `dataset_id`, `dataset_version`, `dataset_sha256`, `commit_sha`, `case_count`, `passed_count`, named metric values, failed cases, reproduction command, and claim boundary. Metrics must be calculated from cases, never from `pytest` module success.
4. Refactor `scripts/check_topic5_hard_gap_batch_1_gate.py` or add a Batch 2 metrics aggregation layer so the quantitative values come from evaluator reports. Remove any `1.0 if passed(...) else 0.0` proxy path for these metrics, and ensure skipped tests cannot be marked passed.
5. Create `scripts/run_topic5_batch_2_verification.py` that:
   - uses `sys.executable` and platform-neutral npm selection;
   - runs on Windows/Linux;
   - captures command, cwd, stdout, stderr, return code, duration, and tool versions;
   - records exact current commit SHA;
   - fails on a dirty tree unless `--allow-dirty`;
   - never marks a skipped mandatory command passed;
   - writes non-empty raw logs and an actual `verification_summary.json`;
   - exits nonzero when any mandatory command fails.
6. Update `.github/workflows/ci.yml` to run backend tests, Ruff, frontend tests, frontend build, OpenAPI drift check, SchemaPack contract gate, and Batch 2 acceptance gate on Windows and Linux where appropriate. No secrets or live LLM calls.
7. Add focused tests for evaluator case accounting/report metadata, proxy rejection, dirty-tree behavior, skipped-command behavior, non-empty logs, and CI command presence.

## Constraints

- Use TDD: add focused failing tests, run them and confirm expected failures, implement minimal behavior, rerun focused tests.
- Reuse existing fixture helpers and services; do not copy production algorithms into gold evaluators.
- Generated reports may go to temporary paths in tests.
- Preserve backward compatibility for existing evaluator imports where feasible.
- Do not edit the future immutable tag or mapping-v2 gold in this task.
- Do not touch user-owned untracked files under `docs/guildline` or existing `.tmp` entries outside `.tmp/topic5-batch2-sdd`.
- Current sandbox may reject Git index writes. Do not use workarounds. If commit is blocked, leave a cleanly scoped working-tree diff and report it.

## Verification

- Run the focused new test modules.
- Run all directly affected existing evaluator/gate tests.
- Run Ruff on changed Python files.
- Return status `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`; list changed files, exact commands/results, and any commit SHA or commit blocker.
