# Review Knowledge Growth Report

- Passed: True
- Real UIR: `examples/real_world/uir/meeting/real_meeting_004_shandan_2025_11_minutes.json`
- Old snapshot unchanged: True
- Badcase violations: 0
- Rejected candidates activated: 0

## Before / After

| Stage | Review required | Auto mapped | Mapping recall | Required coverage | Strict pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before | 3 | 8 | 0.0000 | 1.0000 | 1 |
| After | 2 | 9 | 1.0000 | 1.0000 | 1 |

## Activated aliases

- `organizer`: `发布机构`

## Rejected controls

- `agenda sections` → `decisions`: activated=False; Agenda narrative should not be accepted as the meeting decisions field by default.

## Snapshot invariant

- metadata: bytes=True, structure=True
- canonical: bytes=True, structure=True
- mapping_report: bytes=True, structure=True
- execution_snapshot: bytes=True, structure=True
