# Topic 5 Standard UIR Mapping Evaluation

- split: dev
- status: passed
- dataset size: 18
- auto precision: 0.9310
- auto recall: 1.0000
- auto F1: 0.9643
- assisted recall: 1.0000
- review-required rate: 0.0000
- required missing: 0
- badcase violations: 0
- conversion success rate: 1.0000
- package verifier pass rate: 1.0000
- package verified count: 18

## By Schema

| Schema | Docs | Auto precision | Auto recall | Review rate | Required missing | Badcases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| announcement_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |
| event_notice_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |
| general_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |
| meeting_doc | 3 | 0.8000 | 1.0000 | 0.0000 | 0 | 0 |
| policy_doc | 3 | 0.8000 | 1.0000 | 0.0000 | 0 | 0 |
| procurement_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |

## Warnings

- schema_precision_below_recommended_threshold: meeting_doc
- schema_precision_below_recommended_threshold: policy_doc
