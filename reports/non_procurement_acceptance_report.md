# 非采购 Mapping Recall 验收报告

本报告面向扩展后 30-document real-world dataset 中的 20-document 非采购子集。

## 证据来源

- Baseline：`reports/non_procurement_baseline_report.{json,md}`
- Offline package gap analysis：`reports/non_procurement_gap_analysis.{json,md}`
- API-backed evaluator：`reports/non_procurement_mapping_eval_report.{json,md}`
- 改进计划与 ranked diagnosis：`docs/non_procurement_mapping_improvement_plan.md`

## 验收摘要

最新提交的 API-backed evaluation 未达到 Phase 1 验收目标。Evaluator 已成功处理全部 20 个非采购 documents，但 recall 与 review-required thresholds 仍超出验收边界。

| 检查项 | 目标 | 最新证据 | 状态 |
| --- | ---: | ---: | --- |
| Average mapping recall | `>= 0.50` | `0.4211309523809524` | 未达标 |
| Review-required count | `<= 115` | `149` | 未达标 |
| Required missing count | `<= 14` | `12` | 达标 |
| Badcase violations | `0` | `0` | 达标 |
| Package verification | `20/20` | `20/20` | 达标 |
| Backend regression tests | 无回归 | 本报告前最近一次完整 backend run：`392 passed` | 当时通过 |
| Frontend 与 unified verification | Build 和 `verify_all` 通过 | frontend build 通过；`verify_all --check-openapi` 通过 | 达标 |

## 有用的非 API 证据

Offline package-based gap analyzer 已在非采购子集上完成，可用于诊断：

| Metric | Baseline | 最新 gap analysis |
| --- | ---: | ---: |
| Non-procurement documents | 20 | 20 |
| Strict pass count | 4 | 4 |
| Required missing count | 18 | 15 |
| Review-required count | 145 | 139 |
| Average mapping recall | `0.3494047619047619` | `0.4211309523809524` |
| Badcase violations | 0 | 0 |
| Package verification | 20/20 | 从完整 package outputs 分析 20 个 packages |

这说明 package-derived diagnostics 有安全的增量改善。API-backed evaluator 与 gap analyzer 在 average recall 和 package verification 上一致，但 API-backed evaluator 记录 149 个 review-required mappings 和 12 个 required missing mappings。Required-missing gate 已进入目标范围；recall 与 review-required gates 仍未关闭。

## 决策

Phase 1 仍保持 open。下一步应在不削弱 badcase filters、不中途 auto-accept ambiguous evidence 的前提下，降低 review-required mappings 并提高 average recall。
