# Mapping Recall 0.85 Guarded Sprint

本文档记录字段映射 0.85 冲刺的本轮落地结果。当前结论必须如实表述：本轮已清零 required missing，并保持 badcase safety、package verification 和 overfit scan 通过；但 dev/test assisted recall 仍未达到 0.85，不能宣称 0.85 gate 已通过。

## 1. 执行约束

- 不根据 `doc_id` 写特例规则。
- 不在 runtime mapping 中读取 `mapping_gold.jsonl`、`expected_mappings` 或 badcase gold。
- 不牺牲 badcase safety。
- 不自动接受 LLM suggestion。
- 不通过大幅增加 review-required 虚高指标。
- 能力增强必须来自通用规则或 source-backed candidate extraction。

## 2. 本轮完成内容

| 类别 | 状态 | 说明 |
| --- | --- | --- |
| Evidence path | 已完成 | 评测证据输出到 `docs/交接/evidence/`，避免 README 依赖未提交的 `reports/*` sprint 证据。 |
| P0 required missing | 已完成 | `required_missing_count` 从 2 降到 0。 |
| policy issuer | 已增强 | 支持更多显式 issuer label、分行署名块、弱 source_site 仅 review。 |
| policy publish_date | 已增强 | 支持 `公布日期`、ISO 日期、分行署名日期；official URL year-only 只进 review。 |
| general deadline | 已增强 | 支持 `申报截止时间` 等 label 与 `于 X 前提交` 句式。 |
| meeting action/topic | 已增强 | 补充责任行动句式；保留 topics/decisions/action_items 负样本边界。 |
| evidence naming | 已增强 | 文号 regex 候选 source_name 保留真实文号值。 |
| Tests | 已完成 | 新增/更新 policy/general/meeting/candidate 规则测试。 |

## 3. Final Sprint Result

最终评测时间：2026-07-09 09:33（Asia/Shanghai）

| Metric | Value |
| --- | ---: |
| Dataset size | 50 |
| Dev assisted recall | 0.807 |
| Test assisted recall | 0.794 |
| Blind assisted recall | 0.855 |
| Auto mapping recall overall | 0.7774798927613941 |
| Assisted mapping recall overall | 0.8096514745308311 |
| Review-required rate | 0.043583535108958835 |
| Review-required count | 18 |
| Required missing | 0 |
| Badcase violations | 0 |
| Package pass rate | 1.000 |
| Strict pass | 48/50 |
| Overfit scan | Pass |
| Quality gate | Failed |
| verify_all | 730 passed; Ruff passed; frontend build passed; OpenAPI 63 paths |
| frontend tests | 24 passed / 8 files |

### Split Summary

| Split | Docs | Auto Recall | Assisted Recall | Review Rate | Required Missing | Badcase Violations | Package Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 18 | 0.763 | 0.807 | 0.050 | 0 | 0 | 1.000 |
| test | 9 | 0.779 | 0.794 | 0.013 | 0 | 0 | 1.000 |
| blind | 8 | 0.812 | 0.855 | 0.056 | 0 | 0 | 1.000 |

Generalization gap:

- dev vs test assisted recall gap: 0.013
- test vs blind assisted recall gap: -0.061
- conclusion: pass

### Quality Gate Result

质量门禁未通过，失败原因：

- dev assisted recall 0.807 < 0.850
- test assisted recall 0.794 < 0.850

本轮是否达到 0.85：否。

剩余缺口：source-name exact recall 和少数长尾 review/source alignment。当前 gap analysis 中 `required_missing` 已为 0；后续主要提升点是 general/service fields、meeting source-name alignment、policy_005 irregular heading/source evidence 这类可解释证据，而不是继续扩大 review-required。

## 4. Evidence Files

- [`docs/交接/evidence/mapping_metric_baseline_snapshot.md`](evidence/mapping_metric_baseline_snapshot.md)
- [`docs/交接/evidence/mapping_splits/summary.md`](evidence/mapping_splits/summary.md)
- [`docs/交接/evidence/mapping_gap_analysis.md`](evidence/mapping_gap_analysis.md)
- [`docs/交接/evidence/mapping_overfit_risk_report.md`](evidence/mapping_overfit_risk_report.md)
- [`docs/交接/evidence/mapping_quality_gate_result.md`](evidence/mapping_quality_gate_result.md)
- [`reports/non_procurement_mapping_eval_report.md`](../../reports/non_procurement_mapping_eval_report.md)

## 5. Reproducible Commands

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:18000 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py --report reports\non_procurement_mapping_eval_report.json --out-dir docs\交接\evidence\mapping_splits

backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py --report reports\non_procurement_mapping_eval_report.json --out-json docs\交接\evidence\mapping_gap_analysis.json --out-md docs\交接\evidence\mapping_gap_analysis.md

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py --out-json docs\交接\evidence\mapping_overfit_risk_report.json --out-md docs\交接\evidence\mapping_overfit_risk_report.md

backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py --report docs\交接\evidence\mapping_splits\summary.json --min-assisted-recall 0.85 --max-badcase-violations 0 --max-required-missing 0 --max-dev-test-gap 0.05 --max-test-blind-gap 0.05

backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
Pop-Location
```

## 6. Safety Status

| Check | Result |
| --- | --- |
| badcase violations | 0 |
| required missing | 0 |
| package pass rate | 100% |
| overfit risk scan | Pass |
| doc_id-specific runtime rules found | 0 |
| gold leakage found | 0 |
| LLM auto accepted | 0 |
| review-required inflation | Not observed; rate 0.0436 |

## 7. 下一步建议

1. 继续提升 source-name exact recall，优先处理通用 source_name 规范化，而不是样例特化。
2. 对 general_doc 的 service_object / application_conditions / contact 做 review-vs-accepted 风险分层，避免把宽泛段落自动 accepted。
3. 对 meeting_doc 的 meeting_date、meeting_number、topics 增加更多通用 source-name alias，但仍避免参会人员/主持人误入 topics。
4. 对 policy_doc 的 irregular heading / attachment / page title 场景继续补 source-backed review 候选，不把 `附件1` 等弱信息自动映射为 issuer。
