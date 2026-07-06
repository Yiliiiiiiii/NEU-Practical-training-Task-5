# SchemaPack Agent

## 当前状态

当前已验证基线（2026-07-05）：513 个后端测试与 18 个前端测试通过，Ruff clean，前端生产构建成功，并导出 58 个 OpenAPI paths。

SchemaPack Agent 是一个以 UIR 为起点的系统，用于把规范化文档结构转换为受 Schema 约束、经过 Verifier 检查的输出 Package。已验证的生产边界从 UIR 输入开始，到 Package ZIP 输出结束。

## 已实现能力

当前处理链路为：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render
-> Content Organization -> Validate -> Manifest -> ZIP -> Package Verification
```

- Catalog 治理：覆盖 schemas、schema versions、mapping templates、template versions，以及 effective knowledge-pack 选择。
- 已内置文档 Catalog 家族：`contract_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`procurement_doc`。
- UIR 文档导入、Task 创建/列表/详情、显式执行、报告读取、Package 元数据和 Package 下载 API。
- 确定性 Mapping：支持 exact、alias、regex、type、fuzzy 策略；输出 confidence tier、source evidence、risk flags、review-required reason、badcase filter，以及可选的仅 Review LLM suggestion。
- Transform、Canonical Model、结构化 JSON、Markdown、Chunk 渲染、Validation、Manifest 生成、Package ZIP 创建和严格 Package Verification。
- Human Review 与 Knowledge-loop：支持待审 Review、candidate decision、draft/active/archived knowledge packs、effective template resolution、metrics、snapshot preservation 和 badcase protection。
- React/Vite 工作台：支持导入、创建 Task、执行、查看 Mapping evidence、Validation、Content Organization、Knowledge actions、原始报告和 Package 下载。
- 本地容器部署：包含 backend/frontend Dockerfile、Nginx API proxy、持久卷、启动时数据库初始化、可选 API-key auth、audit logs 和 retention cleanup。
- 下游 Package smoke check 与 training-corpus JSONL 导出工具。
- External UIR 兼容层：支持 block-list 与 section-tree 两种上游 UIR JSON 方言，转换为标准 `UIRDocument`，并通过 Schema Router 推荐到现有 5 类 schema/template。
- Schema/Template Draft Lab、Review Workbench、Knowledge Pack diff/impact/rollback 与 Evaluation Center。
- 版本化 consumer contracts、统一 CLI、Python SDK、Adapter scaffold，以及可选离线 Docling/Unstructured 上游。

## 已验证证据

- 统一验证记录：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 产生 513 个后端测试通过、Ruff clean、前端生产构建成功，并把 58 个 OpenAPI paths 导出到 [`docs/openapi.json`](docs/openapi.json)；前端独立测试为 18/18。API 清单请以 [`docs/openapi_workflow.md`](docs/openapi_workflow.md) 和 [`docs/openapi.json`](docs/openapi.json) 为准。
- Real-world pipeline 记录 45/45 文档导入、45/45 Task 执行完成、45/45 Package verification 通过。见 [`reports/real_world_eval_report.md`](reports/real_world_eval_report.md) 和 [`reports/real_world_eval_report.json`](reports/real_world_eval_report.json)。
- Real-world mapping 报告记录 package pass rate 为 1.000，mapping recall 为 `0.6023391812865497`，validation pass 27/45，badcase violations 为 0。见 [`reports/real_world_mapping_eval_report.md`](reports/real_world_mapping_eval_report.md) 和 [`reports/real_world_mapping_eval_report.json`](reports/real_world_mapping_eval_report.json)。
- Procurement comparison 记录 `procurement_doc` required coverage 为 1.000，而通用 `general_doc` schema 为 0.333。见 [`reports/procurement_doc_eval_report.md`](reports/procurement_doc_eval_report.md) 和 [`reports/procurement_doc_eval_report.json`](reports/procurement_doc_eval_report.json)。
- 32-query retrieval 报告记录 `Recall@3 = 1.000`。见 [`reports/content_organization_retrieval_eval.md`](reports/content_organization_retrieval_eval.md) 和 [`reports/content_organization_retrieval_eval.json`](reports/content_organization_retrieval_eval.json)。
- 两个 Knowledge-loop 报告均保持 snapshot preservation，并记录 badcase violations 为 0。见 [`reports/real_world_knowledge_loop_report.md`](reports/real_world_knowledge_loop_report.md)、[`reports/real_world_knowledge_loop_report.json`](reports/real_world_knowledge_loop_report.json)、[`reports/knowledge_loop_eval_report.md`](reports/knowledge_loop_eval_report.md) 和 [`reports/knowledge_loop_eval_report.json`](reports/knowledge_loop_eval_report.json)。
- LLM fallback 报告记录 `auto_accepted_count = 0`、secret redaction 成功，并产生两个 review-required suggestions。见 [`reports/llm_fallback_eval_report.md`](reports/llm_fallback_eval_report.md) 和 [`reports/llm_fallback_eval_report.json`](reports/llm_fallback_eval_report.json)。
- External UIR adapter 报告记录 18/18 curated fixtures 转换和 UIR validation 通过、trace coverage 与 schema router top-1 accuracy 均为 1.0、LLM auto accepted 与 secret leaks 均为 0。见 [`docs/external_uir_integration.md`](docs/external_uir_integration.md)、[`reports/external_uir_adapter_eval_report.md`](reports/external_uir_adapter_eval_report.md) 和 [`reports/external_uir_adapter_eval_report.json`](reports/external_uir_adapter_eval_report.json)。
- 非采购 strict validation 工作有独立证据：[`reports/strict_validation_improvement_report.md`](reports/strict_validation_improvement_report.md) 和 [`reports/non_procurement_mapping_eval_report.md`](reports/non_procurement_mapping_eval_report.md)。最新 evaluator 记录 35/35 packages 通过、average recall `0.6096598639455783`、review-required 59、required missing 4、strict pass 17/35、badcase violations 0。

## 快速开始

从仓库根目录运行统一验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

一键启动本地开发环境：

```powershell
.\scripts\start_dev.ps1
```

该脚本会打开两个 PowerShell 窗口：一个运行 backend API，另一个运行 frontend workbench，并自动打开 `http://127.0.0.1:5173/`。停止时关闭两个新窗口，或分别按 `Ctrl+C`。

常用选项：

```powershell
.\scripts\start_dev.ps1 -NoBrowser
.\scripts\start_dev.ps1 -BackendPort 8000 -FrontendPort 5173
```

手动启动后端的备用方式：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个终端启动前端：

```powershell
cd frontend
npm ci
npm run dev
```

打开本地工作台：

```text
http://127.0.0.1:5173/
```

容器方式：

```powershell
docker compose up --build
```

打开容器化工作台：

```text
http://127.0.0.1:8080/
```

## 统一验证

权威验证命令为：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

2026-07-06 已验证基线：

- Backend pytest：567 passed。
- Ruff：clean。
- Frontend tests：24 passed。
- Frontend production build：successful。
- OpenAPI export：63 paths 写入 [`docs/openapi.json`](docs/openapi.json)。

## 文档地图

- 当前实施状态与文档口径：[`docs/project_status.md`](docs/project_status.md)、[`docs/README.md`](docs/README.md)
- 网页工作台新手使用教程：[`docs/user_web_workbench_guide.md`](docs/user_web_workbench_guide.md)
- 当前交接入口：[`docs/交接/README.md`](docs/交接/README.md)
- 历史交接汇总：[`docs/final_handoff_status.md`](docs/final_handoff_status.md)
- Demo workflow：[`docs/demo_workflow.md`](docs/demo_workflow.md)
- Final demo script：[`docs/final_demo_script.md`](docs/final_demo_script.md)
- Developer guide：[`docs/developer_guide.md`](docs/developer_guide.md)
- Deployment guide：[`docs/deployment.md`](docs/deployment.md)
- API workflow 与 snapshot：[`docs/openapi_workflow.md`](docs/openapi_workflow.md)、[`docs/openapi.json`](docs/openapi.json)
- API examples：[`docs/api_usage_examples.md`](docs/api_usage_examples.md)
- Requirement mapping：[`docs/requirement_mapping.md`](docs/requirement_mapping.md)
- Badcase analysis：[`docs/badcase_analysis.md`](docs/badcase_analysis.md)
- Package specification：[`docs/package_spec.md`](docs/package_spec.md)
- Real-world UIR dataset guide：[`docs/real_world_uir_dataset.md`](docs/real_world_uir_dataset.md)
- Real-world knowledge-loop guide：[`docs/real_world_knowledge_loop.md`](docs/real_world_knowledge_loop.md)
- 非采购 recall 计划与验收证据：[`docs/non_procurement_mapping_improvement_plan.md`](docs/non_procurement_mapping_improvement_plan.md)、[`reports/non_procurement_acceptance_report.md`](reports/non_procurement_acceptance_report.md)

## 生产边界

- 生产输入是 UIR。Raw PDF、Word、Excel、image、scan 和 OCR parsing 不在生产运行时边界内。
- Real-world source collection 与 UIR-building scripts 是离线数据集工具，不是运行时 ingestion service。
- 非采购 real-world 样本可以产生 verifier-passing packages，但仍需 Review，不能声明 strict field validity。
- 可选 LLM fallback 仅作为 suggestion source。它不会自动接受 mapping；provider failure 会变成 warning/review item，除非显式请求 strict failure。
- Retrieval 与 Mapping evaluations 是确定性项目证据，不是完整 RAG service、model-training pipeline、hosted credential service、SSO/TLS stack、tenant system 或 enterprise model-monitoring platform。

## 五项深化证据

- Real-world UIR dataset：45 个 public-source documents；45/45 import、execution 和 package verification。
- 非采购 mapping：35 个 general/meeting/policy documents；average recall `0.6097`，strict pass 17/35，review-required 59，required missing 4，badcase violations 0，package verification 35/35。
- Content organization：5 种 chunk strategies，以及 summary-faithfulness 和 tag-quality reports。
- Knowledge growth：可复现的 review -> candidate -> draft -> active loop；review-required 5 -> 4，old snapshot unchanged，badcase/reject activation 0。
- Downstream consumption：structured CSV 和 RAG JSONL exporters；45/45 packages 通过 consumer contract。

```powershell
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
backend\.venv\Scripts\python.exe scripts\eval_content_strategy_comparison.py
backend\.venv\Scripts\python.exe scripts\eval_summary_faithfulness.py
backend\.venv\Scripts\python.exe scripts\eval_content_tag_quality.py
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

## Consumer Contracts 与集成工具

`contracts/` 提供 RAG corpus、training corpus、structured CSV 与 package
`1.1` 四份版本化契约。统一 verifier 可校验单个 ZIP 或递归批量校验：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_consumer_contract.py `
  --package reports\integration\standard_package.zip `
  --contract contracts\rag_corpus_contract_v1.json `
  --out reports\consumer_contract_report.json `
  --markdown reports\consumer_contract_report.md
```

统一 CLI 可串联 External UIR 到 Package：

```powershell
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py convert-external --input external.json --out converted.json --route
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py import --input converted.json --out imported.json
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py create-task --doc-id DOC_ID --schema-id policy_doc --template-id policy_doc_base_v1 --out task.json
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py execute-task --task-id TASK_ID
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py download-package --task-id TASK_ID --out standard_package.zip
```

Python SDK 位于 [`sdk/python`](sdk/python)，Adapter scaffold 位于
[`templates/adapter_plugin`](templates/adapter_plugin)。脚手架不会自动注册或执行
adapter；生成代码必须补充 fixtures、badcases 与评测后再人工接入 registry。
## External UIR API/UI MVP

The project includes an External UIR Adapter path for upstream systems that
already emit External UIR JSON. The flow is intentionally manual:

```text
External UIR JSON -> convert & route -> preview -> import standard UIR -> create task -> execute existing pipeline
```

Backend endpoints:

- `POST /api/v1/external-uir/convert`
- `POST /api/v1/external-uir/import`
- `POST /api/v1/external-uir/create-task`

The frontend workbench includes an `External UIR Adapter` panel for paste/upload,
conversion preview, import, and task creation. DeepSeek assistance is disabled
by default and only records adapter suggestions; it does not auto-accept
mappings, activate schemas/templates, create tasks, or execute tasks.

## Optional Raw Document Upstream

Phase 8 adds offline, opt-in entry scripts for Docling and Unstructured. The
providers are imported lazily and are not part of the backend runtime
requirements:

```powershell
backend\.venv\Scripts\python.exe scripts\upstream_docling_to_external_uir.py `
  examples\raw_upstream\sample_policy.pdf `
  --out examples\raw_upstream\sample_policy_external_uir.json `
  --report reports\raw_upstream\sample_policy_report.json
```

If an optional provider is absent, supported text-layer PDF, DOCX, and HTML
inputs can use the existing deterministic extractors. Scanned PDFs remain
unsupported: no OCR is installed or invoked. Output is block-list External UIR
and must continue through Convert -> Preview -> Import -> Create Task.

## SchemaPack-Lineage

Task execution now emits field/block/chunk/artifact trace graphs by default
(`enable_lineage=true`, `strict_lineage=false`). The frontend “可信链路” panel
queries the full graph or bounded field/chunk/artifact subgraphs and displays
accepted, review-required and badcase-blocked states with explicit text labels.

Lineage is report-only and never changes mapping or package results. The MVP
keeps `lineage_graph.json` and `lineage_summary.json` as task reports instead of
ZIP members, avoiding manifest checksum self-reference while preserving the
Package 1.1 contract. See [docs/lineage.md](docs/lineage.md).

Generated evidence:

- `reports/lineage_eval_report.json` / `.md`
- `reports/lineage_demo_report.json` / `.md`
- Evaluation Center lineage gates: parse `1.0`, broken edges `0`, secret leaks
  `0`, field coverage `>= 0.90`
