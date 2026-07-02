# 开发者指南

## 项目结构

- `backend/app/api/v1/`：FastAPI routes，覆盖 documents、catalogs、tasks、reviews、knowledge、evaluation reports 和 audit logs。
- `backend/app/schemas/`：Pydantic contracts，覆盖 UIR、catalog records、task execution、reports、package metadata、reviews 和 knowledge packs。
- `backend/app/services/`：确定性 conversion、catalog、review、knowledge、package、audit 和 retention services。
- `backend/app/services/task_execution_service.py`：完整 UIR-to-package pipeline 的 orchestration。
- `backend/app/db/models.py`：SQLAlchemy tables，用于 tests 和本地 runtime databases。
- `frontend/src/`：React/Vite operator workbench。
- `examples/production_like/` 与 `examples/real_world/`：可复现 evaluation fixtures 与 UIR datasets。
- `scripts/`：verification、OpenAPI export、evaluators、report builders 和 downstream package consumers。
- `docs/` 与 `reports/`：当前操作指南和生成证据。

## 主流程与职责边界

当前执行 pipeline：

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical Model -> Render -> Content Organization
-> Validation -> Manifest -> ZIP -> Package Verification
```

`backend/app/services/task_execution_service.py` 负责 pipeline orchestration。它加载 imported UIR，通过 catalog 解析目标 schema/template，捕获不可变 task snapshots，执行 mapping 和 transformation，生成 canonical/rendered artifacts，组织 chunks，执行 validation，生成 manifest，写入 ZIP package，并验证 package contents。

新增 runtime 行为应放在对应 service 边界内，而不是 API route layer。API routes 负责请求校验、调用 services、返回结构化 responses；conversion decisions 应留在 services 和 reports 中，确保 tasks 可复现。

## Catalog Governance 与 Snapshots

Schemas 和 mapping templates 由 catalog 管理。Version activation 与 archival 必须保持历史可复现性：

- 新 task executions 默认解析 active schema/template versions，除非调用方显式指定 version。
- 每个 task 在执行前保存已解析的 schema/template snapshot。
- 已被引用的 versions 不允许破坏性 lifecycle transitions。
- archived versions 不应被用于新的 task executions。

新增或修改 catalog fixtures 时，要保持 schema fields、aliases、regex rules、enum maps、defaults 和 transform targets 一致。修改 route 或 schema 后，重新运行 OpenAPI export 和 unified verification gate。

## Mapping、Review 与 Knowledge Growth

`MappingService` 应保持确定性 strategy order，并为每个 decision 输出 confidence、confidence tier、evidence、risk flags、`badcase_filter` 和必要的 `review_required_reason`。可选 LLM fallback suggestions 必须保持 review-required，不能自动接受 mapping。

Review-derived knowledge candidates 会进入 draft knowledge packs。Active packs 通过 effective-template path 被选择，使未来 tasks 可以使用 approved aliases，同时保持旧 task snapshots 和 badcase protections。修改此流程时，需要验证 knowledge-loop reports 中的 snapshot preservation 和 badcase violation counts。

## 前端工作台

`frontend/src/App.tsx` 中的 React/Vite workbench 是本地 operator console，支持 UIR import、task creation/execution、report inspection、mapping evidence、review actions、candidate decisions、knowledge-pack activation、audit log reads、content organization controls、chunk previews 和 package download。

控件应贴近其影响的 workflow，并保持 development proxy contract：frontend 的 `/api` 请求代理到本地 backend。

## Package 与 Chunk 变更

修改 package roles、required files、media types 或 checksum rules 时，需同步更新：

- `docs/package_spec.md`
- `ManifestService`
- `PackageService`
- `PackageVerifierService`
- downstream smoke/export scripts（如果 package shape 影响 consumers）

Content organization 变更应在 task options 省略 `content_organization` 时保持兼容。Chunks 应保持 source links、title paths、quality tags、稳定 report summary keys，以及启用 parent-child strategy 时的 parent-child metadata。

## 默认本地 Gate

从仓库根目录运行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

当前已验证基线：203 个 backend tests、Ruff clean、frontend production build successful、32 个 OpenAPI paths。

小循环可以单独运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .

cd ..\frontend
npm ci
npm run build
```

## 报告重新生成

运行 API-backed evaluators 前先启动 backend：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

在另一个仓库根目录终端中重新生成 production-like 与 real-world evidence：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_like.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_knowledge_loop_real_world.py --base-url http://127.0.0.1:8000 --timeout 60
```

重新生成非采购 recall evidence：

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

如果 API-backed evaluator 返回 import errors，应保留失败报告作为 evidence，并先诊断 backend/API path；不要删除 required gold fields、禁用 badcase filters，或把失败导入产生的 zero missing counts 当作成功。

重新生成 offline retrieval、knowledge-loop、LLM fallback 和 acceptance evidence：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_chunk_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_llm_fallback_modes.py
backend\.venv\Scripts\python.exe scripts\build_acceptance_report.py
```

LLM fallback evaluator 默认不联网，覆盖 disabled、deterministic stub 和 provider failure safety modes。除非 operator 提供 credentials 并明确要求，不要运行 OpenAI-compatible network mode。

## 常见问题

- `.env`：本地开发用 `.env.example`，容器 profile 用 `.env.production.example`。除非显式测试 fallback，否则保持 `LLM_FALLBACK_ENABLED=false`。
- SQLite state：backend tests 会创建隔离 pytest databases。本地运行可能使用 `backend/schemapack.db` 或配置的 `DATABASE_URL`；当 catalog state 需要重建时再删除或重置。
- Frontend dependencies：checkout 后或 `frontend/package-lock.json` 变化后运行 `npm ci`。不要把无关 `npm install` lockfile 更新混入文档变更。
- API ports 被占用：本地 backend 和 Compose 都使用 port `8000`；启动 Uvicorn 前先停止已有 process/container 或选择其他端口。
- OpenAPI drift：修改 API route 或 schema 后运行 `scripts/export_openapi.py` 或统一 gate。
- Secrets：LLM 与 API keys 只通过环境变量配置。Task options、execution snapshots、reports 和 audit metadata 必须保持 redacted。
