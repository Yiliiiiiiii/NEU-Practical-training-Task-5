# Badcase 分析

SchemaPack Agent 把 badcase checks 作为 regression gates，确保新的 mapping、knowledge 或 LLM-adjacent 功能不会静默降低输出质量。

## Badcase 类型

| Type | Risk | Protection |
| --- | --- | --- |
| Confusing source alias | source field 看起来像错误的 target field。 | Mapping confidence 和 badcase filters 让它保持 review-required。 |
| Over-eager fuzzy match | 相似 label 被映射到错误 schema field。 | Low-confidence fuzzy matches 进入 Review，而不是 auto-acceptance。 |
| Unsafe knowledge activation | 已 Review alias 可能违反已知 forbidden mappings。 | Badcase hits 在 active-pack 生效前被阻断。 |
| LLM overreach | Model suggestions 看起来合理但可能错误。 | LLM fallback 默认关闭、adapter-driven、每个 task 有 suggestion cap，且始终 review-required。 |
| LLM provider outage | Timeout 或网络失败可能中断确定性 conversion。 | 非 strict mode 记录 mapping warning 与 review item；只有显式 `strict_llm=true` 才失败 task。 |
| LLM secret leakage | Credentials 可能进入 task options、snapshots、reports 或 audit metadata。 | Credentials 只来自 environment；疑似 secret 的 persisted values 会递归 redacted，snapshots 只保留非敏感配置。 |
| Archived catalog use | 旧 schema/template versions 被用于新 tasks。 | Archived versions 会拒绝新 executions。 |
| Snapshot drift | 新 knowledge packs 可能改变历史结果。 | Task execution snapshots 保留 schema/template/effective-template context。 |

Mapping reports 现在为每个 mapping decision 输出 `risk_flags`、`confidence_tier`、`review_required_reason`、structured `evidence` 和 `badcase_filter`。已知 forbidden source/target pairs 会得到 `badcase_blocked`，且不会被自动接受。

## 当前 Regression Checks

运行：

```powershell
.\backend\.venv\Scripts\python.exe scripts\eval_production_like.py
```

期望：

```text
production-like eval complete: 15 cases, gold=1.0, badcase=1.0
```

生成报告包含：

- `phase_b.badcase_violation_count`
- `phase_b.badcase_pass_rate`
- per-case `badcases`
- `old_run_snapshot_unchanged`
- `package_validation`
- `downstream_smoke_summary`

## 当前结果

当前期望结果：

```text
badcase_violation_count = 0
badcase_pass_rate = 1.0
```

## 非采购 Recall Badcases

Expanded real-world mapping gold 可以内嵌 badcases；standalone `examples/real_world/gold/real_world_badcases.jsonl` 是覆盖全部文档的权威 registry，并包含所有 embedded `known_badcases`。非采购 recall 工作新增了高风险 source/target pairs 的 regression coverage，确保它们不会 auto-accept：

| Source label | Forbidden target | Reason |
| --- | --- | --- |
| `发布日期` | `effective_date` | 发布日期 metadata 不能自动等同于生效日期。 |
| `主持人` | `attendees` | 会议主持人/主席不是完整参会人员列表。 |
| `联系人` | `attendees` | 联系人不是会议参会人员列表。 |
| `承办单位` | `issuer` | 承办/组织单位不一定是发文机关。 |
| `预算金额` | `award_amount` | 预算不是中标金额。 |
| `控制价` | `award_amount` | 控制价不是中标金额。 |

这些 badcases 防止 recall 工作变成指标投机：ambiguous 或 high-risk evidence 应保持 review-required，除非有 source-backed safe rule。最新 package-based non-procurement analysis 和 API-backed non-procurement evaluator 均记录 zero badcase violations。深化后的 phase gate 已通过：average recall `0.5678`、review-required 69、required missing 6、package verification 35/35。

本轮另外固定了三条治理边界：

- `成文日期 -> publish_date` 不自动接受；
- `retrieved_at -> effective_date` 作为 Knowledge Pack 阻断控制；
- API knowledge evaluator 只处理当前 task 的显式安全 review pairs，不消费历史 pending reviews。

## 剩余限制

- Regression dataset 仍偏 synthetic，生产 rollout 前应补充真实 enterprise UIR cases。
- Badcase filters 是 deterministic rule-based 保护，不能替代 ambiguous mappings 的人工 Review。
- LLM fallback 仍是 optional 且 human-gated；provider/model evaluation 与 enterprise monitoring 属于部署职责。
