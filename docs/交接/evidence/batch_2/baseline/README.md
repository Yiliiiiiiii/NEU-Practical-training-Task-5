# Topic 5 Batch 2 Baseline

Reviewed head: `661ad4480cfe4aa4982def583c83770c1521707a`  
Target branch: `feat/topic5-batch-2-reliability`

The reviewed head has a clean tracked baseline: 1,036 backend tests and 24 frontend tests pass locally; Ruff, the frontend build, the committed OpenAPI schema comparison, and the current SchemaPack contract gate also pass. The existing Batch 1 gate reports `passed`, but its quantitative summary is not acceptable Batch 2 evidence because it converts component-test outcomes into rates and consumes a verification summary for an older commit.

All ten Batch 1 audit sections are confirmed. Section 4.2 has two narrower corrections: raw evidence files are currently non-empty, and the reviewed commit has two GitHub checks rather than none. The backend check failed and the workflow omits several required gates, so exact-head CI acceptance is still absent.

Files:

- `baseline_report.json` — machine-readable command results and environment.
- `commands.log` — non-empty command transcript captured from the baseline run.
- `batch_1_audit.json` — machine-readable file-level audit with claim boundaries.

No arbitrary-Schema or production-blind mapping claim is made by this baseline.
