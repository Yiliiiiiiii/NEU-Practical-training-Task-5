# Mapping Recall 0.85 Guarded Sprint

本文档记录字段映射指标提升与防过拟合执行文档的本轮落地结果。它是可提交版本；`reports/*` 下的同名评测报告由脚本生成，但当前仓库规则会忽略这些文件。

## 1. 目标

本轮目标是在不引入以下风险的前提下，推进字段映射 assisted recall 向 `0.85` 收敛：

- 不根据 `doc_id` 写特例规则；
- 不在 runtime mapping 中读取 gold label；
- 不牺牲 badcase safety；
- 不自动接受 LLM suggestion；
- 不通过大幅增加 review-required 虚高指标。

## 2. 本轮已完成

| 类别 | 状态 | 说明 |
| --- | --- | --- |
| 指标口径拆分 | 已完成 | `auto_mapping_recall`、`assisted_mapping_recall`、`review_required_recall`、`review_required_rate` 已加入评分与报告。 |
| Baseline snapshot | 已完成 | 新增 `scripts/build_mapping_metric_baseline_snapshot.py`，生成 `reports/mapping_metric_baseline_snapshot.md`。 |
| dev/test/blind split | 已完成 | 新增 `examples/real_world/splits/mapping_split_manifest.json` 与三个 doc_id 列表。 |
| Split evaluator | 已完成 | 新增 `scripts/eval_mapping_splits.py`，输出 split JSON/Markdown summary。 |
| Gap analysis | 已完成 | 新增 `scripts/analyze_mapping_gaps.py`，按 doc_type/field/estimated gain 排序。 |
| Overfit risk scan | 已完成 | 新增 `scripts/check_mapping_overfit_risk.py`，扫描 doc_id 特例和 gold 泄漏。 |
| Quality gate | 已完成 | 新增 `scripts/check_mapping_quality_gate.py`，支持 recall、badcase、required missing 和 split gap 阈值。 |
| 模板增强 | 已完成一轮 | 增强 policy/general/meeting 模板通用别名，并保留现有 unsafe alias 排除规则。 |
| README/需求映射 | 已更新 | 明确 legacy average recall 是 assisted recall 兼容口径。 |

## 3. 当前基线

基线来自 `reports/non_procurement_mapping_eval_report.json`，通过 `scripts/build_mapping_metric_baseline_snapshot.py` 生成快照。

| Metric | Value |
| --- | ---: |
| dataset_size | 35 |
| average_recall / legacy assisted recall | 0.6096598639455783 |
| auto_mapping_recall | 0.6095617529880478 |
| assisted_mapping_recall | 0.6095617529880478 |
| review_required_rate | 0.22264150943396227 |
| review_required_count | 59 |
| required_missing_count | 4 |
| badcase_violations | 0 |
| package_verification_pass | 35 |

结论：当前 baseline 尚未达到 `0.85`，不能宣称达标。

## 4. Split 结果

| Split | Docs | Auto Recall | Assisted Recall | Review Rate | Required Missing | Badcase Violations | Package Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 18 | 0.579 | 0.579 | 0.223 | 2 | 0 | 1.000 |
| test | 9 | 0.676 | 0.676 | 0.291 | 0 | 0 | 1.000 |
| blind | 8 | 0.594 | 0.594 | 0.125 | 2 | 0 | 1.000 |

Generalization gap:

- dev vs test assisted recall gap: `-0.098`
- test vs blind assisted recall gap: `0.082`
- conclusion: `review_required`

## 5. Quality Gate 结果

当前按最终阈值运行质量门禁：

```powershell
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
  --report reports\mapping_splits\summary.json `
  --min-assisted-recall 0.85 `
  --max-badcase-violations 0 `
  --max-required-missing 0 `
  --max-dev-test-gap 0.05 `
  --max-test-blind-gap 0.05
```

结果：未通过。

失败原因：

- dev assisted recall `0.579 < 0.850`；
- dev required missing `2 > 0`；
- test assisted recall `0.676 < 0.850`；
- blind assisted recall `0.594 < 0.850`；
- blind required missing `2 > 0`；
- test/blind assisted recall gap `0.082 > 0.050`。

## 6. Gap Analysis 优先级

当前 gap analysis 排名前十的修复目标：

1. `meeting_doc.topics`
2. `policy_doc.issuer`
3. `policy_doc.publish_date`
4. `general_doc.deadline`
5. `policy_doc.target_audience`
6. `general_doc.application_conditions`
7. `general_doc.service_object`
8. `policy_doc.policy_measures`
9. `meeting_doc.action_items`
10. `meeting_doc.decisions`

下一轮建议优先做 source-backed candidate extraction，而不是继续只扩模板 alias。尤其是 `meeting_doc.topics`、`policy_doc.issuer`、`policy_doc.publish_date`，需要从正文结构、标题段、署名段、网页元数据和安全负样本中抽取更强证据。

## 7. 安全状态

| Check | Result |
| --- | --- |
| badcase violations | 0 |
| package pass rate | 100% |
| overfit risk scan | pass |
| doc_id-specific runtime rules found | 0 |
| gold leakage found | 0 |
| LLM auto accepted | 0 |

Overfit scanner 当前扫描 runtime app code 与 production-like schema/template，没有发现 `real_policy_`、`real_general_`、`real_meeting_`、`real_procurement_`、`doc_id ==` 或 gold leakage 进入 runtime mapping 的风险。

## 8. 可复现命令

```powershell
backend\.venv\Scripts\python.exe scripts\build_mapping_metric_baseline_snapshot.py
backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py
backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py
backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py
backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py --report reports\mapping_splits\summary.json --min-assisted-recall 0.85 --max-badcase-violations 0 --max-required-missing 0 --max-dev-test-gap 0.05 --max-test-blind-gap 0.05
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

## 9. 验证记录

本轮完整验证：

- `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`
- backend pytest：718 passed
- backend ruff：passed
- frontend build：passed
- OpenAPI export：63 paths

质量门禁按最终 0.85 阈值未通过，这是预期的真实验收结论，而不是脚本故障。

## 10. 下一步建议

1. 为 `meeting_doc.topics` 增加正文开场句、议题列表、研究事项、传达学习类段落的候选抽取。
2. 为 `policy_doc.issuer` 增加 source-backed issuer candidate，区分 `发布单位/发文机关/署名机构/来源网站/联系人`。
3. 为 `policy_doc.publish_date` 增强显式发布日期与署名日期的安全区分，继续禁止 `成文日期` 自动作为 publish_date。
4. 为 `general_doc.deadline` 增加截止、受理、办理期限类 label 与正文句式抽取。
5. 每次规则增强后重新运行 split evaluator、overfit risk scan 和 quality gate。
