# SchemaPack-Lineage 专项交接

## 当前实现

- Schema：`backend/app/schemas/lineage.py`
- Graph builder：`backend/app/services/lineage_graph_service.py`
- Query service：`backend/app/services/lineage_query_service.py`
- API：`backend/app/api/v1/lineage.py`
- Frontend：`frontend/src/components/LineagePanel.tsx`
- Evaluator：`scripts/eval_lineage_graph.py`
- Demo report：`scripts/build_lineage_demo_report.py`
- 详细规范：[`../lineage.md`](../lineage.md)

## 数据流

```text
External Field / Standard UIR Block
-> Adapter Trace
-> UIR Block
-> Field Candidate
-> Mapping Decision
-> Review / Knowledge
-> Schema Field
-> Canonical Field
-> Chunk / Rendered Artifact
-> Manifest Entry
-> Consumer Contract
```

## Task 行为

默认 options：

```json
{
  "enable_lineage": true,
  "strict_lineage": false
}
```

Task 执行后生成：

```text
tasks/{task_id}/lineage_graph.json
tasks/{task_id}/lineage_summary.json
```

实际根目录由 `STORAGE_ROOT` 决定。

Non-strict 模式下，lineage 构建失败写入 execution snapshot 的
`lineage_warnings`，不会破坏原 task。Strict 模式才上抛异常。

## API

```text
GET /api/v1/tasks/{task_id}/lineage
GET /api/v1/tasks/{task_id}/lineage/summary
GET /api/v1/tasks/{task_id}/lineage/fields/{field_name}
GET /api/v1/tasks/{task_id}/lineage/chunks/{chunk_id}
GET /api/v1/tasks/{task_id}/lineage/artifacts/{artifact_path}
```

子图查询支持：

```text
direction=upstream|downstream|both
max_depth=1..32
```

## 安全约束

- secret-like key 被递归移除。
- bearer、credential 与 `sk-` 形式的值被屏蔽。
- LLM suggestion 必须保持 review-required。
- badcase-blocked mapping 必须显示为 blocked。
- `source_not_present` 只记录字段缺失，不向 canonical 补值。
- External path 保存在 adapter trace 或 block attributes，不写入
  `source_anchor`。

## Package 边界

Lineage 当前可追踪 Package 1.1 中已有 artifacts 的 path、role、media type、
bytes 与 SHA-256，但 lineage graph/summary 自身不进入 ZIP。

这是为避免 graph 引用最终 manifest hash 时形成 checksum 自引用。后续要加入
ZIP，必须先定义独立、非自引用的 lineage package contract。

## 当前指标

```text
parse pass rate = 1.0
field coverage = 1.0
chunk coverage = 1.0
artifact coverage = 1.0
broken edges = 0
secret leaks = 0
LLM auto accepted = 0
```

Evaluation Center hard gates：

```text
lineage_parse_pass_rate >= 1.0
lineage_broken_edges == 0
lineage_secret_leaks == 0
lineage_field_coverage >= 0.90
```

## 固定说明

> Lineage 证明来源、证据和决策链路可追溯；它不等同于字段语义严格正确。
> 请同时查看 Validation、Review、Badcase 和 Evaluation 报告。
