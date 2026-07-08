# SchemaPack Agent 交接入口

> 最后同步：2026-07-07
> 当前分支：`main`
> 当前基线 commit：`7fd38c77 feat: add phase D/E/F review safety reports`

本目录是当前项目情况的统一交接入口。历史阶段计划与执行文档仍保留在原位置；
若口径冲突，以本目录、[`project_status.md`](project_status.md) 和
[`../openapi.json`](../openapi.json) 为准。

## 建议阅读顺序

1. [`project_status.md`](project_status.md)：统一项目状态、验证基线与最新 Phase D/E/F 结论。
2. [`项目交接总览.md`](项目交接总览.md)：当前能力、架构、交付物和运行方式。
3. [`验证与复现.md`](验证与复现.md)：最新验证命令和证据文件。
4. [`requirement_mapping.md`](requirement_mapping.md)：课题要求到实现与证据。
5. [`acceptance_report.md`](acceptance_report.md)：当前验收口径与未达目标说明。
6. [`final_demo_script.md`](final_demo_script.md)：评审演示脚本。
7. [`badcase_analysis.md`](badcase_analysis.md)：风险类型与防护策略。
8. [`已知边界与后续事项.md`](已知边界与后续事项.md)：非目标、未达指标与后续优先级。
9. [`SchemaPack-Lineage交接.md`](SchemaPack-Lineage交接.md)：可信链路专项说明。
10. [`final_handoff_status.md`](final_handoff_status.md)：历史阶段与当前最终状态汇总。

## 其他权威文档

- [`../developer_guide.md`](../developer_guide.md)：开发、测试和扩展规范。
- [`../api_usage_examples.md`](../api_usage_examples.md)：API、CLI 与 SDK 示例。
- [`../package_spec.md`](../package_spec.md)：Package 1.1 契约。
- [`../lineage.md`](../lineage.md)：Lineage schema、API 与 evaluator。
- [`../external_uir_integration.md`](../external_uir_integration.md)：External UIR adapter/router/API 说明。
- [`../../reports`](../../reports)：脚本生成的评测证据。

## 当前验证摘要

| 项目 | 当前结果 |
| --- | --- |
| 仓库级验证 | `scripts\verify_all.py --check-openapi` 通过 |
| Backend pytest | 662 passed |
| Backend Ruff | clean |
| Frontend production build | successful |
| Frontend tests | 24 passed |
| OpenAPI | 63 paths |
| Regression gates | 8/8 passed（报告基线） |
| Real-world UIR inventory | 60 UIR，60 mapping gold，66 badcases |
| Real-world mapping | recall `0.6831896552`，package pass 60/60，badcase violations 0 |
| Non-procurement semantic sprint | 当前记录：50 samples，average recall `0.8063730159`，strict pass 47/50，required missing 2，review-required 16，package 50/50 |
| UIR Quality Gate | 60 total，12 pass，48 review，0 reject/unsupported |
| DeepSeek | provider smoke passed；report-only；auto accepted 0；secret leaks 0 |

## 当前不能宣称的事项

- 不能宣称生产盲测/影子集 recall 达到 0.85：当前无独立 production shadow/blind gold corpus；Phase I 50-sample latest average recall 为 `0.8063730159`，仍未达到 0.85。
- 不能把 Package Verification 等同于字段语义完全正确。
- 不能让 DeepSeek/LLM suggestion 自动接受 mapping、激活 catalog 或写入生产规则。
