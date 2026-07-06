# External UIR Adapter API/UI + DeepSeek 辅助适配执行文档

> **历史执行文档**：本文保留 API/UI 与 DeepSeek 接入前的基线描述。相关能力现已实现且保持 report-only 安全边界；当前状态见 [`../project_status.md`](../交接/project_status.md)。

## 0. 文档目的

当前项目已经实现了 External UIR Adapter 的 CLI MVP：支持 `block-list` 与 `section-tree` 两类外部 UIR JSON 方言，通过 CLI 转换为项目标准 `UIRDocument`，并由 Schema Router 推荐到现有 5 类 schema/template。当前缺口是：**External UIR 仍然只是 CLI 兼容层，没有后端 API 和前端 UI 入口；DeepSeek 也尚未作为外部 UIR 适配辅助接口接入。**

本执行文档用于指导 Codex 在不破坏现有课题 5 主链路的前提下，继续完善：

```text
外部 UIR JSON
  -> External UIR Adapter API
  -> DeepSeek-assisted adapter suggestion（可选、默认关闭）
  -> 标准 UIRDocument
  -> Schema Router
  -> 前端预览与人工确认
  -> 导入 Document
  -> 创建 Task
  -> 复用现有 SchemaPack pipeline
  -> Package ZIP
```

核心原则：

1. **不改动主链路**：现有 `UIRDocument -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP` 不重构。
2. **不放宽主 UIR schema**：外部格式通过 adapter 转换为标准 UIR，而不是把 `backend/app/schemas/uir.py` 改成万能 JSON 容器。
3. **DeepSeek 只做 suggestion**：不允许 DeepSeek 自动导入、自动激活 schema/template、自动接受 mapping。
4. **API/UI 先做人工确认闭环**：用户先转换并预览，再手动导入和创建 Task。
5. **所有外部 UIR 路径证据必须保留**：保存在 adapter report 和 block `attributes.external_path`，不得写入未定义的 `source_anchor.external_path`。
6. **不能把该能力描述成 raw file parser**：它接收的是外部 UIR JSON，不是 PDF/Word/Excel/图片/OCR 输入。

---

## 1. 当前基础状态

当前项目已有能力：

- `backend/app/schemas/external_uir.py`
- `backend/app/services/external_uir_adapter_service.py`
- `backend/app/services/schema_router_service.py`
- `scripts/convert_external_uir.py`
- `scripts/eval_external_uir_adapter.py`
- `docs/external_uir_integration.md`

当前支持方言：

```text
block-list
section-tree
```

当前支持 router 输出到：

```text
contract_doc       -> contract_doc_base_v1
policy_doc         -> policy_doc_base_v1
meeting_doc        -> meeting_doc_base_v1
general_doc        -> general_doc_base_v1
procurement_doc    -> procurement_doc_base_v1
```

当前已知评测结果：

```text
adapter pass: 4/4
UIR validation pass: 4/4
schema router top-1 accuracy: 1.0
LLM auto accepted: 0
badcase violations: 0
```

当前缺口：

```text
1. 只有 CLI，没有 API route。
2. 前端没有 External UIR 输入、转换、预览、导入入口。
3. DeepSeek 未接入 adapter suggestion。
4. 还没有 API-backed external UIR evaluator。
5. final demo 脚本尚未展示 External UIR API/UI 路径。
```

---

## 2. 总体设计

### 2.1 新增后端 API

建议新增 route 文件：

```text
backend/app/api/v1/external_uir.py
```

并在：

```text
backend/app/api/v1/router.py
```

中注册。

API 分三步，不建议一步到位自动执行 Task：

```text
POST /api/v1/external-uir/convert
POST /api/v1/external-uir/import
POST /api/v1/external-uir/create-task
```

设计意图：

| API | 作用 | 是否持久化 | 是否执行主 pipeline |
|---|---|---:|---:|
| `/convert` | 外部 UIR -> 标准 UIR + adapter report + route report | 否 | 否 |
| `/import` | 外部 UIR -> 标准 UIR -> 调用 DocumentService 导入 | 是，导入 document | 否 |
| `/create-task` | 基于已导入 document 和 route 结果创建 task | 是，创建 task | 否 |
| 现有 `/tasks/{task_id}/execute` | 执行转换 | 是，生成报告和 package | 是 |

不建议新增“convert-import-execute 一键执行”，因为外部 UIR 适配与 schema route 可能存在误判，必须留出预览和人工确认环节。

### 2.2 新增前端入口

在 React/Vite workbench 中增加一个独立面板：

```text
External UIR Adapter
```

用户流程：

```text
粘贴/上传外部 UIR JSON
  -> 选择 source_system
  -> 选择 dialect_hint，可选 auto
  -> 可选启用 DeepSeek suggestion
  -> 点击 Convert & Preview
  -> 查看 standard UIR preview、adapter report、route report
  -> 点击 Import Standard UIR
  -> 确认 router 推荐的 schema/template
  -> 点击 Create Task
  -> 执行现有 Task
```

### 2.3 DeepSeek 接入定位

DeepSeek 只在 External UIR Adapter 阶段辅助：

```text
unknown external keys / unknown nested structures
  -> DeepSeek suggests mapping to standard UIR fields or block structures
  -> adapter validates suggestion
  -> suggestion 写入 adapter report
  -> conversion result 必须通过 UIRDocument validation
```

DeepSeek 不做：

```text
不自动执行 Task
不自动接受 Mapping
不自动激活 schema/template
不自动创建 active Knowledge Pack
不绕过 badcase filter
不把 API key 写入 task options/reports/audit logs
```

---

## 3. 配置设计：DeepSeek API Key 手动填写

### 3.1 配置文件策略

用户计划后续手动填写 API key。实现时请使用本地 `.env` 或 `.env.local` 之类已被 `.gitignore` 忽略的文件。不要把真实 key 写进：

```text
.env.example
docs/
reports/
fixtures/
task options
adapter reports
audit logs
execution snapshots
git commit
```

推荐配置项加入 `.env.example`，只放占位符：

```env
# External UIR LLM assistance. Disabled by default.
EXTERNAL_UIR_LLM_ENABLED=false
EXTERNAL_UIR_LLM_PROVIDER=deepseek

# Fill these in local .env only. Never commit real keys.
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
DEEPSEEK_MAX_RETRIES=0
DEEPSEEK_MAX_SUGGESTIONS_PER_REQUEST=20
DEEPSEEK_STRICT_JSON=true
```

本地使用时，用户手动在 `.env` 中填写：

```env
EXTERNAL_UIR_LLM_ENABLED=true
EXTERNAL_UIR_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

如需要更强推理能力，可手动改成：

```env
DEEPSEEK_MODEL=deepseek-v4-pro
```

注意：

- 不要默认启用 DeepSeek。
- 测试不得真实联网。
- 默认模型建议先用 `deepseek-v4-flash`，更快更便宜；高难度结构建议用户手动切换 `deepseek-v4-pro`。
- 当前 DeepSeek 官方文档显示其 API 兼容 OpenAI/Anthropic 格式，OpenAI-compatible base URL 可用 `https://api.deepseek.com`，模型包含 `deepseek-v4-flash` 和 `deepseek-v4-pro`。如 DeepSeek 后续变更，以官方文档为准。

### 3.2 Settings 扩展

修改：

```text
backend/app/config.py
```

新增 settings 字段：

```python
external_uir_llm_enabled: bool = False
external_uir_llm_provider: str = "deepseek"

deepseek_api_key: str | None = None
deepseek_base_url: str = "https://api.deepseek.com"
deepseek_model: str = "deepseek-v4-flash"
deepseek_timeout_seconds: int = 20
deepseek_max_retries: int = 0
deepseek_max_suggestions_per_request: int = 20
deepseek_strict_json: bool = True
```

确保 secret redaction 逻辑覆盖：

```text
DEEPSEEK_API_KEY
deepseek_api_key
api_key
authorization
bearer
token
secret
```

---

## 4. 后端 Schema 设计

修改或扩展：

```text
backend/app/schemas/external_uir.py
```

建议增加如下 contracts。

### 4.1 External UIR Convert Request

```python
class ExternalUIRConvertRequest(BaseModel):
    payload: dict[str, Any]
    source_system: str = "external"
    dialect_hint: str | None = None  # "auto" | "block-list" | "section-tree" | None
    route_schema: bool = True
    allow_llm: bool = False
    llm_mode: str | None = None  # None | "deepseek"
    dry_run: bool = True
```

规则：

- `payload` 是外部 UIR JSON。
- `allow_llm=true` 时，仍需检查全局 `EXTERNAL_UIR_LLM_ENABLED=true`。
- 如果用户请求 `allow_llm=true` 但服务端未配置 key，应返回结构化 warning，不应 500。
- `dry_run` 默认 true。

### 4.2 External UIR Convert Response

```python
class ExternalUIRConvertResponse(BaseModel):
    standard_uir: UIRDocument
    adapter_report: ExternalUIRAdapterReport
    route_report: SchemaRouteReport | None = None
    warnings: list[str] = []
    errors: list[str] = []
```

### 4.3 External UIR Import Request

```python
class ExternalUIRImportRequest(BaseModel):
    payload: dict[str, Any]
    source_system: str = "external"
    dialect_hint: str | None = None
    route_schema: bool = True
    allow_llm: bool = False
    llm_mode: str | None = None
```

### 4.4 External UIR Import Response

```python
class ExternalUIRImportResponse(BaseModel):
    doc_id: str
    document: DocumentSummary
    adapter_report: ExternalUIRAdapterReport
    route_report: SchemaRouteReport | None = None
    warnings: list[str] = []
```

### 4.5 External UIR Create Task Request

```python
class ExternalUIRCreateTaskRequest(BaseModel):
    doc_id: str
    schema_id: str
    template_id: str
    schema_version: str | None = None
    template_version: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    route_report: SchemaRouteReport | None = None
```

规则：

- 如果 `route_report.review_required=true`，仍允许创建 task，但响应中必须提示“route review required”。
- 不自动 execute。

---

## 5. 后端 Service 设计

### 5.1 保留已有 deterministic adapter

已有：

```text
backend/app/services/external_uir_adapter_service.py
```

请不要重构为 LLM-first。保持顺序：

```text
1. deterministic dialect detection
2. deterministic conversion
3. deterministic validation
4. optional DeepSeek suggestion only for unknown/low-confidence structures
5. merge suggestions conservatively
6. UIRDocument validation
7. adapter report
```

### 5.2 新增 DeepSeek suggestion service

新增：

```text
backend/app/services/external_uir_llm_service.py
```

职责：

```text
输入：外部 UIR 摘要、未知 key 列表、少量样本文本、已转换失败或低置信字段
输出：结构化 suggestion JSON
```

不要把完整大文档无边界发给模型。应限制：

```text
max payload chars
max blocks
max tables
max suggestions
timeout
retry count
```

建议接口：

```python
class ExternalUIRLLMSuggestionService:
    def suggest_adapter_mappings(
        self,
        payload_excerpt: dict[str, Any],
        unknown_paths: list[str],
        dialect_hint: str | None,
        source_system: str,
    ) -> ExternalUIRLLMSuggestionReport:
        ...
```

### 5.3 DeepSeek Client

可单独新增：

```text
backend/app/services/deepseek_client.py
```

或放在 `external_uir_llm_service.py` 内部。建议单独封装，便于测试 mock。

要求：

- 使用 OpenAI-compatible Chat Completions。
- 只读取环境变量/settings 中的 key。
- 不在日志/report 中输出 key。
- 请求失败时返回 warning，不中断 deterministic adapter。
- 单元测试 mock client，不真实请求 DeepSeek。

伪代码：

```python
class DeepSeekClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.api_key = settings.deepseek_api_key

    def chat_json(self, messages: list[dict[str, str]], *, timeout: int) -> dict[str, Any]:
        if not self.api_key:
            raise LLMNotConfiguredError("DEEPSEEK_API_KEY is not configured")
        # Use OpenAI SDK or httpx. Prefer existing project dependency conventions.
```

如项目已有 OpenAI-compatible LLM adapter，可优先复用，不要重复实现过多 provider 层。

### 5.4 Prompt 设计

DeepSeek prompt 必须强约束：

```text
你是 External UIR Adapter 的结构映射助手。
你只能基于输入 JSON 中存在的 source_path 和 value 生成 suggestion。
你不能臆造字段、不能补全原文没有的信息、不能创建 schema、不能激活规则。
输出必须是 JSON object。
每个 suggestion 必须包含:
- external_path
- target_uir_location
- operation
- confidence
- evidence
- review_required
- reason
```

输出 schema 示例：

```json
{
  "suggestions": [
    {
      "external_path": "$.document.sections[0].heading",
      "target_uir_location": "blocks[].text",
      "operation": "create_heading_block",
      "confidence": 0.92,
      "evidence": "source value is a section heading",
      "review_required": false,
      "reason": "Matches section heading pattern"
    }
  ],
  "warnings": [],
  "must_not_auto_accept_mapping": true,
  "must_not_activate_catalog": true
}
```

后端校验要求：

```text
- output 必须是 JSON object；
- suggestions 数量 <= DEEPSEEK_MAX_SUGGESTIONS_PER_REQUEST；
- 每个 suggestion 必须有 external_path 和 evidence；
- confidence 不得单独决定自动通过；
- review_required 字段必须保留；
- must_not_auto_accept_mapping 必须为 true，否则拒绝该响应；
- must_not_activate_catalog 必须为 true，否则拒绝该响应；
- 不允许 suggestion 指向 unknown UIR field；
- 不允许 suggestion 产生 schema/template active 变更。
```

### 5.5 DeepSeek merge 规则

不要让 DeepSeek 直接覆盖 deterministic conversion。推荐规则：

```text
1. deterministic 已成功转换的 block 不被 LLM 覆盖。
2. LLM 只补充 deterministic 未识别的 unknown_paths。
3. LLM 只生成 adapter suggestion，不生成 final mapping decision。
4. 所有 LLM-assisted fields 写入 adapter_report.assisted_suggestions。
5. 如 LLM suggestion 无 evidence 或 source path 不存在，则丢弃并记录 warning。
6. LLM suggestion 导致 UIR validation 失败时，整体回退 deterministic 结果，并记录 warning。
```

---

## 6. API Route 实现细节

### 6.1 `POST /api/v1/external-uir/convert`

功能：

```text
外部 UIR JSON -> 标准 UIRDocument + adapter report + 可选 route report
```

流程：

```text
1. 解析请求体。
2. 调用 ExternalUIRAdapterService.convert(...).
3. 如果 allow_llm=true 且 settings.external_uir_llm_enabled=true，则调用 DeepSeek suggestion。
4. 验证输出 UIRDocument。
5. route_schema=true 时调用 SchemaRouterService。
6. 返回 standard_uir、adapter_report、route_report。
```

错误策略：

| 情况 | 行为 |
|---|---|
| JSON 不合法 | 422 |
| dialect 无法识别 | 200 + errors/warnings，standard_uir 可为空或返回最小失败结构，建议用 400 也可，但保持报告更利于 UI |
| DeepSeek 未配置 | 200 + warning，继续 deterministic |
| DeepSeek timeout | 200 + warning，继续 deterministic |
| UIR validation fail | 422 + adapter_report + validation errors |
| route confidence < 0.50 | 200 + route_report.review_required=true |

建议对 validation fail 使用结构化 error response，方便 UI 展示。

### 6.2 `POST /api/v1/external-uir/import`

功能：

```text
外部 UIR JSON -> 标准 UIRDocument -> DocumentService.import_document
```

流程：

```text
1. 内部调用 convert。
2. convert 成功后调用 DocumentService。
3. 返回 doc_id、document summary、adapter report、route report。
```

注意：

- 不创建 task。
- 不执行 task。
- route 结果只是推荐，用户仍可在 UI 中修改 schema/template。

### 6.3 `POST /api/v1/external-uir/create-task`

功能：

```text
基于 doc_id + schema/template 创建 Task
```

也可以让前端直接使用现有 `/api/v1/tasks`。但新增这个 endpoint 的好处是可以携带 route_report 和 adapter metadata。

最低要求：

- 复用现有 TaskService。
- 不 execute。
- 如果 schema/template 不存在，返回清晰错误。
- 如果 route_report.review_required=true，response 中标明。

如果想保持 API surface 简洁，可以不新增此 endpoint，前端用现有 `/tasks`。但建议文档里说明原因。

---

## 7. 前端 UI 实现

修改：

```text
frontend/src/App.tsx
```

或如果前端已拆分组件，则新增：

```text
frontend/src/components/ExternalUirPanel.tsx
frontend/src/api/externalUir.ts
```

### 7.1 UI 面板结构

新增面板标题：

```text
External UIR Adapter
```

说明文案：

```text
用于接收上游系统输出的外部 UIR JSON，并转换为 SchemaPack 标准 UIRDocument。
这里不是 PDF/Word/Excel/图片/OCR 入口。
```

输入控件：

```text
- Source System: text input，默认 topic11
- Dialect Hint: select，auto / block-list / section-tree
- External UIR JSON: textarea
- Upload JSON File: file input，可选
- Route Schema: checkbox，默认 true
- Use DeepSeek Assistance: checkbox，默认 false；如果后端返回未启用，显示 warning
```

按钮：

```text
- Convert & Preview
- Import Standard UIR
- Create Task with Recommended Schema
- Use Existing Task Flow
```

### 7.2 结果展示

Convert 后显示：

```text
1. Adapter Summary
   - detected dialect
   - block count
   - trace coverage
   - warnings/errors
   - LLM used: true/false
   - LLM auto accepted: 0

2. Standard UIR Preview
   - doc_id
   - uir_version
   - metadata
   - first 5 blocks
   - raw JSON collapsible

3. Route Report
   - selected schema/template
   - confidence
   - review_required
   - alternatives
   - reasons

4. Adapter Trace
   - external_path
   - target UIR location
   - operation
   - confidence
   - evidence
```

### 7.3 前端安全要求

- 不在 UI 中要求用户输入 DeepSeek API key。
- API key 只在本地 `.env` 中配置。
- UI 只提供 `Use DeepSeek Assistance` 开关。
- 如果后端未启用 DeepSeek，显示：

```text
DeepSeek assistance is disabled or not configured. Deterministic adapter result is shown.
```

- 不显示 full secret。
- 不把外部 UIR 自动提交为 task，必须用户点击导入。

---

## 8. Evaluation 与测试

### 8.1 单元测试

新增或扩展：

```text
backend/tests/test_external_uir_api.py
backend/tests/test_external_uir_deepseek_config.py
backend/tests/test_external_uir_llm_safety.py
backend/tests/test_schema_router_service.py
backend/tests/test_external_uir_adapter_service.py
```

测试用例：

```text
1. convert block-list fixture returns valid UIRDocument.
2. convert section-tree fixture returns valid UIRDocument.
3. convert route_schema=true returns route_report.
4. import endpoint creates document but not task.
5. create-task endpoint creates task but does not execute.
6. allow_llm=true while disabled returns warning, deterministic conversion still works.
7. allow_llm=true with mock DeepSeek returns assisted suggestions in report.
8. mock DeepSeek response with invalid JSON is rejected and recorded as warning.
9. mock DeepSeek response without evidence is rejected.
10. mock DeepSeek response with must_not_auto_accept_mapping=false is rejected.
11. DeepSeek key is never persisted in adapter report.
12. badcase forbidden mappings remain blocked.
```

### 8.2 API-backed evaluator

新增：

```text
scripts/eval_external_uir_api.py
```

功能：

```text
1. 启动后端后运行。
2. 遍历 examples/external_uir fixtures。
3. 调用 /api/v1/external-uir/convert。
4. 校验 UIR validation pass。
5. 校验 route top-1 accuracy。
6. 调用 /api/v1/external-uir/import。
7. 可选调用现有 /tasks 创建 task，但不必须 execute。
8. 输出 JSON/Markdown report。
```

输出：

```text
reports/external_uir_api_eval_report.json
reports/external_uir_api_eval_report.md
```

指标：

```json
{
  "fixture_count": 4,
  "convert_pass_count": 4,
  "import_pass_count": 4,
  "uir_validation_pass_count": 4,
  "router_top1_accuracy": 1.0,
  "llm_auto_accepted_count": 0,
  "badcase_violations": 0,
  "secret_leak_count": 0
}
```

### 8.3 前端测试/构建

至少保证：

```powershell
cd frontend
npm run build
```

如项目已有前端测试，则补充基础组件测试。

---

## 9. 文档更新

需要同步更新：

```text
docs/external_uir_integration.md
docs/api_usage_examples.md
docs/user_web_workbench_guide.md
docs/demo_workflow.md
docs/交接/final_demo_script.md
docs/developer_guide.md
docs/交接/requirement_mapping.md
docs/交接/final_handoff_status.md
README.md
```

### 9.1 external_uir_integration.md

新增：

```text
- API route 使用方法
- 前端操作路径
- DeepSeek 配置方式
- allow_llm=true 的安全边界
- API-backed evaluator 命令
```

### 9.2 api_usage_examples.md

新增示例：

```powershell
$external = Get-Content examples\external_uir\dialect_a_block_list\sample_procurement_external.json -Raw | ConvertFrom-Json
$body = @{
  payload = $external
  source_system = "topic11"
  dialect_hint = "auto"
  route_schema = $true
  allow_llm = $false
} | ConvertTo-Json -Depth 100

$result = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/external-uir/convert `
  -ContentType "application/json" `
  -Body $body

$result.route_report
```

DeepSeek 辅助示例：

```powershell
$body = @{
  payload = $external
  source_system = "topic11"
  dialect_hint = "auto"
  route_schema = $true
  allow_llm = $true
  llm_mode = "deepseek"
} | ConvertTo-Json -Depth 100
```

说明：`allow_llm=true` 不代表自动接受，仅代表请求后端尝试 DeepSeek suggestion。

### 9.3 user_web_workbench_guide.md

新增面向新手的 External UIR 使用说明：

```text
如果你的输入不是 SchemaPack 标准 UIR，而是上游系统输出的外部 UIR JSON，
请先使用 External UIR Adapter 面板转换并预览，再导入。
```

### 9.4 final_demo_script.md

新增演示段落：

```text
演示 External UIR Adapter API/UI：
1. 粘贴 topic11 外部 UIR。
2. Convert & Preview。
3. 查看 route 推荐 procurement_doc。
4. Import Standard UIR。
5. Create Task。
6. Execute。
```

---

## 10. OpenAPI 更新

由于新增 API route，必须运行：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

或统一验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

检查：

```powershell
git diff -- docs/openapi.json
```

确认新增路径：

```text
POST /api/v1/external-uir/convert
POST /api/v1/external-uir/import
可选：POST /api/v1/external-uir/create-task
```

---

## 11. 验收标准

本阶段完成后，必须满足：

### 11.1 功能验收

```text
1. 用户能通过 API 提交外部 UIR JSON，并获得标准 UIRDocument。
2. 用户能通过 API 获取 adapter report 和 schema route report。
3. 用户能通过 API 将转换后的标准 UIR 导入 DocumentService。
4. 前端有 External UIR Adapter 面板。
5. 前端能完成 Convert -> Preview -> Import -> Create Task 的人工确认流程。
6. DeepSeek 可通过 .env 手动配置启用。
7. DeepSeek 未配置时不会影响 deterministic adapter。
8. DeepSeek suggestion 不会自动接受 mapping。
```

### 11.2 安全验收

```text
1. LLM auto accepted count = 0。
2. API key 不出现在 reports、logs、snapshots、frontend response。
3. allow_llm 默认 false。
4. EXTERNAL_UIR_LLM_ENABLED 默认 false。
5. DeepSeek 失败、超时、无效 JSON 时，系统回退 deterministic adapter。
6. badcase violations = 0。
7. 不自动创建或激活 schema/template。
8. 不接收 raw PDF/Word/Excel/image/OCR。
```

### 11.3 测试验收

必须通过：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .

cd ..\frontend
npm run build

backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md

backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

如 `eval_external_uir_api.py` 需要后端运行，应先启动：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

---

## 12. 分阶段实施步骤

### Phase 1：后端 API，不接 DeepSeek

目标：

```text
把 CLI 能力暴露为 API。
```

任务：

```text
1. 新增 backend/app/api/v1/external_uir.py。
2. 实现 /convert。
3. 实现 /import。
4. 可选实现 /create-task，或复用现有 /tasks。
5. 注册 router。
6. 增加 API tests。
7. 运行 OpenAPI export。
```

验收：

```text
- convert 4/4 fixtures pass。
- import 4/4 pass。
- OpenAPI 出现 external-uir paths。
```

### Phase 2：前端 UI

目标：

```text
用户无需命令行即可转换外部 UIR。
```

任务：

```text
1. 新增 External UIR Adapter panel。
2. 支持粘贴 JSON。
3. 支持上传 JSON 文件。
4. 调用 /external-uir/convert。
5. 展示 standard UIR preview。
6. 展示 adapter report。
7. 展示 route report。
8. 调用 /external-uir/import。
9. 使用 route 推荐创建 task。
```

验收：

```text
- 浏览器里能完成 Convert -> Import -> Create Task。
- npm run build 通过。
```

### Phase 3：DeepSeek 配置与 mock 接入

目标：

```text
支持 DeepSeek-assisted suggestion，但不真实联网测试。
```

任务：

```text
1. config.py 新增 DeepSeek settings。
2. .env.example 增加占位配置。
3. 新增 deepseek client 或 OpenAI-compatible provider 封装。
4. 新增 external_uir_llm_service.py。
5. allow_llm=true 时按配置调用。
6. 单元测试使用 mock。
7. 确保未配置 key 时 deterministic adapter 正常工作。
```

验收：

```text
- allow_llm=false 正常。
- allow_llm=true 且未配置时返回 warning。
- mock DeepSeek valid JSON 可生成 assisted_suggestions。
- mock DeepSeek invalid JSON 被拒绝。
- secret leak count = 0。
```

### Phase 4：API-backed evaluator 与文档

目标：

```text
形成最终证据链。
```

任务：

```text
1. 新增 scripts/eval_external_uir_api.py。
2. 输出 reports/external_uir_api_eval_report.{json,md}。
3. 更新 README、developer guide、API examples、demo script。
4. 更新 final_handoff_status。
5. 运行 verify_all。
```

验收：

```text
- external API evaluator pass。
- docs 不再只说 CLI。
- final demo 能展示 UI/API。
```

---

## 13. 不要做的事

本阶段不要做：

```text
1. 不要实现 raw PDF/Word/Excel/image/OCR 上传解析。
2. 不要把外部 UIR 任意 JSON 直接塞进主 pipeline。
3. 不要修改 UIRDocument 为过度宽泛结构。
4. 不要自动生成 active schema/template。
5. 不要让 DeepSeek 自动接受 mapping。
6. 不要把 DeepSeek key 写进代码、文档、报告或 git。
7. 不要在测试中真实调用 DeepSeek。
8. 不要做完整 RAG/vector DB。
9. 不要重构 TaskExecutionService 主链路。
```

---

## 14. Codex 执行提示词

可以直接把下面这段交给 Codex：

```text
请在当前 SchemaPack Agent 项目中继续完善 External UIR Adapter：把现有 CLI 兼容层扩展为后端 API 和前端 UI，并接入 DeepSeek 作为可选的 external UIR adapter suggestion provider。注意不要破坏现有 UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP 主链路。

实施要求：
1. 新增 /api/v1/external-uir/convert 和 /api/v1/external-uir/import，必要时新增 /api/v1/external-uir/create-task，或复用现有 /tasks。
2. /convert 返回标准 UIRDocument、adapter report、可选 route report；不持久化、不创建 task、不执行 pipeline。
3. /import 内部转换并调用 DocumentService 导入标准 UIR；不自动创建 task。
4. 前端新增 External UIR Adapter 面板，支持粘贴/上传外部 UIR JSON、选择 dialect hint、Convert & Preview、Import Standard UIR、Create Task with recommended schema。
5. DeepSeek 只作为可选 suggestion provider。默认关闭，配置来自 .env，key 后续手动填写。不要把真实 key 写入代码、报告、日志、fixtures、task options 或 git。
6. 新增配置项：EXTERNAL_UIR_LLM_ENABLED、EXTERNAL_UIR_LLM_PROVIDER、DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL、DEEPSEEK_TIMEOUT_SECONDS、DEEPSEEK_MAX_RETRIES。
7. DeepSeek suggestion 必须输出严格 JSON，并且必须包含 evidence、external_path、confidence、review_required、must_not_auto_accept_mapping=true、must_not_activate_catalog=true。
8. DeepSeek 失败、未配置、超时或输出非法 JSON 时，不中断 deterministic adapter，只记录 warning。
9. 不允许 DeepSeek 自动接受 mapping，不允许自动激活 schema/template，不允许绕过 badcase。
10. 新增 backend tests、API-backed evaluator、OpenAPI export，并更新 docs 和 final demo script。
11. 最终运行 backend pytest、ruff、frontend build、external adapter evaluator、external API evaluator、verify_all --check-openapi。

当前目标不是支持任意原始文件，而是支持上游系统输出的外部 UIR JSON 方言。保持 CLI 能力兼容，并把新能力明确标注为 External UIR API/UI MVP。
```

---

## 15. 最终交付清单

代码：

```text
backend/app/api/v1/external_uir.py
backend/app/schemas/external_uir.py
backend/app/services/external_uir_adapter_service.py
backend/app/services/schema_router_service.py
backend/app/services/external_uir_llm_service.py
backend/app/services/deepseek_client.py
frontend/src/App.tsx 或 frontend/src/components/ExternalUirPanel.tsx
scripts/eval_external_uir_api.py
```

测试：

```text
backend/tests/test_external_uir_api.py
backend/tests/test_external_uir_deepseek_config.py
backend/tests/test_external_uir_llm_safety.py
```

文档：

```text
docs/external_uir_integration.md
docs/api_usage_examples.md
docs/user_web_workbench_guide.md
docs/demo_workflow.md
docs/交接/final_demo_script.md
docs/developer_guide.md
docs/交接/requirement_mapping.md
docs/交接/final_handoff_status.md
README.md
```

报告：

```text
reports/external_uir_api_eval_report.json
reports/external_uir_api_eval_report.md
reports/external_uir_adapter_eval_report.json
reports/external_uir_adapter_eval_report.md
```

验证命令：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

---

## 16. 对外说明口径

完成后可以这样说明：

```text
项目新增了 External UIR Adapter API/UI 层，用于接入上游系统输出的外部 UIR JSON。
外部 UIR 不直接进入主转换流程，而是先转换为项目标准 UIRDocument，并保留 adapter trace。
Schema Router 会推荐到现有 5 类 schema/template，用户确认后再导入和创建任务。
DeepSeek 可作为可选辅助模型，用于未知外部结构的 adapter suggestion，但默认关闭，
且不会自动接受 mapping、不会自动激活 schema/template，也不会绕过 review 与 badcase 保护。
```
