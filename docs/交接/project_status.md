# SchemaPack Agent 当前实施状态

> 最后同步：2026-07-06。本文档是项目能力、验证基线和边界的统一状态入口。
> 历史需求、规格和实施计划保留当时语境；发生冲突时，以本文档、
> [`README.md`](README.md) 和
> [`../openapi.json`](../openapi.json) 为准。

## 验证基线

- Backend：567 tests passed。
- Static checks：Ruff clean。
- Frontend：24 tests passed，production build successful。
- API：63 OpenAPI paths。
- Regression gates：8/8 passed。
- Current metrics：badcase violations 0、LLM auto accepted 0、package
  verification rate 1.0、adapter trace coverage 1.0、downstream contract pass
  rate 1.0、lineage parse pass 1.0、lineage field coverage 1.0、
  lineage broken edges 0、lineage secret leaks 0。

权威复现命令：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

## 已实施能力

| 阶段 | 状态 | 当前实现 |
| --- | --- | --- |
| Phase 1 | 已完成 | 可插拔 External UIR adapter registry、能力声明、自动检测与 trace evidence |
| Phase 2 | 已完成 | Schema Router v2、多候选、证据、风险标记与人工确认 |
| Phase 3 | 已完成 | Schema/Template Draft Generator、字段发现、风险检查、校验与导出 |
| Phase 4 | 已完成 | Review Workbench、影响预览、批量安全、人审负知识、知识包 diff/impact/rollback |
| Phase 5 | 已完成 | Evaluation Center、dataset/run/metric/scorecard API、回归门禁 |
| Phase 6 | 已完成 | Package 1.1、RAG/training/CSV consumer contracts 与统一 verifier |
| Phase 7 | 已完成（Webhook 除外） | 统一 CLI、Python SDK、Adapter scaffold；Webhook 是可选项，未实现 |
| Phase 8 | 已完成 | 可选 Docling/Unstructured 离线上游，惰性依赖，输出 External UIR |
| SchemaPack-Lineage | 已完成（MVP） | 字段/block/chunk/artifact lineage、五个查询 API、前端 panel、评测与回归门 |

核心生产链路保持不变：

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical -> Render -> Content Organization
-> Validate -> Manifest -> ZIP -> Verify
```

## 评测证据

- Real-world UIR：45 documents；45/45 import、execute、package verify。
- Real-world mapping：recall `0.6023391812865497`，package pass 45/45，
  badcase violations 0，validation pass 27/45。
- Non-procurement：35 documents；average recall `0.6096598639455783`，
  package verify 35/35，strict pass 17/35，review-required 59，
  required missing 4，badcase violations 0。
- Adapter Framework：2 adapters、18 fixtures，selection/validation/router/trace
  coverage 均为 1.0，LLM auto accepted 0。
- External UIR API：18/18 convert、import、UIR validation 通过，secret leaks 0。
- Downstream consumer contract：45/45 packages passed。

## 明确边界

- 生产 API 从 UIR 或 External UIR JSON 开始，不提供 raw-document upload API。
- Docling/Unstructured 仅是离线可选入口，不进入 backend 默认依赖。
- 扫描件 OCR 未实现；无可用文本层的 PDF 返回
  `unsupported_scanned_pdf`。
- DeepSeek 和其他 LLM 仅能提供 report-only suggestion，不自动接受 mapping、
  激活 schema/template、创建或执行 task。
- 未实现 Webhook、SSO、tenant-aware authorization、TLS termination、managed
  secret storage、hosted credential provisioning、完整 RAG、模型训练或企业级
  model/provider monitoring。

## 文档口径

- 当前使用文档：`README.md`、`docs/交接/`、`docs/` 根目录指南、本状态页、
  SDK/模板/示例 README。
- 历史文档：`docs/guildline/`、`docs/nbl/`、`docs/superpowers/` 下带日期的
  requirements/specs/plans；保留原始设计，不作为当前状态声明。
- 生成报告：`reports/*.md` 与对应 JSON 是特定评测时点的证据，不应手工改写
  指标；需要更新时运行其生成脚本。

## SchemaPack-Lineage 状态（2026-07-06）

- 已实现 Lineage 1.0 schema、graph builder、field/chunk/artifact query service。
- Task 默认生成 `lineage_graph.json` 与 `lineage_summary.json`；non-strict
  失败不破坏原 task。
- External UIR create-task 会保留 adapter report；Review、Knowledge、
  canonical、chunk、manifest 与 consumer contract 均可进入图。
- 前端已提供 summary cards、三类查询、分层 ledger、节点详情以及
  review-required/blocked 显式状态。
- `eval_lineage_graph.py` 生成 JSON/Markdown，并把四项 lineage hard gates
  合并进 Evaluation Center；当前回归报告为 8/8。
- 真实 demo graph 的 field/chunk/artifact coverage 均为 `1.0`，broken edge、
  secret leak、LLM auto-accept 均为 `0`。
- MVP lineage 文件只作为 task reports，不进入 ZIP；这是为避免 manifest hash
  自引用并保持 Package 1.1 contract 不变。
