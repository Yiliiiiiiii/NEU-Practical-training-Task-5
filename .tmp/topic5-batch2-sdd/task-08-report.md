# Task 8 Report: Mapping Engine v2, Calibration, and Gate

## Engine commit

- Constrained engine commit: `e2101d0d0cc95235585fc7c2fdd25a0767e19234`.
- Replaced the score-sorted greedy loop with deterministic maximum-weight bipartite assignment using explicit per-target dummy abstention nodes.
- Blocked edges are excluded from assignment and cannot hide a valid alternative.
- Stable sorting/tie behavior is independent of candidate input order and dictionary iteration order.
- Source reuse and non-one-to-one operations require explicit strict constraint rules.

## Generic mapping contract

- Generic target and candidate descriptors cover aliases, descriptions, types, enums, formats, parent paths, value shape, section path, block type, neighboring labels, evidence type, and source metadata.
- Scoring weights and evidence priorities are strict MappingTemplate configuration. Unknown evidence is neutral by default or rejected in strict mode.
- Generic candidate extraction now covers Chinese/English labels in paragraph, key-value, and text-table blocks without target-ID hints or document-family constants.
- Review decisions retain calibrated confidence, raw feature trace, score margin, alternatives, negative-pair check, risk flags, review reason, and source backlinks.
- LLM fallback remains disabled in the benchmark and excluded from automatic metrics.

## Dev-only calibration freeze

- Method: deterministic monotonic bins.
- Fit engine commit: `e2101d0d0cc95235585fc7c2fdd25a0767e19234`.
- Frozen dataset SHA: `2e527fb7127e26eb8fbe7f8c579620501624d7922cc8413ed3d424d0d29e8805`.
- Dev gold SHA: `31b14d7ea4fcb7c640219de5e743c58f2dd273e48b55b813c5e8a6bf49d959e8`.
- Fit samples: 270 selected dev decisions; 263 correct and 7 incorrect.
- Test labels used for fit: false. Full-dataset hashes may be validated, but only dev decisions select bins and thresholds.
- Frozen thresholds: auto-accept `1.0`; review-required `0.5`.
- Dev Brier score `0.0`; expected calibration error `0.0` on the public dev fit sample. This is a public-fixture result, not a production-blind calibration claim.

## Public reproducible metrics

- Dev: exact `0.9924528302`, precision `1.0`, recall `0.9924528302`, F1 `0.9962121212`, macro Schema F1 `0.9961904762`, required recall `0.9944444444`.
- Test: exact `0.9962825279`, precision `1.0`, recall `0.9962825279`, F1 `0.9981378026`, macro Schema F1 `0.9976525822`, required recall `1.0`.
- Schema-held-out test F1: `1.0`; test-vs-dev F1 gap: `-0.0019256814`.
- Review-required rate `0.0`; negative-pair, duplicate-source, and invalid-cardinality violations are all `0`.
- External blind status remains `not_run`; production-blind 0.85 cannot be claimed.

## Verification

- 186 related mapping/candidate/SchemaPack regressions passed in the broad Task 8 run.
- Final focused engine/evaluator/gate run: 46 passed.
- Backend Ruff: clean. Changed Task 8 scripts/tests Ruff: clean. `git diff --check`: clean.
- Gate status: passed; it consumes the dev/test evaluator reports and calibration artifact rather than pytest pass booleans.
- Calibration/evidence commit: `39838c70`.
