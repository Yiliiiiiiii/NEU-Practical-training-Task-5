# Review Knowledge Growth Report

- Passed: True
- Real UIR: `examples/real_world/uir/policy/real_policy_001_training_platform_rules.json`
- Old snapshot unchanged: True
- Badcase violations: 0
- Rejected candidates activated: 0

## Before / After

| Stage | Review required | Auto mapped | Mapping recall | Required coverage | Strict pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before | 3 | 5 | 0.0000 | 1.0000 | 1 |
| After | 2 | 6 | 1.0000 | 1.0000 | 1 |

## Activated aliases

- `document_number`: `发文字号：`

## Rejected controls

- `source_site` → `source`: activated=False; The hosting domain alone is provenance context and is not the canonical source URL.

## Snapshot invariant

- metadata: bytes=True, structure=True
- canonical: bytes=True, structure=True
- mapping_report: bytes=True, structure=True
- execution_snapshot: bytes=True, structure=True
