# Real-world Knowledge Loop Report

## Before / after

| Stage | Auto mapped | Review required | Missing required |
| --- | ---: | ---: | ---: |
| Before | 7 | 3 | 1 |
| After | 8 | 2 | 0 |

## Decision evidence

| Decision | Source field | Target field | Outcome | Reason |
| --- | --- | --- | --- | --- |
| approve | 采购方名称 | purchaser | activated | 采购方名称与采购人语义一致，可作为采购文档 purchaser 的安全别名。 |
| reject | 最高限价 | award_amount | review_only | 最高限价是预算/控制价，不是中标金额，不能激活到 award_amount。 |

## Safety

- Badcase violations: 0
- Old snapshot unchanged: true

## Remaining ambiguous cases

- 最高限价
