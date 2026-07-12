# SchemaPack Agent Current Status

> Generated from `docs/交接/topic5_current_status.json`. Do not edit measured values manually.

- Commit: `f335a7225b91d4bee6ca7af707d9d21204fc2e43`
- Branch: `feat/topic5-batch-2-reliability`
- Batch 2 status: `pending_external_ci`
- Local acceptance: `True`
- Exact-head GitHub CI: `False`

## Verification

- Backend tests: 1224 passed
- Backend and Topic 5 Ruff: True
- Frontend tests: True
- Frontend build: True
- OpenAPI drift: 0
- SchemaPack gate: True

## Batch 2 Metrics

- Mapping exact/F1: 0.996283 / 0.998138
- Mapping precision/recall: 1.000000 / 0.996283
- Tag content F1: 0.851064
- Runtime equivalence: 1.0
- Replay semantic match: 1.0
- Partial package survival: 0
- Invalid export acceptance: 0

## Boundaries

- Topic 5 remains UIR/External UIR to schema-driven verified package conversion.
- External blind mapping is not run; production-blind 0.85 is not claimed.
- Performance evidence applies only to the recorded host and is not an absolute SLO.
- LLM suggestions remain disabled or review-only and are excluded from automatic metrics.
