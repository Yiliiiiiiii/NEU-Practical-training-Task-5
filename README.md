# SchemaPack Agent

SchemaPack Agent 是课题 5「数据格式标准化转换智能体」的工程实现。它面向已经进入 UIR / External UIR JSON 的治理后文档，把上游结构化中间表示转换为受 Schema 和 Mapping 约束、可校验、可追溯、可下游消费的标准成果包。

当前 GitHub 仓库：

```text
https://github.com/Yiliiiiiiii/NEU-Practical-training-Task-5
```

## 当前结论

项目主链路已经可运行、可复现，适合作为课题 5 的答辩展示与工程验收基础。它覆盖 Schema 驱动转换、字段映射、结构化 JSON 与 Markdown 双形态输出、内容组织、Package 1.1、下游契约、人工复核、知识沉淀、Lineage 和安全受控的 LLM suggestion。

需要注意：当前不能宣称生产盲测 recall 达到 0.85。非采购语义专项已经提升到 average recall `0.8063730159`，但尚未达到 0.85；仓库中也没有独立 production shadow / blind gold corpus。

## 核心链路

```text
UIR / External UIR JSON
-> Adapter / Schema Router
-> Schema/Template Snapshot
-> Candidate Extraction
-> Mapping + Review / Knowledge
-> Transform + Canonical
-> Render + Content Organization
-> Validate
-> Manifest + ZIP
-> Verify + Consumer Contract
```

生产运行时边界从 UIR 或 External UIR JSON 输入开始，到标准成果包输出结束。PDF、Word、Excel、图片、扫描件和 OCR 不属于默认生产运行时能力；可选 raw upstream 脚本只作为离线入口。

## 已实现能力

- **Schema 驱动转换**：支持 schema/template 快照、字段候选抽取、确定性映射、字段转换、canonical model 和 strict validation。
- **字段映射与复核**：支持 exact、alias、regex、type、fuzzy 等策略，输出 confidence、source evidence、risk flags、review-required reason 和 badcase filter。
- **内容组织**：生成 chunks、摘要、关键词、content/management/quality tags、source links，并保留 table/list/code 等受保护内容结构。
- **双形态成果包**：输出机器可读 JSON / JSONL / reports，以及人读 Markdown；Package 包含 manifest、checksum 和 verifier report。
- **External UIR 兼容**：支持 block-list 与 section-tree 两类外部 UIR 方言，通过 adapter trace 和 schema router 转换到标准 UIR。
- **Review / Knowledge 治理**：支持 review records、candidate decisions、draft/active/archived knowledge packs、impact preview、rollback 和 snapshot protection。
- **Schema / Template Draft Lab**：支持字段发现、草案生成、风险检查、校验和显式导出；draft 不自动激活。
- **Evaluation Center**：包含 dataset、run、metric、scorecard、regression gate 和报告读取能力。
- **下游集成**：提供 Package 1.1、RAG/training/CSV consumer contracts、统一 CLI、Python SDK 和 adapter scaffold。
- **SchemaPack-Lineage**：记录 field、block、chunk、artifact 的可信链路，并提供后端 API 与前端面板。
- **DeepSeek / LLM suggestion**：默认关闭或 report-only，不自动接受 mapping，不激活 schema/template，不创建或执行 task。

## 最新验证

最近一次完整本地验证命令：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

已知结果：

- Backend pytest：`713 passed`
- Backend Ruff：`clean`
- Frontend production build：`successful`
- Frontend tests：`24 passed / 8 files`
- OpenAPI export：`63 paths` 写入 [`docs/openapi.json`](docs/openapi.json)

## 评测证据

### Real-world corpus

- 数据集：60 个 UIR，覆盖 general、meeting、policy、procurement 四类真实样例。
- 全链路：60/60 import，60/60 task execution，60/60 package verification。
- Mapping：overall recall `0.6831896552`，validation pass 40/60，badcase violations 0。
- 证据文件：
  - [`reports/real_world_eval_report.json`](reports/real_world_eval_report.json)
  - [`reports/real_world_mapping_eval_report.json`](reports/real_world_mapping_eval_report.json)

### 非采购语义专项

当前 Phase I 记录：

- Dataset size：50
- Average recall：`0.8063730159`
- Strict pass：47/50
- Required missing：2
- Review-required：16
- Package verification：50/50
- Badcase violations：0

主要剩余缺口集中在 `policy_doc` 的 issuer / publish_date 和少数长尾字段。详见 [`reports/phase_i_non_procurement_mapping_eval_report.json`](reports/phase_i_non_procurement_mapping_eval_report.json)。

### Lineage 与下游契约

- Lineage report：status `passed`，field/chunk/artifact coverage 均为 1.0，broken edges 0，secret leaks 0，LLM auto accepted 0。
- Downstream contract：45/45 packages passed，0 failures。
- 证据文件：
  - [`reports/lineage_eval_report.json`](reports/lineage_eval_report.json)
  - [`reports/downstream_contract_eval_report.json`](reports/downstream_contract_eval_report.json)

### 安全与治理

- UIR Quality Gate：60 total，12 pass，48 review，0 reject，0 unsupported。
- DeepSeek provider smoke：passed，suggestion_count 2，secret leaks 0。
- Review judge dry-run / safe apply：不自动 approve，不自动写入生产规则。
- Secret redaction audit：passed。

## 快速开始

### 一键启动本地开发环境

```powershell
.\scripts\start_dev.ps1
```

默认会启动：

- Backend API：`http://127.0.0.1:8000`
- Frontend workbench：`http://127.0.0.1:5173`

常用参数：

```powershell
.\scripts\start_dev.ps1 -NoBrowser
.\scripts\start_dev.ps1 -BackendPort 8000 -FrontendPort 5173
```

### 手动启动

后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm ci
npm run dev
```

### 容器启动

```powershell
docker compose up --build
```

容器化工作台默认地址：

```text
http://127.0.0.1:8080/
```

## 常用验证命令

仓库级验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

前端测试：

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

下游契约验证示例：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py `
  --packages-root reports\real_world_packages `
  --out reports\downstream_contract_eval_report.json `
  --markdown reports\downstream_contract_eval_report.md
```

## CLI 与 SDK

统一 CLI 可串联 External UIR 到 Package：

```powershell
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py convert-external --input external.json --out converted.json --route
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py import --input converted.json --out imported.json
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py create-task --doc-id DOC_ID --schema-id policy_doc --template-id policy_doc_base_v1 --out task.json
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py execute-task --task-id TASK_ID
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py download-package --task-id TASK_ID --out standard_package.zip
```

Python SDK 位于 [`sdk/python`](sdk/python)。Adapter scaffold 位于 [`templates/adapter_plugin`](templates/adapter_plugin)。

## 文档地图

- 当前状态入口：[`docs/交接/project_status.md`](docs/交接/project_status.md)
- 课题 5 需求映射：[`docs/交接/requirement_mapping.md`](docs/交接/requirement_mapping.md)
- 当前验收报告：[`docs/交接/acceptance_report.md`](docs/交接/acceptance_report.md)
- 最终演示脚本：[`docs/交接/final_demo_script.md`](docs/交接/final_demo_script.md)
- 工作台使用指南：[`docs/user_web_workbench_guide.md`](docs/user_web_workbench_guide.md)
- API 示例：[`docs/api_usage_examples.md`](docs/api_usage_examples.md)
- OpenAPI：[`docs/openapi.json`](docs/openapi.json)
- Package 规范：[`docs/package_spec.md`](docs/package_spec.md)
- External UIR 集成：[`docs/external_uir_integration.md`](docs/external_uir_integration.md)
- Lineage：[`docs/lineage.md`](docs/lineage.md)
- 部署说明：[`docs/deployment.md`](docs/deployment.md)

## 项目边界

- 不提供生产级 raw PDF / Word / Excel / image upload API。
- 不实现 OCR 或扫描件识别。
- 不包含完整 RAG / vector database。
- 不包含模型训练或 fine-tuning。
- 不实现企业级 SSO、tenant-aware authorization、TLS termination、managed secret storage、hosted credential provisioning 或企业级 model/provider monitoring。
- Package Verification 证明包结构、hash、required artifacts、parseability 和 traceability，不等同于每个字段语义都完全正确。
- Gold labels 与 badcases 是课程项目规模评测资产，不是企业级 benchmark。
