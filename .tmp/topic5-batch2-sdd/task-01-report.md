# Task 01 Report — Measured Batch 1 Evidence and Batch 2 Verification

Status: **DONE_WITH_CONCERNS**

Branch: `feat/topic5-batch-2-reliability`  
Current base commit: `661ad4480cfe4aa4982def583c83770c1521707a`

## Outcome

- Added five production-service-backed, case-level Topic 5 evaluators and versioned `v2` fixtures (20 declared cases total).
- Added the required report metadata/accounting fields and named metrics; values are calculated from cases, not pytest module status.
- Refactored the Batch 1 hard-gap gate to require evaluator reports for the affected metrics. Component pytest results remain diagnostic only; skipped components are recorded as `passed: false`.
- Added a Batch 2 evaluator-report acceptance gate.
- Added a cross-platform verification runner with clean-tree enforcement, `sys.executable`, platform-neutral npm selection, raw logs, command evidence, tool versions, exact commit SHA, and a real `verification_summary.json`.
- Added non-mutating OpenAPI drift checking (`export_openapi.py --check`).
- Updated CI to execute the verification runner on `windows-latest` and `ubuntu-latest`, without secrets or live LLM calls.

## RED evidence

1. Initial evaluator/runner contract RED:

   ```text
   backend\.venv\Scripts\python.exe -m pytest \
     backend/tests/test_topic5_batch_2_evaluator_reports.py \
     backend/tests/test_topic5_batch_2_verification_runner.py \
     -q -p no:cacheprovider \
     --basetemp .tmp/topic5-batch2-sdd/pytest-task1-red
   ```

   Result: exit `1`, `11 failed`; each failure identified a missing evaluator or missing verification runner.

2. Gate proxy rejection RED:

   ```text
   backend\.venv\Scripts\python.exe -m pytest \
     backend/tests/test_topic5_batch_2_evaluator_reports.py::test_gate_uses_evaluator_reports_and_rejects_component_proxies \
     -q -p no:cacheprovider \
     --basetemp .tmp/topic5-batch2-sdd/pytest-task1-gate-red
   ```

   Result: exit `1`, `TypeError: evaluate_gate() got an unexpected keyword argument 'evaluator_reports'`.

3. OpenAPI drift RED:

   ```text
   backend\.venv\Scripts\python.exe -m pytest \
     backend/tests/test_openapi_export.py::test_openapi_check_detects_drift_without_rewriting_expected_file \
     -q -p no:cacheprovider \
     --basetemp .tmp/topic5-batch2-sdd/pytest-task1-openapi-red
   ```

   Result: exit `1`, missing `check_openapi_drift`.

4. Batch 2 acceptance gate RED:

   ```text
   backend\.venv\Scripts\python.exe -m pytest \
     backend/tests/test_topic5_batch_2_evaluator_reports.py::test_batch_2_acceptance_gate_fails_a_mutated_case_metric \
     -q -p no:cacheprovider \
     --basetemp .tmp/topic5-batch2-sdd/pytest-task1-acceptance-red
   ```

   Result: exit `1`, missing `scripts/check_topic5_batch_2_acceptance_gate.py`.

5. CI contract RED:

   ```text
   backend\.venv\Scripts\python.exe -m pytest \
     backend/tests/test_topic5_batch_2_ci.py \
     -q -p no:cacheprovider \
     --basetemp .tmp/topic5-batch2-sdd/pytest-task1-ci-red
   ```

   Result: exit `1`; the previous workflow had no OS matrix.

## GREEN and verification evidence

- Evaluator report contract: `6 passed in 0.74s`.
- Verification runner focused tests: `5 passed in 0.16s`.
- Proxy rejection gate test: `1 passed in 0.71s`.
- Existing hard-gap evaluator/gate tests: `5 passed in 1.12s`.
- OpenAPI export/drift tests: `2 passed in 2.28s`.
- Batch 2 acceptance mutation test: `1 passed in 0.72s`.
- CI command/matrix contract test: `1 passed in 0.05s`.
- Fresh directly affected test set:

  ```text
  backend\.venv\Scripts\python.exe -m pytest \
    backend/tests/test_topic5_batch_2_evaluator_reports.py \
    backend/tests/test_topic5_batch_2_verification_runner.py \
    backend/tests/test_topic5_batch_2_ci.py \
    backend/tests/test_topic5_hard_gap_evaluators.py \
    backend/tests/test_openapi_export.py \
    backend/tests/test_metadata_template_service.py \
    backend/tests/test_document_summary_service.py \
    backend/tests/test_artifact_consistency_service.py \
    backend/tests/test_topic5_entity_passthrough.py \
    backend/tests/test_topic11_chunk_provider.py \
    -q -p no:cacheprovider \
    --basetemp .tmp/topic5-batch2-sdd/pytest-task1-final-fresh
  ```

  Result: exit `0`, **80 passed in 6.44s**.

- Changed-Python Ruff:

  ```text
  backend\.venv\Scripts\python.exe -m ruff check \
    scripts/topic5_eval_common.py \
    scripts/eval_topic5_metadata_contract.py \
    scripts/eval_topic5_summary_faithfulness.py \
    scripts/eval_topic5_artifact_consistency.py \
    scripts/eval_topic5_entity_passthrough.py \
    scripts/eval_topic5_topic11_adapter.py \
    scripts/check_topic5_hard_gap_batch_1_gate.py \
    scripts/check_topic5_batch_2_acceptance_gate.py \
    scripts/run_topic5_batch_2_verification.py \
    scripts/export_openapi.py \
    backend/tests/test_topic5_batch_2_evaluator_reports.py \
    backend/tests/test_topic5_batch_2_verification_runner.py \
    backend/tests/test_topic5_batch_2_ci.py \
    backend/tests/test_topic5_hard_gap_evaluators.py \
    backend/tests/test_openapi_export.py
  ```

  Result: exit `0`, `All checks passed!`.

- Five evaluator CLI smokes wrote non-empty reports under `.tmp/topic5-batch2-sdd/smoke-reports`; all exited `0`.
- Batch 2 acceptance gate consumed those reports and exited `0`.
- `python scripts/export_openapi.py --check` exited `0`: committed OpenAPI is current.
- SchemaPack contract gate exited `0` with all eight checks passed; it reported six existing non-blocking schema-precision warnings.
- Dirty-tree CLI smoke correctly refused to run without `--allow-dirty` and printed `git working tree is dirty; rerun with --allow-dirty to override`.
- `git diff --check` exited `0` (Git printed only LF/CRLF conversion warnings).
- `rg` found no `1.0 if passed`, `0 if passed`, or `passed(` proxy expression in `scripts/check_topic5_hard_gap_batch_1_gate.py`.

## Changed files

### Evaluators and fixtures

- `scripts/topic5_eval_common.py`
- `scripts/eval_topic5_metadata_contract.py`
- `scripts/eval_topic5_summary_faithfulness.py`
- `scripts/eval_topic5_artifact_consistency.py`
- `scripts/eval_topic5_entity_passthrough.py`
- `scripts/eval_topic5_topic11_adapter.py`
- `eval/topic5_metadata_contract/v2/cases.json`
- `eval/topic5_summary_faithfulness/v2/cases.json`
- `eval/topic5_artifact_consistency/v2/cases.json`
- `eval/topic5_entity_passthrough/v2/cases.json`
- `eval/topic5_topic11_adapter/v2/cases.json`

### Gates, runner, OpenAPI, and CI

- `scripts/check_topic5_hard_gap_batch_1_gate.py`
- `scripts/check_topic5_batch_2_acceptance_gate.py`
- `scripts/run_topic5_batch_2_verification.py`
- `scripts/export_openapi.py`
- `.github/workflows/ci.yml`

### Tests

- `backend/tests/test_topic5_batch_2_evaluator_reports.py`
- `backend/tests/test_topic5_batch_2_verification_runner.py`
- `backend/tests/test_topic5_batch_2_ci.py`
- `backend/tests/test_topic5_hard_gap_evaluators.py`
- `backend/tests/test_openapi_export.py`

No files under `docs/guildline` or other user-owned untracked paths were read, edited, staged, or removed.

## Risks / concerns

- The complete runner was not executed with `--allow-dirty`, because the task explicitly requires a clean tree by default and the shared workspace contains expected untracked/user files. Its command execution, log, skip, summary, dirty-tree, and platform behavior are covered by focused tests; the evaluator/acceptance/OpenAPI/SchemaPack commands were smoked independently.
- GitHub-hosted Windows/Linux jobs were not available locally; the workflow contract is tested, and CI uses only offline fixtures/mocks.
- The v2 evaluator datasets are deliberately focused (20 total declared cases). Their claim boundaries explicitly avoid extrapolating to semantic extraction, live Topic 11 availability, or cryptographic authenticity.
- The SchemaPack gate's six precision warnings pre-existed and remain non-blocking.

## Commit result

Scoped staging was attempted with only the Task 1 files. It failed exactly as follows:

```text
fatal: Unable to create 'F:/p2/.git/index.lock': Permission denied
```

No workaround was used, no files were staged, and no commit was created. The blocker is the sandbox's read-only `.git` index. The cleanly scoped working-tree diff is ready for the parent agent to stage/commit outside this restriction.

## Review-fix evidence (2026-07-10)

The three verified review findings were fixed with separate RED/GREEN cycles:

1. SchemaPack fail-closed runner command:

   - RED: `test_schemapack_gate_is_configured_to_fail_on_gate` failed because the command did not contain `--fail-on-gate` (`1 failed`).
   - GREEN: the same focused test passed after adding the flag (`1 passed`).
   - Real command smoke: `backend\.venv\Scripts\python.exe scripts/check_schema_pack_contract_gate.py --fail-on-gate` exited `0`; all eight checks passed. The six existing schema-precision warnings remained non-blocking.

2. Mandatory root-level Ruff coverage:

   - RED: `test_ci_lints_topic5_task_scripts_explicitly_from_repo_root` failed with `StopIteration` because `ruff-topic5-scripts` did not exist (`1 failed`).
   - GREEN: the same focused test passed after adding a mandatory ROOT-cwd command with an explicit Task 1 script list (`1 passed`). The list does not lint `.` or the complete legacy `scripts` directory.
   - `ruff_clean` now requires both backend Ruff and `ruff-topic5-scripts`; `ruff_topic5_scripts_clean` is also recorded separately.

3. Recomputed evaluator-report integrity:

   - RED: 15 parameterized mutations of dataset identity/version/SHA/commit, case accounting, `cases`, `failed_cases`, reproduction command, claim boundary, and representative metrics from all five evaluators were all accepted by the previous validator (`15 failed`, all `DID NOT RAISE`).
   - GREEN: `_validated_evaluator_reports` now reruns each registered `EVALUATOR_BUILDERS` builder and compares every builder-produced field except `generated_at` using type-sensitive JSON values (`16 passed`, including the `generated_at` exception test).
   - Existing gate mutation tests now require rejection with `ValueError` instead of treating forged metrics as ordinary threshold failures.

Focused review regression:

```text
backend\.venv\Scripts\python.exe -m pytest \
  backend/tests/test_topic5_batch_2_evaluator_reports.py \
  backend/tests/test_topic5_batch_2_verification_runner.py \
  backend/tests/test_topic5_batch_2_ci.py \
  backend/tests/test_topic5_hard_gap_evaluators.py \
  -q -p no:cacheprovider \
  --basetemp .tmp/topic5-batch2-sdd/pytest-task1-review-focused
```

Result: exit `0`, **37 passed in 8.89s**.

Final directly affected test set: exit `0`, **98 passed in 13.02s**.

Changed-file Ruff (the Task 1 evaluator/gate/runner/OpenAPI scripts and focused tests): exit `0`, `All checks passed!`.

`git diff --check`: exit `0` with only line-ending conversion warnings.

### Review-fix commit result

The earlier index-lock blocker no longer applied. A scoped commit containing only the 21 Task 1 CI/test/fixture/script files succeeded:

```text
6c129f81 fix: replace batch1 proxy metrics with dataset evaluators
```

The unrelated global-assignment report modifications, `docs/guildline`, `.tmp`, and the user PDF remained unstaged and were not committed.
