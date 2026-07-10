# Topic 5 Mapping Quality Gate

- status: passed
- mode: global_assignment
- auto recall: 1.0000
- auto precision: 0.9310
- review-required rate: 0.0000
- required missing: 0
- badcase violations: 0
- test vs blind gap: 0.0000

## Split Metrics

| Split | Auto precision | Auto recall | Review rate | Required missing | Badcases |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 0.9310 | 1.0000 | 0.0000 | 0 | 0 |
| test | 0.9310 | 1.0000 | 0.0000 | 0 | 0 |
| blind | 0.9310 | 1.0000 | 0.0000 | 0 | 0 |

## Claim Boundary

The project demonstrates benchmark-level automatic field mapping performance within the declared Topic 5 standard UIR benchmark scope. It does not claim arbitrary-schema production performance or production shadow/blind performance.

## Per-Schema Warnings

- dev/meeting_doc: schema_precision_below_recommended_threshold
- dev/policy_doc: schema_precision_below_recommended_threshold
- test/meeting_doc: schema_precision_below_recommended_threshold
- test/policy_doc: schema_precision_below_recommended_threshold
- blind/meeting_doc: schema_precision_below_recommended_threshold
- blind/policy_doc: schema_precision_below_recommended_threshold
