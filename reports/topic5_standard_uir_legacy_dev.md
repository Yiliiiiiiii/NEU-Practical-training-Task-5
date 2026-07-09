# Topic 5 Standard UIR Mapping Evaluation

- split: dev
- status: failed
- dataset size: 18
- auto precision: 0.8966
- auto recall: 0.9630
- auto F1: 0.9286
- assisted recall: 1.0000
- review-required rate: 0.0513
- required missing: 0
- badcase violations: 0
- package pass rate: 1.0000

## By Schema

| Schema | Docs | Auto precision | Auto recall | Review rate | Required missing | Badcases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| announcement_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |
| event_notice_doc | 3 | 1.0000 | 1.0000 | 0.0000 | 0 | 0 |
| general_doc | 3 | 0.7500 | 0.7500 | 0.0588 | 0 | 0 |
| meeting_doc | 3 | 0.8000 | 1.0000 | 0.0000 | 0 | 0 |
| policy_doc | 3 | 0.8000 | 1.0000 | 0.0000 | 0 | 0 |
| procurement_doc | 3 | 1.0000 | 1.0000 | 0.1667 | 0 | 0 |

## Failures

- auto_precision_below_threshold
