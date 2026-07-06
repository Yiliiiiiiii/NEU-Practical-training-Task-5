# SchemaPack Agent 交接入口

> 最后同步：2026-07-06
> 当前分支：`codex/quality-polish`
> 实现基线 commit：`8bce0e5`

本目录是当前项目情况的统一交接入口。历史阶段计划、执行文档和旧交接记录
仍保留在原位置，但若口径冲突，以本目录、[`../project_status.md`](../project_status.md)
和 [`../openapi.json`](../openapi.json) 为准。

## 建议阅读顺序

1. [`项目交接总览.md`](项目交接总览.md)：当前能力、架构、交付物和运行方式。
2. [`验证与复现.md`](验证与复现.md)：最新验证基线、命令和证据文件。
3. [`已知边界与后续事项.md`](已知边界与后续事项.md)：明确非目标与后续优先级。
4. [`SchemaPack-Lineage交接.md`](SchemaPack-Lineage交接.md)：可信链路专项说明。

## 其他权威文档

- [`../project_status.md`](../project_status.md)：统一项目状态。
- [`../developer_guide.md`](../developer_guide.md)：开发、测试和扩展规范。
- [`../api_usage_examples.md`](../api_usage_examples.md)：API、CLI 与 SDK 示例。
- [`../package_spec.md`](../package_spec.md)：Package 1.1 契约。
- [`../lineage.md`](../lineage.md)：Lineage schema、API 与 evaluator。
- [`../demo_workflow.md`](../demo_workflow.md)：演示流程。
- [`../final_handoff_status.md`](../final_handoff_status.md)：历史阶段交接汇总。
- [`../../reports`](../../reports)：脚本生成的评测证据。

## 当前验证摘要

| 项目 | 结果 |
| --- | --- |
| Backend pytest | 567 passed |
| Ruff | clean |
| Frontend tests | 24 passed |
| Frontend production build | successful |
| OpenAPI | 63 paths |
| Regression gates | 8/8 passed |
| Badcase violations | 0 |
| LLM auto accepted | 0 |
| Package verification rate | 1.0 |
| Lineage parse / field coverage | 1.0 / 1.0 |
| Lineage broken edges / secret leaks | 0 / 0 |
