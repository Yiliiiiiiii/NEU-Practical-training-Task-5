# Review Knowledge Growth Report

- Passed: True
- Real UIR: `examples/real_world/uir/policy/real_policy_001_training_platform_rules.json`
- Old snapshot unchanged: True
- Badcase violations: 0
- Rejected candidates activated: 0

## Before / After

| Stage | Review required | Auto mapped | Mapping recall | Required coverage | Strict pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before | 5 | 3 | 0.0000 | 0.5000 | 1 |
| After | 4 | 4 | 1.0000 | 0.5000 | 1 |

## Activated aliases

- `document_number`: `发文字号：`

## Rejected controls

- `retrieved_at` → `target_audience`: activated=False; Retrieval time is provenance metadata and must not become the policy target audience.

## Snapshot invariant

- metadata: bytes=True, structure=True
- canonical: bytes=True, structure=True
- mapping_report: bytes=True, structure=True
- execution_snapshot: bytes=True, structure=True
