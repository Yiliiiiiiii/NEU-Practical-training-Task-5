# Procurement Catalog Evaluation

## Summary

- Delta: procurement_doc - general_doc
- Gold recall delta: 0.528
- Required coverage delta: 0.667

## Required Coverage

| Catalog | Required coverage | Missing required |
| --- | ---: | ---: |
| general_doc | 0.333 | 10 |
| procurement_doc | 1.000 | 0 |

## Gold Recall Delta

| Catalog | Gold recall | Package pass rate |
| --- | ---: | ---: |
| general_doc | 0.094 | 1.000 |
| procurement_doc | 0.623 | 1.000 |

## Badcase Comparison

| Catalog | Badcase violations |
| --- | ---: |
| general_doc | 0 |
| procurement_doc | 0 |

## Procurement Detail

# Real-world Mapping Evaluation

## Summary

- Documents: 5
- Mapping recall: 0.623
- Package pass rate: 1.000
- Badcase violations: 0

## Per Document Type

| Document type | Documents | Mapping recall | Package pass rate |
| --- | ---: | ---: | ---: |
| procurement_doc | 5 | 0.623 | 1.000 |

## Per Field

| Field | Missing required | Badcase violations |
| --- | ---: | ---: |

## Missing Or Ambiguous

- real_procurement_001_broadcast_security_supervision: missing=[], review_evidence=2
- real_procurement_002_special_equipment_bid: missing=[], review_evidence=2
- real_procurement_003_radiation_monitoring_award: missing=[], review_evidence=4
- real_procurement_004_veterinary_platform_award: missing=[], review_evidence=4
- real_procurement_005_rehabilitation_equipment_award: missing=[], review_evidence=4

## Badcase Violations

- None

## Review Evidence

- real_procurement_001_broadcast_security_supervision: 2 item(s)
- real_procurement_002_special_equipment_bid: 2 item(s)
- real_procurement_003_radiation_monitoring_award: 4 item(s)
- real_procurement_004_veterinary_platform_award: 4 item(s)
- real_procurement_005_rehabilitation_equipment_award: 4 item(s)

## Package Verification Summary

- Passed: 5
- Failed: 0
