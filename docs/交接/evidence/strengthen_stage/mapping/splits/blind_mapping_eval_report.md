# Real-world Mapping Evaluation

## Summary

- Documents: 8
- Auto mapping recall: 0.841
- Assisted mapping recall: 0.884
- Review-required recall: 0.043
- Review-required rate: 0.105
- Required missing: 3
- Package pass rate: 1.000
- Badcase violations: 0

Metric note: legacy `mapping_recall` is retained as assisted mapping recall.

## Per Document Type

| Document type | Documents | Auto recall | Assisted recall | Review rate | Required missing | Badcases | Package pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meeting_doc | 3 | 0.821 | 0.893 | 0.167 | 2 | 0 | 1.000 |
| policy_doc | 5 | 0.854 | 0.878 | 0.065 | 1 | 0 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_meeting_008_wlmqx_2026_01_minutes: missing=[], review_evidence=2
- real_meeting_009_kundulun_2026_01_minutes: missing=[], review_evidence=1
- real_meeting_010_zhangjiagang_64_minutes: missing=[], review_evidence=2
- real_policy_011_battery_recycling_rules: missing=[], review_evidence=2
- real_policy_014_digital_aging_campaign: missing=[], review_evidence=1

## Badcase Violations

- None

## Review Evidence

- real_meeting_008_wlmqx_2026_01_minutes: 2 item(s)
- real_meeting_009_kundulun_2026_01_minutes: 1 item(s)
- real_meeting_010_zhangjiagang_64_minutes: 2 item(s)
- real_policy_011_battery_recycling_rules: 2 item(s)
- real_policy_014_digital_aging_campaign: 1 item(s)

## Package Verification Summary

- Passed: 8
- Failed: 0
