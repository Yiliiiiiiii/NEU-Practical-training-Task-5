# Badcase 分析

SchemaPack Agent 把 badcase checks 作为 regression gates，确保新的 mapping、knowledge 或 LLM-adjacent 功能不会静默降低输出质量。

## Badcase 类型

| Type | Risk | Protection |
| --- | --- | --- |
| Confusing source alias | source field 看起来像错误的 target field。 | Mapping confidence 和 badcase filters 让它保持 review-required。 |
| Over-eager fuzzy match | 相似 label 被映射到错误 schema field。 | Low-confidence fuzzy matches 进入 Review，而不是 auto-acceptance。 |
| Unsafe knowledge activation | 已 Review alias 可能违反已知 forbidden mappings。 | Badcase hits 在 active-pack 生效前被阻断。 |
| LLM overreach | Model suggestions 看起来合理但可能错误。 | LLM fallback 默认关闭、suggestion cap、report-only/review-required，且不会自动 accepted。 |
| LLM provider outage | Timeout 或网络失败可能中断确定性 conversion。 | 非 strict mode 记录 warning/review item；只有显式 strict 才失败 task。 |
| LLM secret leakage | Credentials 可能进入 task options、snapshots、reports 或 audit metadata。 | Credentials 只来自 environment；persisted values 脱敏；secret audit 检查高熵密钥。 |
| Archived catalog use | 旧 schema/template versions 被用于新 tasks。 | Archived versions 会拒绝新 executions。 |
| Snapshot drift | 新 knowledge packs 可能改变历史结果。 | Task execution snapshots 保留 schema/template/effective-template context。 |

Mapping reports 为每个 mapping decision 输出 `risk_flags`、`confidence_tier`、
`review_required_reason`、structured `evidence` 和 `badcase_filter`。已知 forbidden
source/target pairs 会得到 `badcase_blocked` 或保持 review-required，且不会被自动接受。

## 当前 Regression Checks

生产类/回归门禁：

```powershell
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

非采购语义评测：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\phase_d_non_procurement_mapping_eval_report.json `
  --markdown reports\phase_d_non_procurement_mapping_eval_report.md
```

## 当前结果

当前关键结果：

```text
regression gates = 8/8 passed
real_world badcase violations = 0
phase_d badcase violations = 0
llm_auto_accepted_count = 0
secret leaks = 0
```

Non-procurement semantic sprint 当前记录：

```text
dataset_size = 50
average_recall = 0.8063730159
strict_pass = 47/50
required_missing = 2
review_required = 16
package_verification = 50/50
badcase_violations = 0
```

## 非采购 Recall Badcases

Expanded real-world mapping gold 可以内嵌 badcases；standalone
`examples/real_world/gold/real_world_badcases.jsonl` 是覆盖全部文档的权威 registry，
并包含 embedded `known_badcases`。非采购 recall 工作覆盖了高风险 source/target
pairs，确保它们不会 auto-accept：

| Source label | Forbidden target | Reason |
| --- | --- | --- |
| `发布日期` | `effective_date` | 发布日期 metadata 不能自动等同于生效日期。 |
| `retrieved_at` | `effective_date` | 抓取时间不能自动等同于生效日期。 |
| `主持人` | `attendees` | 会议主持人/主席不是完整参会人员列表。 |
| `联系人` | `attendees` | 联系人不是会议参会人员列表。 |
| `承办单位` | `issuer` | 承办/组织单位不一定是发文机关。 |
| `预算金额` | `award_amount` | 预算不是中标金额。 |
| `控制价` | `award_amount` | 控制价不是中标金额。 |

这些 badcases 防止 recall 工作变成指标投机：ambiguous 或 high-risk evidence 应保持
review-required，除非有 source-backed safe rule。

## DeepSeek / Review Judge 安全结果

- DeepSeek provider smoke：passed，suggestion_count 2，warning_count 0，secret_leak_detected false。
- DeepSeek ablation：report-only not applied；measurable contribution 0.0；auto accepted 0。
- Review judge dry-run：pending 979，suggest reject 26，suggest approve 0，unsafe skipped 953。
- Safe apply：applied approve 0，applied reject 0，kept pending 979。
- Secret redaction audit：passed；exact secret file hits 0；secret leaks 0。

## 剩余限制

- Badcase filters 是 deterministic rule-based 保护，不能替代 ambiguous mappings 的人工 Review。
- 当前 Phase D average recall 未达到 0.78；policy_doc 仍是主要瓶颈。
- 当前无独立 production blind/shadow gold corpus，不能宣称 0.85。
- LLM fallback 仍是 optional 且 human-gated；provider/model evaluation 与 enterprise monitoring 属于部署职责。
