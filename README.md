# SchemaPack Agent / Topic 5 Conversion Agent

## Topic 5 Current Contract

The public inline conversion contract is:

```text
UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config
```

`mapping_rules` is the preferred public API field. Legacy `mapping_template` is still accepted for backward compatibility when it carries the same content.

No-code SchemaPack demos:

```powershell
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
python scripts/validate_schema_pack.py schema_packs/examples/event_notice_doc

python scripts/run_topic5_inline_convert.py --request examples/topic5_inline/announcement_convert_request.json --out reports/topic5_inline_announcement_result.json --create-package
python scripts/run_topic5_inline_convert.py --request examples/topic5_inline/event_notice_convert_request.json --out reports/topic5_inline_event_notice_result.json --create-package
```

Runtime boundaries: production runtime starts from UIR or External UIR JSON. It does not parse raw PDF, Word, Excel, images, or scanned documents. The project does not claim production-grade blind recall 0.85. The current stronger mapping metric is assisted recall 0.861, while auto recall still needs improvement. LLM and Codex paths remain report-only or dry-run and do not write production rules.

本项目实现课题 5“数据格式标准化转换智能体”。系统接收归一后的结构化中间表示 UIR、目标 Schema/元数据模板/映射规则和内容组织参数，完成字段映射、字段重命名/合并/拆分、Schema 校验、面向 RAG 的分段打标摘要，并封装为人读 Markdown 与机读 JSON/chunks 的标准成果包。

输入为 UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config。

仓库内置的 policy_doc、meeting_doc、procurement_doc、contract_doc、general_doc 等 SchemaPack 只是示例配置与评测基准，用于证明系统支持多目标结构转换；它们不是系统能力边界。新增目标结构应优先通过新增 SchemaPack 配置完成，而不是修改后端代码。

SchemaPack 只是示例配置与评测基准，不是系统能力边界。

当前 GitHub 仓库：

```text
https://github.com/Yiliiiiiiii/NEU-Practical-training-Task-5
```

## 当前结论

项目主链路已经可运行、可复现，适合作为课题 5 的答辩展示与工程验收基础。当前新增 Topic 5 标准接口 `POST /api/v1/topic5/convert` 与 `POST /api/v1/topic5/convert/package`，可直接接收 inline UIR、目标 Schema、元数据模板、映射模板和内容组织参数；原有 Schema Router、Review/Knowledge、Lineage、Evaluation Center 和 DeepSeek suggestion 均作为增强能力保留。

强化阶段最新结论：课程规模 50-sample non-procurement split 的 dev/test/blind assisted mapping recall 已全部达到 0.85 以上，required missing = 0，badcase violations = 0，package verification = 50/50，overfit scan pass。最终综合门禁为 `conditional_pass`：mapping/package/overfit/operation/schema 已通过；DeepSeek 进行了 15 次 live report-only 调用但存在 unsafe suggestion，需要保持人工复核；Codex review 当前为 dry-run（未声明 live subagent）；content tag / summary quality 仍为 partial。不能宣称生产级盲测 recall，也不能宣称 LLM 或 Codex 自动写入生产规则。

## 核心链路

```text
标准 UIRDocument
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
-> Config Validation
-> Generic Candidate Extraction
-> Schema-aware Mapping
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

基本阶段一键复现命令：

```powershell
.\scripts\run_basic_stage_verification.ps1
```

强化阶段一键复现命令：

```powershell
.\scripts\run_strengthen_stage_verification.ps1
```

最新 basic-stage 已知结果：

- Backend pytest：`733 passed`
- Backend Ruff：`clean`
- Frontend production build：`successful`
- Frontend tests：`24 passed / 8 files`
- OpenAPI export：`63 paths` 写入 [`docs/openapi.json`](docs/openapi.json)
- Mapping quality gate：未通过，失败原因已记录在 [`docs/交接/evidence/basic_stage/mapping/mapping_quality_gate_result.md`](docs/交接/evidence/basic_stage/mapping/mapping_quality_gate_result.md)

## 评测证据

### Real-world corpus

- 数据集：60 个 UIR，覆盖 general、meeting、policy、procurement 四类真实样例。
- 全链路：60/60 import，60/60 task execution，60/60 package verification。
- Mapping：overall recall `0.6831896552`，validation pass 40/60，badcase violations 0。
- 证据文件：
  - [`reports/real_world_eval_report.json`](reports/real_world_eval_report.json)
  - [`reports/real_world_mapping_eval_report.json`](reports/real_world_mapping_eval_report.json)

### 非采购语义专项

当前 basic-stage 记录：

- Dataset size：50
- Auto mapping recall：`0.777`
- Assisted mapping recall：`0.807`
- Review-required rate：`0.057`
- Strict pass：48/50
- Required missing：0
- Review-required：24
- Package verification：50/50
- Badcase violations：0
- Split assisted recall：dev `0.798`、test `0.794`、blind `0.826`
- Quality gate：未通过，原因是 dev/test/blind assisted recall 均低于 `0.850`
- DeepSeek suggestion eval：report-only，suggestion_count 20，LLM auto accepted 0
- Codex review subagent：dry-run，reviewed_items 23，applied_count 0
- Content tag/summary quality 与 package consistency 已输出到 [`docs/交接/evidence/basic_stage/`](docs/交接/evidence/basic_stage/)

主要剩余缺口集中在 source-name exact recall、general_doc 长尾字段和少数 meeting/policy evidence alignment。详见 [`docs/交接/evidence/mapping_gap_analysis.md`](docs/交接/evidence/mapping_gap_analysis.md)。

当前 0.85 guarded sprint 使用 [`docs/交接/evidence/mapping_metric_baseline_snapshot.md`](docs/交接/evidence/mapping_metric_baseline_snapshot.md) 统一基线口径，并通过 [`examples/real_world/splits/mapping_split_manifest.json`](examples/real_world/splits/mapping_split_manifest.json)、`scripts/eval_mapping_splits.py`、`scripts/analyze_mapping_gaps.py`、`scripts/check_mapping_overfit_risk.py` 和 `scripts/check_mapping_quality_gate.py` 固化 dev/test/blind、gap analysis、防过拟合扫描和质量门禁。可提交版执行记录见 [`docs/交接/mapping_recall_085_guarded_sprint.md`](docs/交接/mapping_recall_085_guarded_sprint.md)。

当前 strengthen-stage 记录：

- Dataset size：50
- Auto mapping recall：`0.812`
- Assisted mapping recall：`0.861`
- Review-required rate：`0.109`
- Review-required：48
- Required missing：0
- Badcase violations：0
- Package verification：50/50
- Split assisted recall：dev `0.868`、test `0.868`、blind `0.884`
- Mapping quality gate：通过，见 [`docs/交接/evidence/strengthen_stage/mapping/mapping_quality_gate_result.md`](docs/交接/evidence/strengthen_stage/mapping/mapping_quality_gate_result.md)
- DeepSeek live report-only：15 requests，top1/top3 hit rate `1.0`，unsafe suggestions 0，secret leaks 0，LLM auto accepted 0
- Codex review dry-run：reviewed_items 48，applied_count 0，production_write_count 0，`can_claim_live_subagent_review = false`
- Final gate：`conditional_pass`，见 [`docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md`](docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md)

### Lineage 与下游契约

- Lineage report：status `passed`，field/chunk/artifact coverage 均为 1.0，broken edges 0，secret leaks 0，LLM auto accepted 0。
- Downstream contract：45/45 packages passed，0 failures。
- 证据文件：
  - [`reports/lineage_eval_report.json`](reports/lineage_eval_report.json)
  - [`reports/downstream_contract_eval_report.json`](reports/downstream_contract_eval_report.json)
  - [`reports/knowledge_loop_eval_report.md`](reports/knowledge_loop_eval_report.md)

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

## Topic 5 Phase 2 Mapping Benchmark

Phase 2 adds `eval/topic5_standard_uir` and a feature-flagged
`global_assignment` mapping mode. The latest gate evidence is written to
`reports/topic5_mapping_quality_gate_report.json` and
`reports/topic5_mapping_quality_gate_report.md`.

Current measured claim: Topic 5 benchmark-level auto mapping recall >= 0.85
within the declared standard UIR benchmark scope. This is not a production
shadow/blind claim unless `production_shadow_eval_report.json` is also
completed.

## Topic 5 Phase 3 SchemaPack Contract

A SchemaPack is the versioned external configuration contract for Topic 5. It declares the target schema, metadata template, mapping rules, content organization parameters, optional router hints, deterministic output assertions, examples, and badcases.

The canonical Topic 5 input consists of normalized UIR, target schema, metadata template, mapping rules, and content organization parameters. A SchemaPack packages these configuration assets for reusable execution.

Phase 3 adds strict `schema_pack.yaml` manifests, manifest-only asset loading, optional `output_assertions.yaml`, atomic `conversion_assertion_report.json` task evidence, positive/badcase evaluation, and a Phase 3 contract gate. Registered tasks can select a pack with `schema_pack_id`; inline requests can provide `output_assertions` directly.

Output assertions are optional. Existing Package 1.1 deliverables and legacy Topic 5 requests remain supported.

Conversion output assertions are deterministic SchemaPack-scoped checks over Topic 5 converted output. They complement target-schema validation but do not implement Topic 6 quality scoring, grading, semantic fidelity evaluation, or routing recommendations.

Phase 3 explicitly adds no quality score, no quality grade, no publication route, no semantic fidelity judgment, no LLM-as-Judge, and no Topic 11 retrieval optimization.

The project demonstrates benchmark-level automatic field mapping performance within the declared Topic 5 standard UIR benchmark scope. It does not claim arbitrary-schema production performance or production shadow/blind performance.

Latest Phase 3 repository verification on 2026-07-10: backend `885 passed`, Ruff clean, frontend production build successful, frontend `24 passed / 8 files`, and 65 OpenAPI paths exported. The Phase 3 contract gate passed all eight hard checks; documented per-schema precision warnings remain non-blocking in this phase.
