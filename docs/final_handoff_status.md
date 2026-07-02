# SchemaPack Agent 最终交接状态

## 集成仓库状态

- 当前主线基线：`main`。
- 验证基线日期：2026-06-30。
- 统一验证命令：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`。
- 已验证结果：203 个 backend tests passed、Ruff clean、frontend production build successful，并导出 32 个 OpenAPI paths 到 [`docs/openapi.json`](openapi.json)。
- 核心生产边界：UIR input 到 schema-driven package output。

当前处理链路：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

## 已实现能力矩阵

| Area | 当前能力 | Evidence |
| --- | --- | --- |
| Schema/template catalogs | Catalog/governance 覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection，并支持 status transitions、referenced-version protection 和 immutable task snapshots。 | [`docs/developer_guide.md`](developer_guide.md) |
| Document and task APIs | UIR import、document list/detail、task create/list/detail、explicit execution、report retrieval、package metadata 和 package download。 | [`docs/openapi.json`](openapi.json) |
| Mapping and transform | 确定性 field candidate extraction、exact/alias/regex/type/fuzzy matching、evidence、confidence tiers、risk flags、review-required reasons、badcase filtering、projection、normalization、enum maps 和 defaults。 | [`reports/real_world_mapping_eval_report.md`](../reports/real_world_mapping_eval_report.md) |
| Rendering and packages | Canonical model build、JSON/Markdown/chunk rendering、deterministic content organization、validation、manifest generation、ZIP creation 和 strict package verification。 | [`docs/package_spec.md`](package_spec.md) |
| Human review and knowledge | Review approval/rejection、knowledge candidates、draft/active/archived packs、effective-template resolution、metrics、snapshot preservation 和 badcase protections。 | [`reports/knowledge_loop_eval_report.md`](../reports/knowledge_loop_eval_report.md) |
| Optional LLM fallback | 默认关闭，支持 deterministic stub 与 OpenAI-compatible modes；suggestions 仅 Review；具备 bounded retries/timeouts、suggestion caps、redacted reports、provider warning handling 和 strict-mode override。 | [`reports/llm_fallback_eval_report.md`](../reports/llm_fallback_eval_report.md) |
| Frontend workbench | Import、task creation、execution、mapping evidence、validation、content organization controls、chunk preview、raw reports、review/knowledge actions、audit panel 和 package download。 | [`docs/demo_workflow.md`](demo_workflow.md) |
| Deployment | Backend/frontend Dockerfiles、Nginx proxy、Docker Compose volumes、startup database initialization、API-key auth option、audit logs 和 retention cleanup。 | [`docs/deployment.md`](deployment.md) |
| Downstream consumption | Package ZIP/directory smoke ingest 和 training-corpus JSONL export。 | [`docs/package_spec.md`](package_spec.md) |

## API 与 Frontend Surface

- OpenAPI snapshot 在 [`docs/openapi.json`](openapi.json) 中导出 32 个 paths。API inventory 以该文件和 [`docs/openapi_workflow.md`](openapi_workflow.md) 为准。
- Frontend 是 React/Vite workbench，覆盖 demo path：sample UIR import、task creation、execution、report inspection、review decisions、knowledge activation、content organization settings、enriched chunk preview 和 package download。
- 本地 frontend development server 将 `/api` 代理到 `http://127.0.0.1:8000`。
- 容器 profile 通过 Nginx 提供 frontend，并在同一 local origin 下代理 backend API。

## Catalogs、Data 与 Packages

- Catalog/governance types 已覆盖 schemas、schema versions、mapping templates、template versions 和 effective knowledge-pack selection。
- Seeded document families：`contract_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`procurement_doc`。
- Catalog baseline 包含 5 个 schemas 和 5 个 mapping templates。
- Real-world UIR dataset 已扩展到 30 documents。
- Real-world execution evidence 记录 30/30 imports、30/30 executions、30/30 verifier-passing packages。
- Real-world package outputs 位于 `reports/real_world_packages/`；production-like evaluator package outputs 位于 `reports/packages/`。
- Generated packages 包含 structured content、Markdown content、chunks、metadata、mapping/transform/validation/canonical/content-organization/verifier reports、manifest 和 checksums。

## 评估证据

- Unified verification：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 通过，记录 392 个 backend tests passed、Ruff clean、frontend production build successful 和 32 OpenAPI paths。
- Real-world pipeline：30/30 documents import、execute，并产生 verifier-passing packages。
- Real-world mapping：mapping recall `0.48847926267281105`，package pass rate 1.000，badcase violations 0。
- 非采购 API-backed evaluator：20/20 package verification，badcase violations 0，required missing 12；但 average recall `0.4211309523809524`、review-required 149，Phase 1 仍未达标。
- Procurement comparison、content retrieval、knowledge-loop、LLM fallback 等报告仍作为辅助证据保留在 `reports/`。

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
