# SchemaPack Agent 外部 UIR 适配与 Schema Router 执行文档

> **历史执行文档**：本文的“当前缺口”和阶段描述记录实施前状态。Adapter Framework、Router v2、API/UI 与 Draft Generator 均已落地；当前状态见 [`../project_status.md`](../project_status.md)。

> 面向 Codex 的实施指导文档  
> 目标：在不破坏当前 SchemaPack Agent 主链路的前提下，为来自课题 11 或其他上游系统的“外部 UIR 方言”增加适配能力，使其能够规范化为当前项目的标准 UIRDocument，并路由到现有 Schema/Template；当现有 Schema 不适配时，仅生成 draft schema/template 供人工审核，不自动激活生产规则。

---

## 0. 当前项目背景与设计前提

当前项目的稳定主链路是：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

当前生产运行边界是：

```text
标准 UIRDocument 输入 -> schema-driven package output
```

当前项目**不处理 raw PDF、Word、Excel、图片、扫描件、OCR 原始解析**。这些能力属于上游解析或离线数据集工具链，不应并入本次改造范围。

当前项目已有的核心 Schema/Catalog family：

```text
contract_doc
policy_doc
meeting_doc
general_doc
procurement_doc
```

本次扩展要解决的问题不是“让系统直接吃任意原始文件”，而是：

```text
让系统能够接收来自上游课题 11 或其他系统的不同 UIR JSON 方言，
先把它们转换为当前项目标准 UIRDocument，
再进入既有 SchemaPack 主流程。
```

---

## 1. 总体目标

### 1.1 一句话目标

新增一层外部 UIR 兼容层：

```text
External UIR
  -> External UIR Adapter
  -> 标准 SchemaPack UIRDocument
  -> Schema Router
  -> 现有 Schema/Template
  -> 现有 TaskExecutionService
  -> 标准 Package ZIP
```

当现有 5 类 Schema 无法覆盖输入文档时，系统可以辅助生成：

```text
new_schema_draft.json
new_template_draft.json
draft_report.json
```

但必须保持 `draft` 状态，不能自动激活。

### 1.2 本次改造完成后应具备的能力

1. 能识别并转换至少 2 种外部 UIR 方言。
2. 能把外部 UIR 转换为当前项目可导入的标准 UIRDocument。
3. 能生成 adapter report，记录外部字段到标准 UIR 字段的转换依据。
4. 能对标准化后的 UIR 运行现有 UIR validation。
5. 能根据文档内容自动推荐当前已有的 schema/template。
6. 能在低置信场景中要求人工确认，而不是强行路由。
7. 能在现有 schema 不适配时生成 draft schema/template，而不是直接创建 active schema/template。
8. 能保证 LLM 只作为 suggestion source，不自动接受 mapping、不自动激活规则。
9. 能通过现有 package verifier、badcase evaluator、knowledge-loop snapshot 等回归检查。

---

## 2. 非目标与边界

本次不要做以下事情：

1. 不要改造项目为 raw PDF/Word/Excel/image/OCR 解析系统。
2. 不要让主 pipeline 同时兼容大量 UIR 方言。
3. 不要把当前标准 UIRDocument 改成过度宽泛的“万能 JSON 容器”。
4. 不要绕过现有 UIR validation。
5. 不要让 LLM 直接生成可自动导入的生产规则。
6. 不要让 LLM 生成的 schema/template 自动 active。
7. 不要为了提高指标删除 required fields。
8. 不要关闭 badcase filters。
9. 不要破坏已有 5 类 schema/template 的行为。
10. 不要修改历史 task snapshot 的语义。

---

## 3. 推荐总体架构

```text
┌──────────────────────────────┐
│ 上游课题11 / 外部系统 UIR JSON │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ ExternalUIRAdapterService     │
│ - deterministic adapters      │
│ - optional LLM suggestions    │
│ - adapter report              │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ 标准 UIRDocument Validation   │
│ - Pydantic model validation   │
│ - block/source/table checks   │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ SchemaRouterService           │
│ - route to existing schema    │
│ - confidence / alternatives   │
│ - review_required if low conf │
└───────────────┬──────────────┘
                │
                ├──────────────► 低置信：人工选择 schema/template
                │
                ▼
┌──────────────────────────────┐
│ Existing TaskExecutionService │
│ UIR -> Schema -> Mapping ...  │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ Standard Package ZIP          │
└──────────────────────────────┘
```

当现有 schema 不合适时：

```text
External UIR / 标准 UIR
        │
        ▼
SchemaTemplateDraftService
        │
        ├── new_schema_draft.json
        ├── new_template_draft.json
        └── draft_report.json

注意：draft 需要人工审核后才能进入 catalog activation。
```

---

## 4. 核心设计原则

### 4.1 主链路不动，兼容层前置

不要直接修改 `TaskExecutionService` 的核心流程来兼容外部 UIR。

应新增：

```text
external UIR -> standard UIR
```

再把标准 UIR 交给现有导入与执行流程。

### 4.2 一个标准 UIRDocument，多种外部 Adapter

不要建立“几套本地标准 UIR”。建议保持：

```text
一个稳定的 SchemaPack 标准 UIRDocument
+ 多个 external UIR adapter
+ 多个 schema/template catalog family
```

### 4.3 规则优先，LLM 兜底

外部 UIR 转换必须优先使用确定性规则：

```text
known external field -> canonical UIR field
known block shape -> standard block
known table shape -> attributes.rows
known source info -> source/source_anchor
```

LLM 只能用于：

```text
无法确定的字段解释
候选 block_type 判断
候选 schema/template routing
draft schema/template 建议
```

LLM 的输出必须带：

```text
confidence
evidence
source_path
review_required
```

### 4.4 所有转换要可追溯

Adapter report 必须记录：

```text
external_path
canonical_path
strategy
confidence
evidence
review_required
warning/error
```

### 4.5 低置信不强行通过

低置信外部字段、低置信 schema 路由、低置信 mapping suggestion 都必须进入 Review。

### 4.6 Draft 不等于 Active

LLM 或规则生成的新 schema/template 只能是 draft。必须经人工确认和现有 catalog governance 才能激活。

---

## 5. 需要新增的模块与文件

### 5.1 Backend schemas

新增：

```text
backend/app/schemas/external_uir.py
```

建议包含以下 Pydantic 模型：

```python
class ExternalUIRSource(BaseModel):
    source_system: str
    source_format: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    source_sha256: str | None = None

class ExternalUIRPayload(BaseModel):
    external_doc_id: str | None = None
    source: ExternalUIRSource
    payload: dict[str, Any]
    hints: dict[str, Any] = Field(default_factory=dict)

class AdapterTraceItem(BaseModel):
    external_path: str
    canonical_path: str
    strategy: Literal["rule", "heuristic", "llm_suggestion", "fallback"]
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    review_required: bool = False
    warning: str | None = None

class AdapterReport(BaseModel):
    adapter_version: str
    source_system: str
    external_doc_id: str | None
    generated_doc_id: str
    status: Literal["passed", "review_required", "failed"]
    trace_items: list[AdapterTraceItem]
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    raw_payload_hash: str

class SchemaRouteDecision(BaseModel):
    selected_schema_id: str | None
    selected_template_id: str | None
    confidence: float
    reason: str
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False
```

注意：

- `payload` 用于承载任意外部 UIR 原始 JSON。
- 不要把 `ExternalUIRPayload` 当成生产 UIR。
- 只有经过 adapter 产出的标准 `UIRDocument` 才能进入主流程。

---

### 5.2 External UIR Adapter Service

新增：

```text
backend/app/services/external_uir_adapter_service.py
```

职责：

1. 接收 `ExternalUIRPayload` 或原始 dict。
2. 检测外部 UIR 方言类型。
3. 调用对应 deterministic adapter。
4. 必要时调用 LLM suggestion provider，但不自动接受。
5. 输出标准 UIRDocument dict。
6. 输出 AdapterReport。
7. 调用当前 UIRDocument 模型做 validation。

建议接口：

```python
class ExternalUIRAdapterService:
    def detect_dialect(self, payload: dict[str, Any]) -> str:
        ...

    def adapt(self, external: ExternalUIRPayload, *, allow_llm: bool = False) -> tuple[UIRDocument, AdapterReport]:
        ...

    def adapt_from_dict(self, payload: dict[str, Any], *, source_system: str, allow_llm: bool = False) -> tuple[UIRDocument, AdapterReport]:
        ...
```

首批支持两种方言即可：

```text
dialect_a: block-list UIR
- 有 blocks/chunks/items
- 每个 block 有 text/type/title/metadata/source

dialect_b: section-tree UIR
- 有 document.sections[]
- section 下有 heading/paragraphs/tables/children
```

---

### 5.3 Deterministic adapter registry

可以在同一个 service 中实现，也可以拆分为：

```text
backend/app/services/external_uir_adapters/
  __init__.py
  base.py
  block_list_adapter.py
  section_tree_adapter.py
```

建议先简单实现，不要过度抽象。

每个 adapter 至少要处理：

```text
外部 doc_id -> doc_id
外部 title -> metadata.title 或 heading block
外部 source/url -> source.source_url / metadata.source_url
外部 chunks/blocks/sections -> UIR blocks
外部 table rows -> block.attributes.rows
外部 page/anchor -> block.source_anchor
外部 field hints -> block.attributes.field_name
```

---

### 5.4 Schema Router Service

新增：

```text
backend/app/services/schema_router_service.py
```

职责：

1. 根据标准 UIRDocument 内容推荐 schema/template。
2. 支持已有 5 个 schema family。
3. 给出 confidence、reason、alternatives。
4. 低置信时 `review_required=true`。
5. 不直接创建 task，不直接执行 task。

建议初始规则：

#### procurement_doc signal

```text
采购
招标
中标
成交
供应商
采购人
代理机构
预算金额
中标金额
项目编号
```

#### policy_doc signal

```text
政策
通知
办法
意见
实施方案
发布机关
发文机关
成文日期
发布日期
有效期
```

#### meeting_doc signal

```text
会议
纪要
主持人
参会人员
议题
审议
会议时间
会议编号
```

#### contract_doc signal

```text
合同
协议
甲方
乙方
金额
履约
签订日期
有效期
```

#### general_doc signal

```text
服务指南
办事指南
申报
申请条件
办理流程
材料清单
服务对象
联系方式
```

建议 decision 示例：

```json
{
  "selected_schema_id": "procurement_doc",
  "selected_template_id": "procurement_doc_base_v1",
  "confidence": 0.91,
  "reason": "detected procurement keywords and supplier/amount/project-number fields",
  "alternatives": [
    {"schema_id": "general_doc", "template_id": "general_doc_base_v1", "confidence": 0.42}
  ],
  "review_required": false
}
```

低置信示例：

```json
{
  "selected_schema_id": null,
  "selected_template_id": null,
  "confidence": 0.34,
  "reason": "no existing schema family reached routing threshold",
  "alternatives": [
    {"schema_id": "general_doc", "template_id": "general_doc_base_v1", "confidence": 0.34},
    {"schema_id": "policy_doc", "template_id": "policy_doc_base_v1", "confidence": 0.29}
  ],
  "review_required": true
}
```

---

### 5.5 Schema/Template Draft Service

新增：

```text
backend/app/services/schema_template_draft_service.py
```

职责：

1. 当现有 schema 路由低置信时，辅助生成 draft schema/template。
2. draft 只落到本地 reports 或 examples，不自动注册 active。
3. 输出 draft report。
4. 可选 LLM 只能生成 suggestion。
5. 生成结果必须通过 schema/template validation。

建议接口：

```python
class SchemaTemplateDraftService:
    def generate_draft(self, uir: UIRDocument, *, allow_llm: bool = False) -> DraftSchemaTemplateResult:
        ...
```

输出文件建议：

```text
reports/external_uir_drafts/<doc_id>/new_schema_draft.json
reports/external_uir_drafts/<doc_id>/new_template_draft.json
reports/external_uir_drafts/<doc_id>/draft_report.json
```

Draft report 内容：

```json
{
  "doc_id": "...",
  "status": "draft_generated",
  "schema_id_suggestion": "custom_doc",
  "template_id_suggestion": "custom_doc_base_v1",
  "fields": [
    {
      "field_name": "...",
      "type": "string",
      "required": false,
      "evidence": ["..."]
    }
  ],
  "aliases": [
    {
      "source_label": "...",
      "target_field": "...",
      "confidence": 0.82,
      "review_required": true
    }
  ],
  "must_not_auto_activate": true
}
```

---

### 5.6 CLI scripts

新增：

```text
scripts/convert_external_uir.py
scripts/eval_external_uir_adapter.py
```

#### convert_external_uir.py

用途：把外部 UIR JSON 转换为标准 UIR JSON，并输出 report。

示例命令：

```powershell
backend\.venv\Scripts\python.exe scripts\convert_external_uir.py `
  --input examples\external_uir\dialect_a\sample_procurement_external.json `
  --source-system topic11 `
  --out examples\external_uir\converted\sample_procurement_standard_uir.json `
  --report reports\external_uir_adapter\sample_procurement_adapter_report.json
```

支持参数：

```text
--input
--source-system
--out
--report
--allow-llm
--route-schema
--route-report
--draft-if-unmatched
```

#### eval_external_uir_adapter.py

用途：批量验证 fixtures。

示例命令：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir\fixtures `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md
```

评测内容：

```text
external fixtures count
adapter success count
standard UIR validation pass count
adapter trace coverage
schema router top-1 accuracy
review-required count
LLM auto-accepted count must be 0
badcase violations
package verification after task execution, if backend available
```

---

### 5.7 Optional API route

MVP 可以先只做 CLI。若要接入 API，新增：

```text
backend/app/api/v1/external_uir.py
```

建议路由：

```text
POST /api/v1/external-uir/convert
POST /api/v1/external-uir/route-schema
POST /api/v1/external-uir/generate-schema-draft
```

注意：

- 这些 API 不应自动创建 task。
- `generate-schema-draft` 不应自动注册 active schema/template。
- 如果返回标准 UIR，应同时返回 adapter report。

返回结构示例：

```json
{
  "status": "converted",
  "doc_id": "external_converted_001",
  "uir": {"...": "standard UIRDocument"},
  "adapter_report": {"...": "..."},
  "schema_route": {
    "selected_schema_id": "procurement_doc",
    "selected_template_id": "procurement_doc_base_v1",
    "confidence": 0.91,
    "review_required": false
  }
}
```

---

### 5.8 Frontend workbench 可选增强

MVP 阶段可不做 UI。若做，建议新增一个轻量面板：

```text
External UIR Import / Adapter Panel
```

功能：

1. 粘贴外部 UIR JSON。
2. 点击“转换为标准 UIR”。
3. 展示 adapter report。
4. 展示 schema router 推荐结果。
5. 低置信时让用户手动选择 schema/template。
6. 点击“导入标准 UIR”后复用现有导入/创建 task/执行流程。

不要把这个面板和现有主流程混在一起，避免初学者误以为任意 JSON 都是标准 UIR。

---

## 6. 数据契约设计

### 6.1 标准 UIR 最小要求

Adapter 输出必须满足当前 UIRDocument 所需结构。最小结构示例：

```json
{
  "uir_version": "1.0",
  "doc_id": "converted_external_001",
  "metadata": {
    "title": "...",
    "doc_type": "procurement_doc",
    "source_system": "topic11"
  },
  "source": {
    "source_type": "external_uir",
    "source_uri": "..."
  },
  "blocks": [
    {
      "block_id": "b001",
      "block_type": "heading",
      "text": "...",
      "level": 1,
      "source_anchor": {
        "external_path": "payload.sections[0].heading"
      },
      "attributes": {}
    },
    {
      "block_id": "b002",
      "block_type": "paragraph",
      "text": "...",
      "source_anchor": {
        "external_path": "payload.sections[0].paragraphs[0]"
      },
      "attributes": {}
    }
  ],
  "assets": []
}
```

实际字段请以项目现有 `backend/app/schemas/uir.py` 为准。Codex 实施前必须阅读该文件，不要凭空新增与模型冲突的字段。

### 6.2 Adapter trace 要求

每个关键转换必须有 trace。至少覆盖：

```text
doc_id
title/source metadata
每个 block 的 text 来源
每个 table rows 来源
每个 field hint 来源
schema route 的证据来源
```

trace 示例：

```json
{
  "external_path": "payload.document.sections[2].tables[0].rows",
  "canonical_path": "blocks[12].attributes.rows",
  "strategy": "rule",
  "confidence": 1.0,
  "evidence": ["external table rows preserved as UIR block attributes.rows"],
  "review_required": false
}
```

### 6.3 LLM suggestion trace 要求

LLM 参与时必须标记：

```json
{
  "external_path": "payload.items[7].kind",
  "canonical_path": "blocks[7].block_type",
  "strategy": "llm_suggestion",
  "confidence": 0.74,
  "evidence": ["model suggested this block is a list because it contains enumerated clauses"],
  "review_required": true,
  "warning": "LLM suggestion is not auto-accepted"
}
```

---

## 7. LLM 安全设计

### 7.1 默认关闭

新增 adapter 中的 LLM 应默认关闭：

```text
EXTERNAL_UIR_ADAPTER_LLM_ENABLED=false
```

如复用现有 LLM fallback 配置，也必须保证：

```text
LLM suggestions are review-required
LLM suggestions are capped
LLM provider failures become warnings unless strict mode is explicitly enabled
secrets are environment-only and redacted in reports
```

### 7.2 允许 LLM 做什么

允许：

1. 判断外部字段语义。
2. 建议 block_type。
3. 建议 schema family。
4. 建议 draft schema field。
5. 建议 draft mapping alias。

### 7.3 禁止 LLM 做什么

禁止：

1. 自动接受 mapping。
2. 自动激活 schema/template。
3. 自动把 draft knowledge pack 变 active。
4. 绕过 badcase filter。
5. 生成没有 source evidence 的字段。
6. 伪造 source_anchor。
7. 将缺失信息补写为看似真实的信息。

---

## 8. 分阶段实施计划

## Phase 0：代码审计与基线确认

### 目标

确认现有 UIRDocument、Schema/Template、TaskExecutionService、LLM fallback、badcase、package verifier 的真实接口。

### Codex 必做

1. 阅读：

```text
backend/app/schemas/uir.py
backend/app/schemas/target_schema.py
backend/app/schemas/mapping_template.py
backend/app/services/task_execution_service.py
backend/app/services/mapping_service.py
backend/app/services/catalog_governance_service.py
backend/app/services/package_verifier_service.py
```

2. 运行基线验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

3. 记录当前测试数量、OpenAPI paths、是否有失败。

### 验收

- 不改代码。
- 能说明当前标准 UIRDocument 必填字段。
- 能说明新增 Adapter 应调用哪个现有 validation。

---

## Phase 1：建立 External UIR fixtures 与契约

### 目标

准备两种外部 UIR 方言样本，作为 adapter 的测试输入。

### 新增目录

```text
examples/external_uir/
  dialect_a_block_list/
    sample_procurement_external.json
    sample_policy_external.json
  dialect_b_section_tree/
    sample_meeting_external.json
    sample_general_external.json
  expected/
    sample_procurement_expected_route.json
    sample_policy_expected_route.json
    sample_meeting_expected_route.json
    sample_general_expected_route.json
```

### 方言 A：block-list UIR 示例形态

```json
{
  "id": "ext_proc_001",
  "title": "某采购项目中标公告",
  "url": "https://example.gov/procurement/001",
  "chunks": [
    {"id": "c1", "type": "title", "text": "某采购项目中标公告"},
    {"id": "c2", "type": "paragraph", "text": "项目编号：ABC-001"},
    {"id": "c3", "type": "table", "rows": [["中标供应商", "某某公司"], ["中标金额", "100万元"]]}
  ]
}
```

### 方言 B：section-tree UIR 示例形态

```json
{
  "document": {
    "docNo": "ext_meeting_001",
    "name": "某市政府常务会议纪要",
    "source": {"url": "https://example.gov/meeting/001"},
    "sections": [
      {
        "heading": "会议概况",
        "paragraphs": ["会议时间：2026年6月30日。主持人：张三。"],
        "children": [
          {"heading": "审议事项", "paragraphs": ["会议审议通过了若干事项。"]}
        ]
      }
    ]
  }
}
```

### 验收

- fixtures 能被 JSON parser 读取。
- 每个 fixture 有 expected route。
- 不接触主 pipeline。

---

## Phase 2：实现 ExternalUIRAdapterService

### 目标

把两种外部 UIR 方言转换为标准 UIRDocument。

### 新增文件

```text
backend/app/schemas/external_uir.py
backend/app/services/external_uir_adapter_service.py
backend/tests/test_external_uir_adapter_service.py
scripts/convert_external_uir.py
```

### 功能要求

1. 自动检测方言：
   - 有 `chunks` / `blocks` / `items` → block-list adapter。
   - 有 `document.sections` → section-tree adapter。
2. 生成稳定 `doc_id`。
3. 保留 title/source/source_url。
4. 生成 UIR blocks。
5. 保留 source_anchor.external_path。
6. table rows 转为 `attributes.rows`。
7. 输出 adapter report。
8. 运行 UIRDocument validation。
9. 失败时输出明确 error。

### 测试要求

```text
test_detects_block_list_dialect
test_detects_section_tree_dialect
test_adapts_block_list_to_valid_uir
test_adapts_section_tree_to_valid_uir
test_adapter_report_has_trace_items
test_table_rows_are_preserved
test_source_anchor_external_path_is_preserved
test_invalid_external_payload_fails_with_report
```

### 验收命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_external_uir_adapter_service.py -q
```

---

## Phase 3：实现 SchemaRouterService

### 目标

对标准化后的 UIR 推荐已有 schema/template。

### 新增文件

```text
backend/app/services/schema_router_service.py
backend/tests/test_schema_router_service.py
```

### 功能要求

1. 支持 5 类 schema：

```text
contract_doc
policy_doc
meeting_doc
general_doc
procurement_doc
```

2. 返回：

```text
selected_schema_id
selected_template_id
confidence
reason
alternatives
review_required
```

3. 路由阈值建议：

```text
confidence >= 0.75: 自动推荐，可继续执行
0.50 <= confidence < 0.75: 推荐但 review_required
confidence < 0.50: 不自动选择，必须人工选择
```

4. 不能直接创建 task。
5. 不能直接执行 pipeline。

### 测试要求

```text
test_routes_procurement_doc
test_routes_policy_doc
test_routes_meeting_doc
test_routes_general_doc
test_routes_contract_doc
test_low_confidence_requires_review
test_alternatives_are_sorted_by_confidence
test_router_does_not_mutate_uir
```

### 验收命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_schema_router_service.py -q
```

---

## Phase 4：Adapter + Router CLI 闭环

### 目标

通过 CLI 完成：

```text
external UIR -> standard UIR -> schema route decision
```

### 修改文件

```text
scripts/convert_external_uir.py
```

### 命令示例

```powershell
backend\.venv\Scripts\python.exe scripts\convert_external_uir.py `
  --input examples\external_uir\dialect_a_block_list\sample_procurement_external.json `
  --source-system topic11 `
  --out examples\external_uir\converted\sample_procurement_standard_uir.json `
  --report reports\external_uir_adapter\sample_procurement_adapter_report.json `
  --route-schema `
  --route-report reports\external_uir_adapter\sample_procurement_route_report.json
```

### 验收

1. 输出标准 UIR 文件。
2. 输出 adapter report。
3. 输出 route report。
4. route report 能正确选择 `procurement_doc`。
5. 标准 UIR 能用现有导入 API 导入。

---

## Phase 5：接入现有 Task 执行链路的离线评测

### 目标

批量验证外部 UIR 转换后能进入现有 TaskExecutionService，生成 package。

### 新增文件

```text
scripts/eval_external_uir_adapter.py
backend/tests/test_external_uir_end_to_end.py
```

### 评测流程

```text
for each external fixture:
  1. adapt external UIR -> standard UIR
  2. validate standard UIR
  3. route schema/template
  4. import document through existing service or API
  5. create task
  6. execute task
  7. verify package
  8. record report
```

MVP 可先 service-level，不一定走 HTTP API。最终建议支持 API-backed 模式。

### 报告字段

```json
{
  "dataset_size": 4,
  "adapter_pass_count": 4,
  "uir_validation_pass_count": 4,
  "schema_router_correct_count": 4,
  "schema_router_top1_accuracy": 1.0,
  "task_execute_pass_count": 4,
  "package_verify_pass_count": 4,
  "review_required_count": 0,
  "llm_auto_accepted_count": 0,
  "badcase_violations": 0
}
```

### 验收指标

```text
standard UIR validation pass rate = 100%
adapter trace coverage = 100%
schema router top-1 accuracy >= 85%
package verification pass rate >= 95% on curated fixtures
LLM auto accepted count = 0
badcase violations = 0
```

---

## Phase 6：可选 LLM Suggestion 接口

### 目标

在 deterministic adapter 无法确定时，引入 LLM suggestion，但不自动接受。

### 修改/新增文件

```text
backend/app/services/external_uir_adapter_service.py
backend/app/services/schema_router_service.py
backend/tests/test_external_uir_llm_safety.py
scripts/eval_external_uir_llm_modes.py
```

### 实现建议

优先复用现有 LLM fallback 安全配置和 redaction 逻辑。不要新写一套不受控的 provider client。

### 安全测试

```text
test_llm_disabled_by_default
test_llm_suggestion_is_review_required
test_llm_suggestion_is_not_auto_accepted
test_llm_provider_failure_becomes_warning_in_non_strict_mode
test_secret_like_values_are_redacted_in_adapter_report
test_llm_cannot_activate_schema_template
```

### 验收

- LLM disabled 模式通过。
- stub 模式通过。
- provider failure 模式通过。
- `auto_accepted_count = 0`。
- report 中不出现 API key。

---

## Phase 7：Schema/Template Draft Generator

### 目标

当 SchemaRouterService 无法把外部 UIR 安全归入已有 5 类 schema 时，生成 draft schema/template 供人工审核。

### 新增文件

```text
backend/app/services/schema_template_draft_service.py
backend/tests/test_schema_template_draft_service.py
scripts/generate_schema_template_draft.py
```

### 功能要求

1. 只生成 draft。
2. 不自动写入 active catalog。
3. 不自动创建 knowledge pack。
4. 不自动执行 task。
5. draft 必须附 evidence。
6. draft template 中每条 alias/regex/default/transform target 必须能被 validator 检查。
7. draft report 必须写明：`must_not_auto_activate: true`。

### 验收

```text
test_generates_schema_draft_from_uir_blocks
test_generates_template_draft_with_review_required_aliases
test_draft_is_not_active
test_unknown_schema_requires_manual_activation
test_draft_report_has_evidence
test_badcase_pairs_are_not_suggested_as_safe_aliases
```

---

## Phase 8：API 与前端面板，可选

### 目标

为工作台提供外部 UIR 转换入口。

### Backend API

新增：

```text
backend/app/api/v1/external_uir.py
```

路由：

```text
POST /api/v1/external-uir/convert
POST /api/v1/external-uir/route-schema
POST /api/v1/external-uir/generate-schema-draft
```

需要更新：

```text
backend/app/api/v1/router.py
docs/openapi.json
```

运行：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

### Frontend

在 `frontend/src/App.tsx` 中增加外部 UIR 面板，保持轻量：

```text
粘贴 External UIR JSON
点击 Convert
展示 Adapter Report
展示 Schema Route
如果 route high-confidence，允许一键导入标准 UIR
如果 low-confidence，要求用户手动选择 schema/template
```

### 前端不要做的事

1. 不要让用户一键激活 draft schema。
2. 不要隐藏 adapter warnings。
3. 不要把外部 UIR 与标准 UIR 混称。

---

## Phase 9：文档与验收报告

### 新增/更新文档

```text
docs/external_uir_integration.md
docs/api_usage_examples.md
docs/developer_guide.md
docs/requirement_mapping.md
docs/final_demo_script.md
docs/final_handoff_status.md
README.md
```

### 报告

新增：

```text
reports/external_uir_adapter_eval_report.json
reports/external_uir_adapter_eval_report.md
reports/external_uir_llm_safety_report.json
reports/external_uir_llm_safety_report.md
```

### 文档必须明确

1. 本项目仍然只以标准 UIRDocument 作为生产主流程输入。
2. External UIR Adapter 是兼容层，不是原始文件解析器。
3. LLM 只提供 suggestion，不自动接受。
4. 新 schema/template 只生成 draft，不自动 active。
5. Package verification 不等于字段语义完全正确。
6. 外部 UIR 转换结果必须通过 UIR validation。

---

## 9. 验收标准

### 9.1 功能验收

| 项目 | 目标 |
| --- | --- |
| 外部 UIR 方言支持 | 至少 2 种 |
| 外部 UIR -> 标准 UIR | 可运行 |
| 标准 UIR validation | curated fixtures 100% 通过 |
| Adapter trace coverage | 100% |
| Schema Router | 支持 5 类现有 schema |
| Router top-1 accuracy | curated fixtures >= 85% |
| 低置信路由 | 必须 review_required |
| LLM suggestion | 默认关闭，仅 suggestion |
| LLM auto accepted | 0 |
| Draft schema/template | 只生成 draft，不 active |
| Package verification | curated fixtures >= 95%，最好 100% |
| Badcase violations | 0 |

### 9.2 回归验收

必须运行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

建议运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_like.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py --fixtures examples\external_uir --out reports\external_uir_adapter_eval_report.json --markdown reports\external_uir_adapter_eval_report.md
```

如果新增 API，则必须重新导出 OpenAPI：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

---

## 10. 风险与防护

### 风险 1：把外部 UIR 适配误做成原始文件解析

防护：文档、API、UI 均使用 `External UIR`，不要使用 `PDF import`、`Word import` 等表述。

### 风险 2：标准 UIR 被改得过度宽泛

防护：优先在 adapter 层做转换，不要随意放宽 UIRDocument schema。

### 风险 3：LLM 幻觉导致伪造字段

防护：LLM output 必须有 source evidence，默认 review_required；无 source evidence 的字段不得进入标准 UIR。

### 风险 4：新 schema/template 自动激活导致治理污染

防护：draft generator 输出只落 reports，不调用 activate API。

### 风险 5：为了路由准确率误映射

防护：Router 只决定 schema/template，不负责字段 mapping；字段 mapping 仍走现有 MappingService、badcase filter 和 review。

### 风险 6：历史任务被新 adapter 或 schema 影响

防护：保持 task snapshot 不变；新增 adapter 只影响新输入。

---

## 11. 推荐 Codex 执行顺序

请按以下顺序执行，不要跳阶段：

```text
1. 先阅读现有 UIRDocument 与 TaskExecutionService。
2. 新增 external UIR fixtures。
3. 实现 external_uir.py schemas。
4. 实现 deterministic ExternalUIRAdapterService。
5. 编写 adapter tests 并通过。
6. 实现 SchemaRouterService。
7. 编写 router tests 并通过。
8. 实现 convert_external_uir.py CLI。
9. 实现 eval_external_uir_adapter.py。
10. 跑外部 UIR adapter eval。
11. 再考虑 LLM suggestion 安全接入。
12. 再考虑 schema/template draft generator。
13. 最后更新 docs 和 README。
14. 运行统一 verify_all gate。
```

---

## 12. 给 Codex 的直接提示词

可以把下面这段直接交给 Codex：

```text
请在当前 SchemaPack Agent 项目中实现“External UIR Adapter + Schema Router”扩展。要求不破坏现有 UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP 主链路。生产主流程仍只接受当前项目标准 UIRDocument。

新增目标：
1. 支持至少两种外部 UIR JSON 方言：block-list 和 section-tree。
2. 将外部 UIR 转换为当前项目标准 UIRDocument。
3. 生成 adapter_report，记录 external_path -> canonical_path、strategy、confidence、evidence、review_required、warnings/errors。
4. 转换后的 UIR 必须通过现有 UIRDocument validation。
5. 新增 SchemaRouterService，把标准 UIR 推荐到现有 5 类 schema/template：contract_doc、policy_doc、meeting_doc、general_doc、procurement_doc。
6. Router 必须输出 selected_schema_id、selected_template_id、confidence、reason、alternatives、review_required。
7. 低置信时不得自动选择，必须 review_required。
8. 新增 CLI scripts/convert_external_uir.py，支持输入外部 UIR、输出标准 UIR、adapter report 和 route report。
9. 新增 scripts/eval_external_uir_adapter.py，批量评测 fixtures，并输出 JSON/Markdown 报告。
10. LLM 如接入只能作为 suggestion，默认关闭，auto_accepted_count 必须为 0，不能自动激活 schema/template，不能绕过 badcase filter。
11. 如果实现 schema/template draft generator，只能生成 draft 文件和 draft_report，不得自动 active。
12. 补充 tests，至少覆盖 adapter、router、trace、validation、low-confidence review、LLM safety。
13. 更新 docs/external_uir_integration.md、developer_guide、README 和 final_handoff_status。
14. 最后运行 backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi，并报告结果。

严禁：
- 不要把项目改成直接解析 PDF/Word/Excel/image/OCR。
- 不要放宽主 UIRDocument 以容纳任意 JSON。
- 不要让 LLM 自动接受 mapping。
- 不要让 draft schema/template 自动 active。
- 不要关闭 badcase filters。
- 不要删除 required fields 来提高指标。
```

---

