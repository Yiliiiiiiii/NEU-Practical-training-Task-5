# Task 7: Freeze Independent Tag Gold and Mapping v2 Benchmark

This task is dataset/evaluator/baseline only. Do not change mapping or tag production logic.

## Tag quality v2

- Create immutable `eval/topic5_tag_quality/v2/` with a dataset card, source UIR references/snapshots, independently frozen labels, manifest, dataset SHA, and baseline report.
- Separate content-tag semantic precision/recall/F1 from management and quality deterministic `rule_correctness`, `trace_correctness`, and `scope_correctness`; do not present deterministic rule output as independent semantic F1.
- Add a v2 evaluator and tests for schema, determinism, hashing, category separation, unknown tags, invalid references, and frozen-file drift.
- Do not modify v2 after its baseline commit; corrections require v3.

## Mapping v2

- Create the exact `eval/topic5_mapping_v2/` structure required by spec sections 5.2-5.4.
- Minimum 90 documents, at least 6 schema families, at least 15 documents per family, at least 300 positive mappings, and at least 80 explicit negative/no-match decisions.
- Include the required linguistic/layout/semantic variety. Exact-name positives must be <=25%; at least 30% of test sources held out by source/organization or layout pattern; include a schema-held-out test subset.
- Primary cases must not leak target IDs through `attributes.field_name`, candidate hints, doc IDs, or copied gold labels. Add an executable leakage audit and tests.
- Provide `scripts/eval_topic5_mapping_v2.py` with `--split dev|test`, automatic-only metric definitions from the spec, per-schema macro metrics, dataset IDs/versions/SHA, deterministic reports, external blind status `not_run`, and nonzero exit on invalid dataset.
- Provide a platform-neutral external blind runner/manifest that remains `not_run` without independent annotations.
- Store current-engine dev/test baseline reports without changing engine behavior or acceptance thresholds.
- Calculate and freeze hashes for UIR, schemas, rules, gold, and split files. Add a check/gate that detects post-freeze drift.

## Process and verification

- Use TDD for dataset validation, leakage, metrics, split constraints, hashes, determinism, and CLI failure behavior.
- Generate dataset content through a reviewed deterministic builder if useful, but committed gold must be standalone and the evaluator must never derive gold from predictions.
- Prefer two commits: `test: freeze topic5 tag quality v2 gold` and `test: freeze topic5 mapping v2 benchmark and baseline`. Never squash these with later mapping-engine changes.
- Report to `.tmp/topic5-batch2-sdd/task-07-report.md` and never stage `.tmp` or user files.
- Run new evaluator/tests, existing tag/mapping gates, Ruff, and `git diff --check`.
