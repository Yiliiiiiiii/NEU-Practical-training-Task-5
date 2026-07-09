# Real-world Mapping Evaluation

## Summary

- Documents: 8
- Auto mapping recall: 0.812
- Assisted mapping recall: 0.855
- Review-required recall: 0.043
- Review-required rate: 0.056
- Required missing: 5
- Package pass rate: 1.000
- Badcase violations: 0

Metric note: legacy `mapping_recall` is retained as assisted mapping recall.

## Per Document Type

| Document type | Documents | Auto recall | Assisted recall | Review rate | Required missing | Badcases | Package pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meeting_doc | 3 | 0.786 | 0.857 | 0.074 | 3 | 0 | 1.000 |
| policy_doc | 5 | 0.829 | 0.854 | 0.044 | 2 | 0 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_meeting_008_wlmqx_2026_01_minutes: missing=[], review_evidence=1
- real_meeting_010_zhangjiagang_64_minutes: missing=[], review_evidence=1
- real_policy_011_battery_recycling_rules: missing=[], review_evidence=2

## Badcase Violations

- None

## Review Evidence

- real_meeting_008_wlmqx_2026_01_minutes: 1 item(s)
- real_meeting_010_zhangjiagang_64_minutes: 1 item(s)
- real_policy_011_battery_recycling_rules: 2 item(s)

## Package Verification Summary

- Passed: 8
- Failed: 0
