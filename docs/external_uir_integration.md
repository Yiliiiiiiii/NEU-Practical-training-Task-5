# External UIR Adapter 与 Schema Router

本文档说明外部 UIR JSON 方言进入 SchemaPack Agent 的兼容层。它不是 raw PDF、Word、Excel、图片、扫描件或 OCR 解析入口。

## 边界

生产主链路仍然是：

```text
标准 UIRDocument -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

外部 UIR 只能先经过 adapter 转换为当前项目的标准 `UIRDocument`，再交给既有导入和任务执行流程。当前实现不放宽 `backend/app/schemas/uir.py`，因此外部路径证据保存在 adapter report 和 block `attributes.external_path` 中，而不是写入 `source_anchor.external_path`。

## 已支持方言

- block-list：顶层包含 `chunks`、`blocks` 或 `items`，每个 item 可以包含 `text`、`type`、`rows`、`metadata`、`page`、`bbox` 等字段。
- section-tree：顶层包含 `document.sections[]`，section 可以包含 `heading`、`paragraphs`、`tables` 和 `children`。

## 新增模块

- `backend/app/schemas/external_uir.py`：外部 payload、adapter trace、adapter report、route decision contracts。
- `backend/app/adapters/`：adapter contract、registry 与内置 block-list/section-tree adapters。
- `backend/app/services/external_uir_adapter_service.py`：registry 编排和标准 UIR 转换。
- `backend/app/services/schema_router_service.py`：把标准 UIR 推荐到现有 5 类 schema/template。
- `backend/app/services/schema_draft_workflow_service.py`：显式生成和校验 schema/template drafts。
- `scripts/convert_external_uir.py`：单文件转换 CLI。
- `scripts/eval_external_uir_adapter.py`：fixtures 批量评测 CLI。

## 转换命令

```powershell
backend\.venv\Scripts\python.exe scripts\convert_external_uir.py `
  --input examples\external_uir\dialect_a_block_list\sample_procurement_external.json `
  --source-system topic11 `
  --out examples\external_uir\converted\sample_procurement_standard_uir.json `
  --report reports\external_uir_adapter\sample_procurement_adapter_report.json `
  --route-schema `
  --route-report reports\external_uir_adapter\sample_procurement_route_report.json
```

输出包括标准 UIR、adapter report，以及可选 schema route report。

## 批量评测命令

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md
```

当前 curated suite 覆盖 18 个 fixtures：procurement、policy、meeting、general
四类正常样本，以及表格、嵌套 section-tree、缺字段、噪声和 badcase。契约位于
`examples/external_uir/expected/adapter_expected.jsonl`、
`router_expected.jsonl`、`trace_expected.jsonl` 和 `badcases.jsonl`。

最终报告记录 18/18 selection、conversion 和 UIR validation 通过，trace
coverage `1.0`、schema router top-1 accuracy `1.0`、LLM auto accepted `0`、
badcase violations `0`、secret leaks `0`。warning 会保留在 adapter report；
缺少关键元数据或存在结构噪声时进入 `review_required`，仅缺少可选 URL 不会把
成功转换误报为失败。

## Router 规则

`SchemaRouterService` 支持：

- `contract_doc` -> `contract_doc_base_v1`
- `policy_doc` -> `policy_doc_base_v1`
- `meeting_doc` -> `meeting_doc_base_v1`
- `general_doc` -> `general_doc_base_v1`
- `procurement_doc` -> `procurement_doc_base_v1`

置信度规则：

- `confidence >= 0.75`：高置信推荐，`review_required=false`。
- `0.50 <= confidence < 0.75`：保留推荐，但 `review_required=true`。
- `confidence < 0.50`：不自动选择 schema/template，`review_required=true`。

## LLM 与 Draft 安全

DeepSeek suggestion provider 已作为默认关闭的 report-only 路径接入。
`allow_llm=true` 只允许产生带 evidence 的
`adapter_report.assisted_suggestions`；确定性转换仍是 `standard_uir` 的唯一来源，
`llm_auto_accepted_count` 必须为 0。

Schema/Template Draft Generator 已实现字段发现、草稿生成、风险检查、校验与显式
导出。草稿不会自动注册或激活，也不会绕过 catalog governance；激活仍需要独立的
人工流程。
## External UIR API/UI MVP

The External UIR adapter is now available through a manual-confirmation API/UI
path in addition to the CLI. It accepts upstream External UIR JSON dialects
(`block-list` and `section-tree`) and converts them into the project standard
`UIRDocument`; it is not a raw PDF/Word/Excel/image/OCR parser.

API flow:

1. `POST /api/v1/external-uir/convert` converts External UIR JSON and returns
   `standard_uir`, `adapter_report`, optional `route_report`, warnings, and
   errors. This endpoint does not persist a document, create a task, or execute
   the conversion pipeline.
2. `POST /api/v1/external-uir/import` performs the same conversion and imports
   the standard UIR through `DocumentService`. It does not create a task.
3. `POST /api/v1/external-uir/create-task` creates a task from an imported
   document and an explicitly selected schema/template. It does not execute the
   task.

DeepSeek assistance is disabled by default. Set these only in local `.env` when
manual testing is needed:

```env
EXTERNAL_UIR_LLM_ENABLED=true
EXTERNAL_UIR_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`allow_llm=true` only asks the backend to request adapter suggestions. The
suggestions are written to `adapter_report.assisted_suggestions`; they are not
accepted as mappings, do not activate schema/template catalog entries, and do
not execute tasks. If DeepSeek is disabled, unconfigured, times out, or returns
invalid JSON, the deterministic adapter result is still returned with a warning.

Workbench flow:

1. Open the External UIR Adapter panel.
2. Paste or upload upstream External UIR JSON.
3. Choose `source_system`, optional `dialect_hint`, and whether to route schema.
4. Click `Convert & Preview`.
5. Review the standard UIR, adapter report, route report, warnings, and trace.
6. Click `Import Standard UIR`.
7. Confirm or adjust the recommended schema/template.
8. Click `Create Task`, then use the existing task execution flow.

API evaluator:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md
```

## Optional Raw Upstream

Docling/Unstructured 入口位于 `scripts/upstream_*_to_external_uir.py`，仅用于
离线生成 External UIR。它们使用惰性可选依赖，不是 backend API，也不会自动
导入、建任务或执行。无文本层扫描 PDF 仍返回 `unsupported_scanned_pdf`。
# Current Router Contract

Schema Router is optional recommendation logic. It can run with built-in historical signals enabled for compatibility, or with built-in signals disabled so that only SchemaPack `router_rules.yaml` entries are considered. Router output does not define system capability boundaries; explicit Topic 5 inline input remains authoritative.
