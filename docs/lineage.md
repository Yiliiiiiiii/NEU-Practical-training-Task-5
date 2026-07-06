# SchemaPack-Lineage 可信转换链路

SchemaPack-Lineage 是现有转换主链路的只读旁路记录层。它不会参与 mapping、transform、validation 或 package 决策，只把来源、证据、决策、版本与最终 artifact 串成可查询的有向图。

```text
External Field -> Adapter Trace -> UIR Block -> Candidate
-> Mapping Decision -> Review / Knowledge -> Schema Field
-> Canonical Field -> Chunk / Rendered Artifact
-> Manifest Entry -> Consumer Contract
```

## Task 输出

Task 默认使用：

```json
{
  "enable_lineage": true,
  "strict_lineage": false
}
```

执行成功后写入：

```text
storage/tasks/{task_id}/lineage_graph.json
storage/tasks/{task_id}/lineage_summary.json
```

实际 storage root 由 `STORAGE_ROOT` 决定。`strict_lineage=false` 时，lineage 构建失败只写入 execution snapshot 的 `lineage_warnings`，不改变原 task 的成功结果；显式启用 strict 模式时才让异常阻断 task。

## 查询 API

```text
GET /api/v1/tasks/{task_id}/lineage
GET /api/v1/tasks/{task_id}/lineage/summary
GET /api/v1/tasks/{task_id}/lineage/fields/{field_name}
GET /api/v1/tasks/{task_id}/lineage/chunks/{chunk_id}
GET /api/v1/tasks/{task_id}/lineage/artifacts/{artifact_path}
```

字段、chunk 与 artifact 查询支持：

```text
direction=upstream|downstream|both
max_depth=1..32
```

不存在的 task 或 root 统一返回 `404`。Artifact path 需要 URL encode。

## 审计语义

- accepted mapping、review-required mapping 与 badcase-blocked mapping 使用不同状态。
- LLM suggestion 只能保持 `review_required`；evaluator 会把 accepted LLM mapping 计为安全违规。
- 文档中不存在的 optional field 会生成 `source_not_present` 决策。它只证明缺失已被明确记录，不会向 canonical 补值。
- External UIR task 通过 task option snapshot 保留 adapter report，并生成 `external_field -> adapter_trace -> uir_block`。
- Review、knowledge candidate 与 applied active pack 通过稳定 id 关联。
- Manifest entry 保留 path、role、media type、bytes 与 SHA-256。
- Lineage metadata 会递归移除 secret-like key，并屏蔽 bearer、credential 与 `sk-` 形式的值。

## Package MVP 边界

Lineage graph 能追踪现有 ZIP artifacts 到 manifest 与 consumer contract，但 `lineage_graph.json` 和 `lineage_summary.json` 本期只作为 task reports，不写入 ZIP。

原因是 graph 需要记录最终 manifest hash；如果 graph 自身也进入 manifest，就会形成自引用 checksum。Package 1.1 required artifacts、verifier 与 consumer contracts 因此保持不变。后续如需进入 ZIP，应先定义不引用自身 hash 的独立 package-lineage contract。

## Frontend

Task 执行并产生 lineage report 后，工作台“可信链路”面板显示：

- 总体、field、chunk、artifact coverage；
- review-required、blocked 与 knowledge 状态；
- field/chunk/artifact 查询；
- 分层 ledger 与 node metadata/evidence。

固定提示：

> Lineage 证明来源、证据和决策链路可追溯；它不等同于字段语义严格正确。请同时查看 Validation、Review、Badcase 和 Evaluation 报告。

## Evaluation

```powershell
backend\.venv\Scripts\python.exe scripts\eval_lineage_graph.py `
  --base-url http://127.0.0.1:8000 `
  --out reports\lineage_eval_report.json `
  --markdown reports\lineage_eval_report.md `
  --evaluation-metrics reports\evaluation_center\current_metrics.json
```

Evaluator 直接解析 graph 并计算 parse pass、field/chunk/artifact coverage、mapping/review/knowledge/manifest link rate、orphan、broken edge、secret leak 与 LLM auto-accept。

Evaluation Center hard gates：

```text
lineage_parse_pass_rate >= 1.0
lineage_broken_edges == 0
lineage_secret_leaks == 0
lineage_field_coverage >= 0.90
```

Demo 报告由以下命令生成：

```powershell
backend\.venv\Scripts\python.exe scripts\build_lineage_demo_report.py `
  --graph backend\storage\tasks\<task_id>\lineage_graph.json `
  --out reports\lineage_demo_report.json `
  --markdown reports\lineage_demo_report.md
```

