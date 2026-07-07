# Review Knowledge Growth Report

- Passed: True
- Real UIR: `examples/real_world/uir/general/real_general_011_shanghai_branch_registration.json`
- Old snapshot unchanged: True
- Badcase violations: 0
- Rejected candidates activated: 0

## Before / After

| Stage | Review required | Auto mapped | Mapping recall | Required coverage | Strict pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before | 2 | 5 | 0.0000 | 1.0000 | 1 |
| After | 1 | 6 | 1.0000 | 1.0000 | 1 |

## Activated aliases

- `service_object`: `受理`

## Rejected controls

- `内容` → `summary`: activated=False; The generic legal basis content row should not become a summary alias by default.

## Snapshot invariant

- metadata: bytes=True, structure=True
- canonical: bytes=True, structure=True
- mapping_report: bytes=True, structure=True
- execution_snapshot: bytes=True, structure=True
