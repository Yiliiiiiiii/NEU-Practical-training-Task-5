# SchemaPack Agent 最终交接状态

> 本文保留各阶段交接历史。当前统一交接入口为
> [`README.md`](README.md)。

## 集成仓库状态

- 当前质量打磨分支：`codex/quality-polish`。
- 验证基线日期：2026-07-06。
- 统一验证命令：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`。
- Backend pytest: 567 passed.
- Ruff: clean.
- Frontend production build: successful.
- Frontend tests: 24 passed.
- OpenAPI export: 63 paths written to [`docs/openapi.json`](../openapi.json).
- 核心生产边界：UIR input 到 schema-driven package output。

当前处理链路：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render
-> Content Organization -> Validate -> Manifest -> ZIP -> Package Verification
```

## 已实现能力矩阵

| Area | 当前能力 | Evidence |
| --- | --- | --- |
| Schema/template catalogs | Catalog/governance 覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection，并支持 status transitions、referenced-version protection 和 immutable task snapshots。 | [`docs/developer_guide.md`](../developer_guide.md) |
| Document and task APIs | UIR import、document list/detail、task create/list/detail、explicit execution、report retrieval、package metadata 和 package download。 | [`docs/openapi.json`](../openapi.json) |
| Mapping and transform | 确定性 field candidate extraction、exact/alias/regex/type/fuzzy matching、evidence、confidence tiers、risk flags、review-required reasons、badcase filtering、projection、normalization、enum maps 和 defaults。 | [`reports/real_world_mapping_eval_report.md`](../../reports/real_world_mapping_eval_report.md) |
| Rendering and packages | Canonical model build、JSON/Markdown/chunk rendering、deterministic content organization、validation、manifest generation、ZIP creation 和 strict package verification。 | [`docs/package_spec.md`](../package_spec.md) |
| Human review and knowledge | Review approval/rejection、knowledge candidates、draft/active/archived packs、effective-template resolution、metrics、snapshot preservation 和 badcase protections。 | [`reports/knowledge_loop_eval_report.md`](../../reports/knowledge_loop_eval_report.md) |
| Optional LLM fallback | 默认关闭，支持 deterministic stub 与 OpenAI-compatible modes；suggestions 仅 Review；具备 bounded retries/timeouts、suggestion caps、redacted reports、provider warning handling 和 strict-mode override。 | [`reports/llm_fallback_eval_report.md`](../../reports/llm_fallback_eval_report.md) |
| Frontend workbench | Import、task creation、execution、mapping evidence、validation、content organization controls、chunk preview、raw reports、review/knowledge actions、audit panel 和 package download。 | [`docs/demo_workflow.md`](../demo_workflow.md) |
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
- Frontend 是 React/Vite workbench，覆盖 demo path：sample UIR import、task creation、execution、report inspection、review decisions、knowledge activation、content organization settings、enriched chunk preview 和 package download。
- 本地 frontend development server 默认将 `/api` 代理到
  `http://127.0.0.1:8000`；可用 `VITE_API_PROXY_TARGET` 覆盖本地验收目标。
- 容器 profile 通过 Nginx 提供 frontend，并在同一 local origin 下代理 backend API。

## Catalogs、Data 与 Packages

- Catalog/governance types 已覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection。
- Seeded document families：`contract_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`procurement_doc`。
- Catalog baseline 包含 5 个 schemas 和 5 个 mapping templates。
- Real-world UIR dataset 已扩展到 45 documents。
- Real-world execution evidence 记录 45/45 imports、45/45 executions、45/45 verifier-passing packages。
- Real-world package outputs 位于 `reports/real_world_packages/`；production-like evaluator package outputs 位于 `reports/packages/`。
- Generated packages 包含 structured content、Markdown content、chunks、metadata、mapping/transform/validation/canonical/content-organization/verifier reports、manifest 和 checksums。

## 评估证据

- Unified verification：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 通过，记录 567 个 backend tests passed、Ruff clean、frontend production build successful 和 63 OpenAPI paths；frontend tests 24/24。
- Real-world pipeline：45/45 documents import、execute，并产生 verifier-passing packages。
- Real-world mapping：mapping recall `0.6023391812865497`，validation pass 27/45，package pass rate 1.000，badcase violations 0。
- 非采购 API-backed evaluator：35/35 package verification，average recall `0.6096598639455783`、review-required 59、required missing 4、strict pass 17/35、badcase violations 0。
- External UIR：18/18 fixtures 的 selection、validation、trace 和 router 均通过，trace coverage 与 router top-1 accuracy 为 1.0，LLM auto accepted、badcase violations、secret leaks 均为 0。
- Procurement comparison、content retrieval、knowledge-loop、LLM fallback 等报告仍作为辅助证据保留在 `reports/`。
- SchemaPack-Lineage：parse/field/chunk/artifact coverage 均为 1.0，
  broken edges、secret leaks、LLM auto accepted 均为 0；综合 regression
  gates 8/8。

## 复现命令

仓库级验证：

```powershell
git branch --show-current
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
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

另一个终端重新生成 real-world 与 evaluation reports：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
```

## 已知边界

- 生产输入是 UIR。Raw PDF、Word、Excel、image、scanned document 和 OCR parsing 不是生产 runtime features。
- Real-world source collection 与 UIR-building scripts 是离线 dataset tooling，不是 API-bound ingestion services。
- 非采购 real-world samples 可以产生 verifier-passing packages，但 strict field validity 仍需继续改善。
- Retrieval evaluation 是 deterministic chunk-ranking evidence，不是完整 RAG service。
- Optional LLM fallback 是 review-only suggestion path，不会在没有 human/governed review 的情况下激活 mappings。
- 项目不实现 SSO、tenant-aware authorization、TLS termination、hosted credential provisioning、enterprise model monitoring、full quality scoring、model training 或 autonomous production rule activation。

## 生产化方向

- Multi-tenant 使用前，应增加 authenticated operator review screens、role-aware workflows 和 tenant-aware authorization。
- 生产启用 network LLM fallback 前，应增加 SSO/TLS integration、hosted credential management、model/provider evaluation 和 monitoring。
- 持续通过 gold-label、badcase、review 和 snapshot-preservation checks 扩展 regression datasets。
- 如 downstream consumers 需要强类型集成，可发布 generated API clients。
- 继续诚实区分 verifier-passing packages 与 strict field-valid claims。

## 2026-07-03 三项深化交接

- Real-world UIR：45 documents（general 10、meeting 10、policy 15、procurement 10）。
- 非采购：average recall `0.5677551020408163`，review-required 69，required missing 6，badcase violations 0，package verification 35/35。
- Knowledge Pack：draft 无影响；active 影响 future task；old snapshot unchanged；rejected/badcase activation 为 0。
- Runtime 边界仍是 `UIR input -> schema-driven package output`；没有加入 OCR、完整 RAG、模型训练或 LLM 自动激活规则。

## 2026-07-05 三项质量打磨

- Strict validation：非采购 strict pass `13/35 -> 17/35`，required missing
  `6 -> 4`，review-required `69 -> 59`，35/35 packages，badcase violations 0。
- Adapter：fixtures `4 -> 18`，覆盖正常、表格、嵌套、缺字段、噪声和 badcase；
  selection、validation、trace、router 均达 1.0，LLM auto accepted 0。
- Evaluation Center：新增 summary/cards/warnings scorecard、四分区前端、文字状态、
  固定语义边界说明、静态 scorecard 与 regression gate Markdown 报告。
- 未增加 OCR、完整 RAG、模型训练、LLM 自动激活或 raw-document production API。

## 2026-07-03 External UIR Adapter 交接

- 新增 External UIR 兼容层，支持 block-list 与 section-tree 两种外部 UIR JSON 方言。
- Adapter 输出当前项目标准 `UIRDocument`，不放宽主 UIR schema；外部路径证据保存在 adapter report 与 block `attributes.external_path`。
- 新增 Schema Router，覆盖 `contract_doc`、`policy_doc`、`meeting_doc`、`general_doc`、`procurement_doc` 五类现有 schema/template。
- CLI 闭环：`scripts/convert_external_uir.py` 输出标准 UIR、adapter report 和可选 route report。
- 批量评测：`scripts/eval_external_uir_adapter.py` 在 4 个 curated fixtures 上记录 adapter pass 4/4、UIR validation pass 4/4、router correct 4/4、top-1 accuracy 1.0、LLM auto accepted 0、badcase violations 0。
- 后续阶段已新增 External UIR API/UI、Schema/Template Draft Generator 与默认关闭的 report-only DeepSeek suggestion；本段保留 CLI 首次交接的历史顺序。
## External UIR API/UI MVP Status

Implemented:

- Backend routes: `/api/v1/external-uir/convert`,
  `/api/v1/external-uir/import`, and `/api/v1/external-uir/create-task`.
- Manual-confirmation frontend panel for External UIR conversion, preview,
  import, and task creation.
- DeepSeek configuration placeholders and report-only suggestion service.
- Mock-tested safety boundaries: disabled-by-default behavior, strict JSON
  safety flags, evidence requirement, and secret redaction.
- API-backed evaluator script at `scripts/eval_external_uir_api.py`.

Safety posture:

- No raw-document parsing or OCR was added to the production runtime; optional
  offline Docling/Unstructured entry scripts are separate.
- No DeepSeek suggestion is auto-accepted as mapping.
- No schema/template is activated by External UIR or DeepSeek flow.
- Real DeepSeek keys must only be placed in local `.env`.

## 2026-07-04 Optional Raw Document Upstream

- Added offline Docling and Unstructured entry scripts backed by a shared,
  provider-neutral External UIR mapper.
- Both providers are lazy optional imports and remain absent from backend
  runtime requirements.
- Existing deterministic PDF/DOCX/HTML extractors provide an explicit fallback;
  textless scanned PDFs are rejected and OCR remains out of scope.
- Added a visually checked sample PDF, generated block-list External UIR, and a
  provenance/safety report with zero auto-imports, task creations, LLM
  auto-accepts, or secret leaks.
- Verified the sample through Convert -> Import -> Create Task -> Execute ->
  Package. The task reached the expected `review_required` state and produced a
  9,984-byte ZIP.

## 2026-07-04 成熟化路线最终状态

- Phase 1-6 与 Phase 8 已全部完成。
- Phase 7 已完成统一 CLI、Python SDK 和 Adapter scaffold；路线中的 Webhook
  是可选项，本项目未实现。
- Frontend 已包含 External UIR Adapter、Schema Draft Lab、Review Workbench
  和 Evaluation Center。
- 当前统一状态页为 [`project_status.md`](project_status.md)；历史 guideline、
  specs 和 plans 保留原始目标，不再作为当前能力缺口清单。

## 2026-07-06 SchemaPack-Lineage 交接

- 新增 `backend/app/schemas/lineage.py`、graph/query services 与五个只读 API。
- Task 默认启用 lineage、默认 non-strict；失败 warning 与主转换结果解耦。
- External adapter trace、mapping/review/knowledge、canonical/chunk、
  manifest/consumer contract 已形成稳定关联。
- 前端新增“可信链路”面板与 6 项组件测试。
- 新增 lineage evaluator、demo report builder 和 Evaluation Center 四项 hard
  gates；当前综合 gate report 为 8/8。
- `reports/lineage_eval_report.*` 与 `reports/lineage_demo_report.*` 均由脚本
  生成，不是手工指标。
- Package 1.1 未加入 lineage 自身文件，原因与后续 contract 要求记录在
  [`package_spec.md`](../package_spec.md) 和 [`lineage.md`](../lineage.md)。
