# SchemaPack Agent 最终交接状态

> 本文保留各阶段交接历史，并给出当前 `main@7fd38c77` 的统一最终状态。当前统一交接入口为 [`README.md`](README.md)。

## 集成仓库状态

- 当前分支：`main`。
- 当前基线 commit：`7fd38c77 feat: add phase D/E/F review safety reports`。
- 验证基线日期：2026-07-07。
- 统一验证命令：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`。
- Backend pytest：662 passed。
- Ruff：clean。
- Frontend production build：successful。
- Frontend tests：24 passed。
- OpenAPI export：63 paths written to [`docs/openapi.json`](../openapi.json)。
- 核心生产边界：UIR / External UIR JSON input 到 schema-driven package output。

当前处理链路：

```text
UIR / External UIR JSON -> Adapter / Schema Router -> Schema -> Mapping
-> Transform -> Canonical -> Render -> Content Organization -> Validate
-> Manifest -> ZIP -> Package Verification
```

## 已实现能力矩阵

| Area | 当前能力 | Evidence |
| --- | --- | --- |
| Schema/template catalogs | Catalog/governance 覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection，并支持 status transitions、referenced-version protection 和 immutable task snapshots。 | [`docs/developer_guide.md`](../developer_guide.md) |
| Document and task APIs | UIR import、document list/detail、task create/list/detail、explicit execution、report retrieval、package metadata 和 package download。 | [`docs/openapi.json`](../openapi.json) |
| Mapping and transform | 确定性 field candidate extraction、exact/alias/regex/type/fuzzy matching、evidence、confidence tiers、risk flags、review-required reasons、badcase filtering、projection、normalization、enum maps 和 defaults。 | [`reports/real_world_mapping_eval_report.md`](../../reports/real_world_mapping_eval_report.md) |
| Rendering and packages | Canonical model build、JSON/Markdown/chunk rendering、deterministic content organization、validation、manifest generation、ZIP creation 和 strict package verification。 | [`docs/package_spec.md`](../package_spec.md) |
| Human review and knowledge | Review approval/rejection、knowledge candidates、draft/active/archived packs、effective-template resolution、metrics、snapshot preservation 和 badcase protections。 | [`reports/review_knowledge_growth_report.json`](../../reports/review_knowledge_growth_report.json) |
| Optional LLM / DeepSeek | 默认关闭或 report-only；suggestions 仅 Review；bounded retries/timeouts、suggestion caps、redacted reports、provider warning handling。 | [`reports/deepseek_provider_smoke_report.json`](../../reports/deepseek_provider_smoke_report.json)、[`reports/deepseek_ablation_report.json`](../../reports/deepseek_ablation_report.json) |
| Frontend workbench | Import、task creation、execution、mapping evidence、validation、content organization controls、chunk preview、raw reports、review/knowledge actions、audit panel、External UIR、Draft Lab、Review Workbench、Evaluation Center、Lineage panel。 | [`docs/demo_workflow.md`](../demo_workflow.md) |
| Deployment | Backend/frontend Dockerfiles、Nginx proxy、Docker Compose volumes、startup database initialization、API-key auth option、audit logs 和 retention cleanup。 | [`docs/deployment.md`](../deployment.md) |
| External UIR and routing | Adapter registry、自动检测、block-list/section-tree、trace evidence、Router v2、API/UI 和 report-only DeepSeek suggestion。 | [`docs/external_uir_integration.md`](../external_uir_integration.md) |
| Draft and review governance | Schema/Template Draft Lab、Review Workbench、impact preview、batch safety、负知识、knowledge diff/impact/rollback。 | [`docs/交接/project_status.md`](project_status.md) |
| Evaluation Center | Dataset/run/metric/scorecard API、四分区前端、风险说明、报告读取和 8/8 regression gates。 | [`reports/evaluation_center`](../../reports/evaluation_center) |
| SchemaPack-Lineage | 字段/block/chunk/artifact lineage、五个查询 API、前端可信链路 panel、评测与四项 hard gates。 | [`docs/lineage.md`](../lineage.md) |
| Downstream consumption | Package 1.1、RAG/training/CSV contracts、ZIP/directory verifier 和 exporters。 | [`docs/package_spec.md`](../package_spec.md) |
| Integration ecosystem | Unified CLI、Python SDK 和 inert Adapter scaffold。Webhook 未实现。 | [`sdk/python/README.md`](../../sdk/python/README.md) |
| Optional raw upstream | 离线 Docling/Unstructured entry scripts，惰性依赖，输出 External UIR；无 OCR。 | [`examples/raw_upstream/README.md`](../../examples/raw_upstream/README.md) |

## API 与 Frontend Surface

- OpenAPI snapshot 在 [`docs/openapi.json`](../openapi.json) 中导出 63 个 paths。API inventory 以该文件和 [`docs/openapi_workflow.md`](../openapi_workflow.md) 为准。
- Frontend 是 React/Vite workbench，覆盖 demo path：sample UIR import、task creation、execution、report inspection、review decisions、knowledge activation、content organization settings、enriched chunk preview、package download、External UIR、Draft Lab、Review Workbench、Evaluation Center 和 Lineage。
- 本地 frontend development server 默认将 `/api` 代理到 `http://127.0.0.1:8000`；可用 `VITE_API_PROXY_TARGET` 覆盖本地验收目标。
- 容器 profile 通过 Nginx 提供 frontend，并在同一 local origin 下代理 backend API。

## Catalogs、Data 与 Packages

- Catalog/governance types 覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection。
- Seeded document families：`contract_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`procurement_doc`。
- Catalog baseline 包含 5 个 schemas 和 5 个 mapping templates。
- Real-world corpus：60 UIR（general 15、meeting 15、policy 20、procurement 10）、60 mapping gold、120 retrieval queries、66 badcases。
- Real-world execution evidence：60/60 imports、60/60 executions、60/60 verifier-passing packages。
- Real-world package outputs 位于 `reports/real_world_packages/`；production-like evaluator package outputs 位于 `reports/packages/`。
- Generated packages 包含 structured content、Markdown content、chunks、metadata、mapping/transform/validation/canonical/content-organization/verifier reports、manifest 和 checksums。

## 评估证据

- Unified verification：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 通过，记录 662 个 backend tests passed、Ruff clean、frontend production build successful 和 63 OpenAPI paths；frontend tests 24/24。
- Real-world pipeline：60/60 documents import、execute，并产生 verifier-passing packages。
- Real-world mapping：mapping recall `0.6831896552`，validation pass 40/60，package pass rate 1.000，badcase violations 0。
- Non-procurement evaluator：当前 50/50 package verification，average recall `0.8063730159`、review-required 16、required missing 2、strict pass 47/50、badcase violations 0；尚未达到 0.85。
- UIR Quality Gate：60 total，12 pass，48 review，0 reject，0 unsupported，allow-auto-accept 12。
- DeepSeek provider smoke：passed；suggestion_count 2；warning_count 0；secret leaks 0；auto accepted 0。
- Review judge dry-run/apply-safe：979 pending reviewed，suggest reject 26，suggest approve 0，applied approve/reject 0。
- External UIR：18/18 fixtures 的 selection、validation、trace 和 router 均通过，trace coverage 与 router top-1 accuracy 为 1.0，LLM auto accepted、badcase violations、secret leaks 均为 0。
- SchemaPack-Lineage：parse/field/chunk/artifact coverage 均为 1.0，broken edges、secret leaks、LLM auto accepted 均为 0；综合 regression gates 8/8。

## 复现命令

仓库级验证：

```powershell
git branch --show-current
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

前端测试：

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

启动本地开发环境：

```powershell
.\scripts\start_dev.ps1
```

手动启动 backend：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

重新生成 real-world、non-procurement 与 Phase D/E/F reports：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
backend\.venv\Scripts\python.exe scripts\eval_uir_quality_gate.py
backend\.venv\Scripts\python.exe scripts\eval_deepseek_smoke.py
```

## 已知边界

- 生产输入是 UIR 或 External UIR JSON。Raw PDF、Word、Excel、image、scanned document 和 OCR parsing 不是生产 runtime features。
- Real-world source collection 与 UIR-building scripts 是离线 dataset tooling，不是 API-bound ingestion services。
- 非采购 real-world samples 可以产生 verifier-passing packages，但 strict field validity 仍需继续改善。
- Retrieval evaluation 是 deterministic chunk-ranking evidence，不是完整 RAG service。
- Optional LLM/DeepSeek fallback 是 review-only suggestion path，不会在没有 human/governed review 的情况下激活 mappings。
- 项目不实现 SSO、tenant-aware authorization、TLS termination、hosted credential provisioning、enterprise model monitoring、full quality scoring、model training 或 autonomous production rule activation。
- 当前无独立 production shadow/blind gold corpus，不能宣称 0.85。

## 生产化方向

- Multi-tenant 使用前，应增加 authenticated operator review screens、role-aware workflows 和 tenant-aware authorization。
- 生产启用 network LLM fallback 前，应增加 SSO/TLS integration、hosted credential management、model/provider evaluation 和 monitoring。
- 持续通过 gold-label、badcase、review 和 snapshot-preservation checks 扩展 regression datasets。
- 建立独立 production shadow/blind corpus 后再评估 0.85。
- 如 downstream consumers 需要强类型集成，可发布 generated API clients。
- 继续诚实区分 verifier-passing packages 与 strict field-valid claims。

## 历史阶段摘要

### 2026-07-03 三项深化交接

- Real-world UIR 扩展为 45 documents（general 10、meeting 10、policy 15、procurement 10）。
- 非采购 early gate：average recall `0.5677551020`，review-required 69，required missing 6，badcase violations 0，package verification 35/35。
- Knowledge Pack：draft 无影响；active 影响 future task；old snapshot unchanged；rejected/badcase activation 为 0。
- Runtime 边界仍是 `UIR input -> schema-driven package output`；没有加入 OCR、完整 RAG、模型训练或 LLM 自动激活规则。

### 2026-07-05 三项质量打磨

- Strict validation：非采购 strict pass `13/35 -> 17/35`，required missing `6 -> 4`，review-required `69 -> 59`，35/35 packages，badcase violations 0。
- Adapter：fixtures `4 -> 18`，覆盖正常、表格、嵌套、缺字段、噪声和 badcase；selection、validation、trace、router 均达 1.0，LLM auto accepted 0。
- Evaluation Center：新增 summary/cards/warnings scorecard、四分区前端、文字状态、固定语义边界说明、静态 scorecard 与 regression gate Markdown 报告。

### 2026-07-06 SchemaPack-Lineage 交接

- 新增 `backend/app/schemas/lineage.py`、graph/query services 与五个只读 API。
- Task 默认启用 lineage、默认 non-strict；失败 warning 与主转换结果解耦。
- External adapter trace、mapping/review/knowledge、canonical/chunk、manifest/consumer contract 已形成稳定关联。
- 前端新增“可信链路”面板与组件测试。
- 新增 lineage evaluator、demo report builder 和 Evaluation Center 四项 hard gates。

### 2026-07-07 Phase C / Phase D / E / F 交接

- Phase C sprint4：50 samples，average recall `0.7165476190`，strict pass 31/50，required missing 4，review-required 22，package 50/50，badcase violations 0。
- Phase D：50 samples，average recall `0.7426031746`，strict pass 39/50，required missing 2，review-required 21，package 50/50，badcase violations 0。
- 当前非采购语义评测记录：50 samples，average recall `0.8063730159`，strict pass 47/50，required missing 2，review-required 16，package 50/50，badcase violations 0。
- UIR Quality Gate：60 total，12 pass，48 review，0 reject/unsupported。
- DeepSeek smoke：provider passed，report-only not applied，auto accepted 0，secret leaks 0。
- Review judge：dry-run/apply-safe 均未自动写入 approve/reject。
- 0.85：未达成也未宣称；blind/shadow reports 为 `not_run`，原因是缺少独立 gold corpus。
