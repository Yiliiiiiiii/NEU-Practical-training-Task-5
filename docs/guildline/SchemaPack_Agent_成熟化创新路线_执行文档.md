# SchemaPack Agent 成熟化与创新发展路线执行文档

> **实施状态（2026-07-04）**：Phase 1-6、Phase 8 已完成；Phase 7 的 CLI、Python SDK 与 Adapter scaffold 已完成，Webhook 作为可选项未实现。详见 [`../project_status.md`](../project_status.md)。

> 交付对象：Codex / 开发执行模型  
> 适用项目：SchemaPack Agent（课题 5：数据格式标准化转换智能体）  
> 文档目标：在当前项目已经完成主链路、External UIR API/UI MVP 与 DeepSeek report-only suggestion 占位的基础上，规划下一阶段成熟化、创新化、平台化路线。  
> 核心原则：不破坏当前稳定主链路，不把项目变成 OCR/原始文档解析器，不让 LLM 自动改写生产规则。所有新增能力都要通过 adapter、schema governance、human review、evaluation gate 和 package verification 进行治理。

---

## 0. 当前项目基线与继续发展的定位

### 0.1 当前已经具备的核心能力

当前 SchemaPack Agent 已经具备以下稳定主链路：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

当前能力大致包括：

1. 标准 `UIRDocument` 输入。
2. 5 类内置 schema/template family：
   - `contract_doc`
   - `general_doc`
   - `meeting_doc`
   - `policy_doc`
   - `procurement_doc`
3. 文档导入、任务创建、任务执行、报告读取、Package 下载。
4. 确定性 mapping：
   - exact
   - alias
   - regex
   - type
   - fuzzy
   - optional LLM suggestion，但必须 review-required。
5. Transform、Canonical、Markdown/JSON/Chunks 渲染。
6. Validation、Manifest、ZIP package、Verifier。
7. Human Review 与 Knowledge Pack：
   - review approval/rejection
   - candidate decision
   - draft/active/archived knowledge packs
   - effective template resolution
   - snapshot preservation
   - badcase protection
8. External UIR Adapter：
   - 支持 `block-list` 与 `section-tree` 两类外部 UIR JSON 方言。
   - 支持 CLI。
   - 已升级为 API/UI MVP：
     - `POST /api/v1/external-uir/convert`
     - `POST /api/v1/external-uir/import`
     - `POST /api/v1/external-uir/create-task`
   - 前端已有 External UIR Adapter panel。
   - DeepSeek 默认关闭，只做 report-only suggestion。
9. 已有真实 UIR 数据集、badcase registry、retrieval query gold、non-procurement mapping 改进报告等项目证据。

### 0.2 下一阶段总目标

下一阶段目标不是“继续堆功能”，而是把项目升级为：

> 面向多源文档智能体的 Schema 化治理与成果包生成平台。

更具体地说，SchemaPack Agent 应定位为：

```text
上游解析器 / 上游课题 / 外部系统
        ↓
External UIR Adapter Framework
        ↓
标准 UIRDocument
        ↓
Schema / Template / Mapping Governance
        ↓
Human Review & Knowledge Growth
        ↓
Package Contract & Downstream Evaluation
        ↓
RAG / 训练语料 / 结构化入库 / 人工审核 / API 消费
```

它不应该和 OCR、PDF 解析器、RAG 框架直接竞争，而应该成为这些系统之间的“可信中间层”。

### 0.3 参考开源项目的启发

以下项目仅作为架构启发，不要求直接依赖：

| 项目 | 可借鉴点 | SchemaPack 不应做什么 |
| --- | --- | --- |
| Docling | 文档解析、PDF 理解、多格式输入、面向 GenAI 的结构化输出。参考其“上游解析器”角色。 | 不要在主线中重造 OCR/PDF 解析。 |
| Unstructured | 面向 LLM 的文档 ETL、多格式非结构化数据预处理、chunking/enrichment。 | 不要把 SchemaPack 改造成通用文件解析 ETL。 |
| Airbyte | Connector 生态、source/destination 抽象、连接器 registry、可扩展适配层。 | 不要让每个 adapter 乱接主流程，应统一 registry 与测试规范。 |
| dbt | 转换即代码、测试、文档、lineage、治理资产版本化。 | 不要让 schema/template 成为不可测的散乱 JSON。 |
| OpenRefine | 人机协同清洗、转换、reconciliation、人工确认。 | 不要让大模型自动替代人工治理。 |
| Haystack / LlamaIndex | 下游 RAG / agent / pipeline 编排生态。 | 不要实现完整 RAG runtime；提供高质量 package 与 evaluation 即可。 |
| Ragas | 从主观检查走向系统化评测。 | 不要只展示 demo，应把 evaluation center 作为成熟度核心。 |

参考链接：

```text
Docling: https://docling-project.github.io/docling/
Unstructured: https://docs.unstructured.io/open-source/introduction/overview
Airbyte Connectors: https://docs.airbyte.com/platform/1.8/move-data/sources-destinations-connectors
dbt Docs: https://docs.getdbt.com/docs/build/documentation
OpenRefine: https://openrefine.org/
Haystack: https://docs.haystack.deepset.ai/docs/intro
LlamaIndex: https://developers.llamaindex.ai/python/framework/
Ragas: https://docs.ragas.io/en/stable/
```

---

## 1. 总体发展路线

建议按 8 个阶段推进。每个阶段都必须有：

1. 明确边界。
2. 独立测试。
3. 独立评估脚本。
4. 文档说明。
5. 不破坏当前主链路。
6. 不降低 badcase protection。
7. 不把 LLM suggestion 当成自动规则。

阶段总览：

| Phase | 名称 | 核心目标 | 优先级 |
| --- | --- | --- | --- |
| Phase 0 | 基线冻结与工程守护 | 冻结当前可用状态，建立后续开发的回归门禁 | P0 |
| Phase 1 | Adapter Framework 生态化 | 将 External UIR 从固定服务扩展为可插拔 adapter framework | P0 |
| Phase 2 | Schema Router v2 | 让 schema/template 推荐更可解释、可比较、可人工确认 | P0 |
| Phase 3 | Schema/Template Draft Generator | 根据样本辅助生成新 schema/template 草稿 | P1 |
| Phase 4 | Review Workbench 产品化 | 把 review 从单条确认升级为治理工作台 | P1 |
| Phase 5 | Evaluation Center | 建立统一评测中心，持续量化项目质量 | P1 |
| Phase 6 | Downstream Contract Platform | 强化 Package 下游消费契约与版本兼容 | P2 |
| Phase 7 | Integration & Plugin Ecosystem | 提供 SDK、CLI、Webhook、Adapter 模板 | P2 |
| Phase 8 | Optional Raw Document Upstream | 可选接入 Docling/Unstructured，而不是自研 OCR | P3 |

---

# Phase 0：基线冻结与工程守护

## 0.1 目标

在继续开发前，先明确当前项目的“可回退基线”。后续所有阶段都不能破坏：

```text
标准 UIR -> Schema/Template -> Mapping -> Transform -> Package
```

以及：

```text
External UIR -> Convert -> Preview -> Import -> Create Task -> Execute
```

## 0.2 必须检查

从项目根目录运行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

若新增 API 后 OpenAPI path 数量变化，先重新导出：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
git diff -- docs/openapi.json
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

启动后端：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

运行 External UIR API evaluator：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md
```

运行现有 External UIR adapter evaluator：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md
```

运行核心回归：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_like.py
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_llm_fallback_modes.py
```

## 0.3 工程守护要求

后续所有阶段都要满足：

```text
llm_auto_accepted_count = 0
badcase_violations = 0
package_verification 不下降
旧 task snapshot 不被修改
DeepSeek key 不进入 repo / reports / task options / audit logs
External UIR API 不自动执行 task
External UIR API 不自动激活 schema/template
```

## 0.4 不允许行为

严禁：

1. 修改 `backend/app/schemas/uir.py` 来容纳任意外部 JSON。
2. 把外部 JSON 原样当作标准 UIR 导入。
3. 让 DeepSeek 直接生成 active schema/template。
4. 让 DeepSeek suggestion 直接进入 mapping accepted 状态。
5. 删除 required fields 来提高指标。
6. 禁用 badcase filters 来提高 recall。
7. 把 package verification 等同于字段语义全部正确。
8. 把 OCR、扫描件识别、PDF 原始解析作为主线功能。

---

# Phase 1：Adapter Framework 生态化

## 1.1 目标

当前 External UIR Adapter 已支持：

```text
block-list
section-tree
```

下一步要从“两个内置方言”升级为：

```text
可注册、可测试、可评估、可版本化的 Adapter Framework
```

目标架构：

```text
External UIR Payload
        ↓
Adapter Registry
        ↓
Selected Adapter
        ↓
Standard UIRDocument
        ↓
Adapter Report
        ↓
Schema Router
        ↓
Existing Pipeline
```

## 1.2 建议新增目录

```text
backend/app/adapters/
  __init__.py
  base.py
  registry.py
  builtin/
    __init__.py
    block_list_adapter.py
    section_tree_adapter.py
    topic11_adapter.py
    generic_json_adapter.py
  reports.py
  validators.py

backend/app/schemas/
  adapter.py

backend/tests/
  test_adapter_registry.py
  test_block_list_adapter.py
  test_section_tree_adapter.py
  test_topic11_adapter.py
  test_adapter_trace_contract.py
  test_adapter_quality_metrics.py

examples/external_uir/
  manifests/
    adapter_fixture_manifest.json
  topic11/
    sample_001.json
    expected_001.json
  block_list/
    sample_001.json
  section_tree/
    sample_001.json
  generic_json/
    sample_001.json

scripts/
  eval_adapters.py
  scaffold_adapter.py
```

说明：

- 当前已有 `external_uir_adapter_service.py` 不要直接删除。
- 先将其作为 legacy wrapper，内部调用新的 adapter registry。
- 新代码稳定后，再逐步把旧 service 逻辑拆分到 adapter classes。

## 1.3 Adapter 基类设计

新增：

```python
# backend/app/adapters/base.py

from abc import ABC, abstractmethod
from typing import Any

class AdapterCapability(BaseModel):
    adapter_id: str
    adapter_version: str
    supported_dialects: list[str]
    source_systems: list[str]
    supports_tables: bool = True
    supports_sections: bool = True
    supports_pages: bool = False
    supports_bbox: bool = False
    requires_llm: bool = False
    description: str

class AdapterInput(BaseModel):
    payload: dict[str, Any]
    source_system: str = "unknown"
    dialect_hint: str = "auto"
    options: dict[str, Any] = Field(default_factory=dict)

class AdapterResult(BaseModel):
    standard_uir: UIRDocument
    adapter_report: AdapterReport
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

class ExternalUirAdapter(ABC):
    capability: AdapterCapability

    @abstractmethod
    def can_handle(self, adapter_input: AdapterInput) -> float:
        """Return confidence 0.0-1.0."""

    @abstractmethod
    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        """Convert external UIR payload into standard UIRDocument."""
```

## 1.4 Adapter Registry

新增：

```python
# backend/app/adapters/registry.py

class AdapterRegistry:
    def register(self, adapter: ExternalUirAdapter) -> None:
        ...

    def list_capabilities(self) -> list[AdapterCapability]:
        ...

    def select_adapter(self, adapter_input: AdapterInput) -> SelectedAdapter:
        ...

    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        ...
```

选择策略：

1. 若 `dialect_hint` 明确指定 adapter，则优先使用指定 adapter。
2. 若 `dialect_hint=auto`，调用所有 adapter 的 `can_handle()`。
3. 选择 confidence 最高者。
4. 若最高 confidence < 0.5，则返回 `review_required=true` 或 `unsupported_dialect` error。
5. 返回 alternatives，方便 UI 展示。

## 1.5 Adapter Report 统一结构

新增或扩展：

```python
class AdapterTraceItem(BaseModel):
    trace_id: str
    external_path: str
    target_path: str
    transform: str
    evidence: str | None = None
    confidence: float
    warnings: list[str] = Field(default_factory=list)

class AdapterReport(BaseModel):
    adapter_id: str
    adapter_version: str
    source_system: str
    dialect: str
    detected_dialect: str
    trace_items: list[AdapterTraceItem]
    trace_coverage: float
    block_count: int
    table_count: int
    warning_count: int
    error_count: int
    assisted_suggestions: list[dict] = Field(default_factory=list)
    llm_auto_accepted_count: int = 0
```

要求：

- 每个生成的 UIR block 都必须尽量有对应 trace。
- `trace_coverage` 计算方式：
  ```text
  有 external_path 的 standard UIR block 数 / standard UIR block 总数
  ```
- 外部路径证据必须放在：
  ```text
  adapter_report.trace_items[].external_path
  block.attributes.external_path
  ```
- 不得放入未定义的 `source_anchor.external_path`。

## 1.6 API 改造

当前已有：

```text
POST /api/v1/external-uir/convert
POST /api/v1/external-uir/import
POST /api/v1/external-uir/create-task
```

新增可选 API：

```text
GET  /api/v1/external-uir/adapters
POST /api/v1/external-uir/detect
```

### GET /api/v1/external-uir/adapters

返回所有 adapter capability：

```json
{
  "items": [
    {
      "adapter_id": "block_list",
      "adapter_version": "1.0.0",
      "supported_dialects": ["block-list"],
      "source_systems": ["topic11", "generic"],
      "supports_tables": true,
      "supports_sections": false,
      "requires_llm": false
    }
  ]
}
```

### POST /api/v1/external-uir/detect

只检测，不转换：

```json
{
  "selected_adapter": {
    "adapter_id": "block_list",
    "confidence": 0.91
  },
  "alternatives": [
    {
      "adapter_id": "section_tree",
      "confidence": 0.12
    }
  ],
  "review_required": false
}
```

## 1.7 前端改造

External UIR Adapter 面板新增：

1. Adapter 自动检测结果。
2. Adapter 下拉选择。
3. Adapter capability 展示。
4. Alternatives 展示。
5. Trace coverage 可视化。
6. Conversion warnings 显示。
7. `unsupported_dialect` 时给出人工提示。
8. 保留现有 Convert -> Preview -> Import -> Create Task 流程。

前端状态建议：

```ts
type AdapterState = {
  adapters: AdapterCapability[]
  selectedAdapterId?: string
  detectedAdapter?: AdapterDetectionResult
  standardUir?: unknown
  adapterReport?: AdapterReport
  routeReport?: RouteReport
  warnings: string[]
  errors: string[]
}
```

## 1.8 评估脚本

新增：

```text
scripts/eval_adapters.py
```

输入：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_adapters.py `
  --fixtures examples\external_uir `
  --out reports\adapter_framework_eval_report.json `
  --markdown reports\adapter_framework_eval_report.md
```

输出指标：

```json
{
  "adapter_count": 4,
  "fixture_count": 20,
  "adapter_selection_accuracy": 0.95,
  "uir_validation_pass_rate": 1.0,
  "trace_coverage_avg": 0.98,
  "schema_router_top1_accuracy": 0.9,
  "llm_auto_accepted_count": 0,
  "badcase_violations": 0
}
```

## 1.9 Phase 1 验收标准

必须满足：

```text
adapter registry 可列出所有 adapter
block-list 和 section-tree 通过新 registry 跑通
现有 /external-uir/convert 行为不破坏
新增 /external-uir/adapters 与 /detect 可用
每个 adapter 至少 3 个 fixture
adapter eval pass
standard UIR validation pass rate = 100%
llm_auto_accepted_count = 0
badcase_violations = 0
verify_all.py --check-openapi 通过
```

---

# Phase 2：Schema Router v2

## 2.1 目标

当前 Schema Router 已能推荐到 5 类 schema/template。下一步要让推荐过程更成熟：

1. 可解释。
2. 可比较 alternatives。
3. 可人工 override。
4. 可回归评测。
5. 可绑定 adapter report。
6. 可输出 route evidence。

## 2.2 当前支持的目标

Router 继续只推荐已有 schema/template：

```text
contract_doc -> contract_doc_base_v1
general_doc -> general_doc_base_v1
meeting_doc -> meeting_doc_base_v1
policy_doc -> policy_doc_base_v1
procurement_doc -> procurement_doc_base_v1
```

暂时不要自动创建新 schema/template。

## 2.3 新 RouteReport 结构

建议：

```python
class RouteEvidence(BaseModel):
    evidence_type: str  # keyword, field_hint, metadata, table_label, adapter_hint
    value: str
    source_path: str | None = None
    weight: float
    matched_schema: str

class SchemaRouteCandidate(BaseModel):
    schema_id: str
    template_id: str
    confidence: float
    reasons: list[str]
    evidence: list[RouteEvidence]
    risk_flags: list[str] = Field(default_factory=list)

class SchemaRouteReport(BaseModel):
    selected_schema_id: str | None
    selected_template_id: str | None
    confidence: float
    review_required: bool
    candidates: list[SchemaRouteCandidate]
    decision_reason: str
    route_version: str
```

## 2.4 路由策略

采用混合分数：

```text
score = metadata_score * 0.30
      + keyword_score * 0.25
      + field_label_score * 0.25
      + table_pattern_score * 0.10
      + adapter_hint_score * 0.10
```

示例规则：

### procurement_doc

加分 evidence：

```text
采购
中标
招标
成交
供应商
采购人
代理机构
预算金额
中标金额
项目编号
```

风险：

```text
预算金额不能自动当 award_amount
控制价不能自动当 award_amount
```

### policy_doc

加分 evidence：

```text
政策
通知
办法
意见
指南
发布机构
发文机关
发布日期
有效期
```

风险：

```text
成文日期不能自动当 publish_date
retrieved_at 不能当 effective_date
```

### meeting_doc

加分 evidence：

```text
会议
纪要
主持人
参会
议题
研究事项
会议时间
```

风险：

```text
主持人不能自动当 attendees
联系人不能当 attendees
```

### general_doc

加分 evidence：

```text
办事指南
申报指南
申请条件
服务对象
办理流程
所需材料
联系方式
```

### contract_doc

加分 evidence：

```text
甲方
乙方
合同
协议
金额
期限
生效
签订
```

## 2.5 API 行为

`POST /api/v1/external-uir/convert` 保持：

- `route_schema=true` 时返回 route_report。
- 只是推荐，不创建 task。
- `review_required=true` 时前端必须要求人工确认。

`POST /api/v1/external-uir/create-task` 要求：

- 不能只使用 router result 自动创建。
- 必须由请求体显式传入 `schema_id`、`template_id`。
- 可以传入 `route_report_id` 或 route snapshot，但它只是 evidence。

## 2.6 前端改造

External UIR Adapter panel 中新增：

1. 推荐 schema/template 高亮。
2. Alternatives 列表。
3. Route confidence 条。
4. Route evidence 展开。
5. `review_required=true` 时要求用户点击确认。
6. 用户可以手动 override schema/template。
7. 创建 task 前提示：
   ```text
   该操作只创建任务，不会执行；请确认 schema/template 选择。
   ```

## 2.7 评测脚本

新增或扩展：

```text
scripts/eval_schema_router.py
```

指标：

```text
top1_accuracy
top2_accuracy
review_required_count
unsafe_auto_route_count
route_evidence_coverage
```

验收：

```text
top1_accuracy >= 0.85
top2_accuracy >= 0.95
unsafe_auto_route_count = 0
review_required_count 可解释
```

---

# Phase 3：Schema/Template Draft Generator

## 3.1 目标

这是最具创新性的阶段：让系统能根据一批标准 UIR 或 External UIR 转换结果，辅助生成新的 schema/template 草稿。

核心流程：

```text
样本集合
-> 字段发现
-> 字段聚类
-> 候选 schema draft
-> 候选 mapping template draft
-> 风险扫描
-> badcase 预检查
-> 人工 review
-> draft 保存
-> regression evaluation
-> 人工 active
```

## 3.2 重要边界

绝对禁止：

```text
LLM 生成 active schema
LLM 生成 active template
LLM 自动激活 catalog version
LLM 自动接受 mapping
LLM 删除 required fields
LLM 绕过 badcase filters
```

允许：

```text
生成 draft_schema.json
生成 draft_template.json
生成 draft_report.json
生成 risk_report.json
生成 suggested_aliases
生成 suggested_regex
生成 suggested_transform_rules
```

## 3.3 建议新增目录

```text
backend/app/services/
  schema_draft_service.py
  template_draft_service.py
  field_discovery_service.py
  draft_risk_service.py

backend/app/schemas/
  schema_draft.py

backend/app/api/v1/
  schema_drafts.py

backend/tests/
  test_schema_draft_service.py
  test_template_draft_service.py
  test_draft_risk_service.py
  test_schema_draft_api.py

examples/schema_drafts/
  samples/
  expected/

reports/schema_drafts/
```

## 3.4 字段发现

Field Discovery 从样本中提取：

```text
metadata keys
block.attributes.field_name
table rows field/value
heading labels
colon patterns，例如 "项目名称：xxx"
repeated label patterns
dates / amounts / identifiers
```

输出：

```json
{
  "field_candidates": [
    {
      "field_name": "project_name",
      "source_labels": ["项目名称", "采购项目名称"],
      "value_examples": ["xxx 项目"],
      "frequency": 0.8,
      "inferred_type": "string",
      "evidence_paths": ["blocks[0].attributes.rows[1]"],
      "risk_flags": []
    }
  ]
}
```

## 3.5 字段聚类

把相似 label 聚成候选字段：

```text
项目名称 / 采购项目名称 / 标的名称 -> project_name
采购人 / 采购单位 / 招标人 -> purchaser
```

策略：

1. Deterministic normalization：
   - 去空格。
   - 全角半角归一。
   - 标点归一。
   - 常见同义词。
2. Embedding/LLM 可选，但只做 suggestion。
3. 高频 + 多样本出现的字段优先。
4. 高风险字段必须 review-required。

## 3.6 Draft Schema 生成

生成 schema 时字段包含：

```json
{
  "field_id": "project_name",
  "name": "project_name",
  "type": "string",
  "required": true,
  "description": "采购项目名称",
  "source_evidence": ["项目名称", "采购项目名称"],
  "confidence": 0.91,
  "review_required": false
}
```

Required 判定建议：

```text
样本覆盖率 >= 0.8 且领域核心字段 -> required 推荐
0.4 <= 样本覆盖率 < 0.8 -> optional 推荐
高风险字段 -> review_required
```

但 required 只能是 recommendation，最终必须人工确认。

## 3.7 Draft Template 生成

生成：

```text
aliases
regex_rules
type_rules
default_rules
transform_rules
```

示例：

```json
{
  "target_field": "project_name",
  "aliases": ["项目名称", "采购项目名称"],
  "confidence": 0.93,
  "evidence_count": 12,
  "review_required": false
}
```

Regex suggestion 必须带测试样例：

```json
{
  "target_field": "meeting_date",
  "pattern": "会议时间[:：]\\s*(\\d{4}年\\d{1,2}月\\d{1,2}日)",
  "positive_examples": ["会议时间：2026年7月3日"],
  "negative_examples": ["发布日期：2026年7月3日"],
  "review_required": true
}
```

## 3.8 Draft Risk Scan

必须扫描：

1. 是否包含 forbidden source/target pair。
2. 是否把预算金额映射成中标金额。
3. 是否把主持人映射成 attendees。
4. 是否把联系人映射成 attendees。
5. 是否把成文日期映射成 publish_date。
6. 是否把 retrieved_at 映射成 effective_date。
7. 是否删除或弱化 required fields。
8. 是否有过宽 regex。
9. 是否有 LLM hallucinated field。
10. 是否没有 source evidence。

风险报告：

```json
{
  "must_not_auto_activate": true,
  "risk_count": 2,
  "risks": [
    {
      "risk_type": "forbidden_mapping",
      "source_label": "控制价",
      "target_field": "award_amount",
      "severity": "high",
      "action": "remove_or_review"
    }
  ]
}
```

## 3.9 DeepSeek 在 Draft Generator 中的使用方式

DeepSeek 只能用于：

```text
字段命名建议
字段描述建议
同义 label 聚类建议
regex 草稿建议
transform rule 草稿建议
```

DeepSeek 输出必须是严格 JSON，并通过 Pydantic 校验。

配置仍只在 `.env`：

```env
EXTERNAL_UIR_LLM_ENABLED=true
EXTERNAL_UIR_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

不得将 API key 写入：

```text
task options
adapter report
draft report
audit logs
fixtures
docs
git commit
```

## 3.10 API 设计

新增：

```text
POST /api/v1/schema-drafts/discover
POST /api/v1/schema-drafts/generate
GET  /api/v1/schema-drafts/{draft_id}
POST /api/v1/schema-drafts/{draft_id}/validate
POST /api/v1/schema-drafts/{draft_id}/export
```

暂不实现：

```text
POST /api/v1/schema-drafts/{draft_id}/activate
```

激活仍走现有 catalog governance，且必须人工确认。

## 3.11 前端设计

新增 “Schema Draft Lab” 面板：

1. 选择样本 documents。
2. 点击 Discover Fields。
3. 查看字段候选。
4. 查看聚类结果。
5. 生成 schema draft。
6. 生成 template draft。
7. 查看 risk report。
8. 导出 draft。
9. 显示：
   ```text
   Draft 不会自动生效，必须进入 Catalog Review 后才能激活。
   ```

## 3.12 Phase 3 验收标准

```text
能从 5-10 个样本生成 draft schema/template
所有 draft 都包含 source evidence
risk scan 必须运行
must_not_auto_activate = true
DeepSeek 未配置时 deterministic path 可运行
DeepSeek 配置时只生成 suggestion
badcase_violations = 0
llm_auto_accepted_count = 0
无 API key 泄露
```

---

# Phase 4：Review Workbench 产品化

## 4.1 目标

当前 Review 已能 approve/reject。下一步要变成“治理工作台”。

核心目标：

```text
Review item
-> human decision
-> candidate rule
-> impact preview
-> draft pack
-> regression evaluation
-> active pack
-> future tasks only
```

## 4.2 新增功能

### 4.2.1 Review Impact Preview

在 approve 之前，系统预测这条规则会影响哪些 future mappings：

```json
{
  "candidate_id": "cand_xxx",
  "would_affect": [
    {
      "doc_id": "real_policy_007",
      "source_label": "发文单位",
      "target_field": "issuer",
      "confidence_after": 0.88
    }
  ],
  "risk_flags": [],
  "badcase_hits": []
}
```

### 4.2.2 Negative Knowledge

Reject 不只是丢弃，而是形成 negative rule：

```json
{
  "source_label": "控制价",
  "forbidden_target": "award_amount",
  "reason": "控制价不是中标金额",
  "source": "human_rejection"
}
```

Negative knowledge 要进入 badcase protection 或 risk scan。

### 4.2.3 Batch Review

支持按以下维度批量查看：

```text
schema_id
target_field
review_required_reason
confidence_tier
risk_flag
source_label
```

但批量 approve 必须限制：

```text
同一 source_label
同一 target_field
同一 schema/template
无 high-risk flag
无 badcase hit
```

### 4.2.4 Knowledge Pack 冲突检测

检测：

```text
两个 active pack 对同一 source_label 给出不同 target
active pack 与 badcase forbidden pair 冲突
new draft 与 archived rule 冲突
template alias 与 negative knowledge 冲突
```

### 4.2.5 Pack Rollback

允许把 active pack archive，并确认：

```text
future tasks 不再使用
old tasks snapshot 不变
reports 保留历史 pack reference
```

## 4.3 API 设计

新增或扩展：

```text
GET  /api/v1/reviews/summary
GET  /api/v1/reviews/grouped
POST /api/v1/reviews/{review_id}/impact-preview
POST /api/v1/reviews/batch-approve
POST /api/v1/reviews/batch-reject

GET  /api/v1/knowledge/packs/{pack_id}/diff
GET  /api/v1/knowledge/packs/{pack_id}/impact
POST /api/v1/knowledge/packs/{pack_id}/rollback
GET  /api/v1/knowledge/conflicts
```

## 4.4 前端设计

新增 Review Workbench：

1. 左侧 filter：
   - schema
   - field
   - reason
   - confidence
   - risk flag
2. 中间 review list。
3. 右侧 evidence panel：
   - source value
   - source path
   - block preview
   - mapping reason
   - badcase filter
4. Impact preview tab。
5. Candidate rule preview。
6. Pack diff preview。
7. Approve/reject buttons。
8. Batch mode，但高风险默认禁用。

## 4.5 评估指标

```text
review_required_count
review_resolution_rate
candidate_generation_count
active_pack_effect_count
negative_rule_count
conflict_count
badcase_violations
old_snapshot_unchanged
```

## 4.6 验收标准

```text
approve 前可查看 impact preview
reject 可形成 negative knowledge
badcase hit 阻止 active
batch approve 不能处理 high-risk item
rollback 不影响 old snapshot
knowledge-loop evaluator 通过
badcase violations = 0
```

---

# Phase 5：Evaluation Center

## 5.1 目标

当前项目有很多评测脚本和 reports，但比较分散。下一步建立统一 Evaluation Center：

```text
Dataset Registry
Gold Label Registry
Badcase Registry
Eval Run Store
Metrics Dashboard
Regression Gate
Trend Report
```

这一步会显著提升项目成熟度，因为成熟项目不仅能跑 demo，还能持续证明每次改动没有破坏质量。

## 5.2 建议新增目录

```text
backend/app/services/
  evaluation_center_service.py
  dataset_registry_service.py
  metric_registry_service.py

backend/app/schemas/
  evaluation_center.py

backend/app/api/v1/
  evaluation_center.py

frontend/src/
  EvaluationCenterPanel.tsx

reports/evaluation_center/
```

## 5.3 Dataset Registry

统一登记：

```json
{
  "dataset_id": "real_world_uir_2026_07_03",
  "dataset_type": "real_world_uir",
  "doc_count": 45,
  "doc_types": {
    "general_doc": 10,
    "meeting_doc": 10,
    "policy_doc": 15,
    "procurement_doc": 10
  },
  "gold_files": [
    "examples/real_world/gold/mapping_gold.jsonl",
    "examples/real_world/gold/real_world_badcases.jsonl",
    "examples/real_world/gold/retrieval_queries.jsonl"
  ]
}
```

新增文件：

```text
examples/datasets/dataset_registry.json
```

## 5.4 Metric Registry

统一指标定义：

```json
{
  "metric_id": "mapping_recall",
  "description": "Gold mappings covered by accepted or review-required safe mappings.",
  "higher_is_better": true,
  "threshold": 0.55
}
```

核心指标：

```text
adapter_validation_pass_rate
adapter_trace_coverage
schema_router_top1_accuracy
mapping_recall
required_field_coverage
review_required_count
required_missing_count
badcase_violation_count
package_verification_rate
retrieval_recall_at_3
summary_faithfulness_score
tag_quality_score
downstream_contract_pass_rate
llm_auto_accepted_count
secret_leak_count
old_snapshot_unchanged
```

## 5.5 Eval Run Store

每次评测生成统一结构：

```json
{
  "run_id": "eval_20260703_001",
  "created_at": "2026-07-03T00:00:00Z",
  "git_commit": "abc123",
  "dataset_id": "real_world_uir_2026_07_03",
  "eval_type": "non_procurement_mapping",
  "metrics": {
    "average_recall": 0.5677551020408163,
    "review_required": 69,
    "required_missing": 6,
    "badcase_violations": 0
  },
  "passed": true,
  "report_paths": {
    "json": "reports/non_procurement_mapping_eval_report.json",
    "markdown": "reports/non_procurement_mapping_eval_report.md"
  }
}
```

保存到：

```text
reports/evaluation_center/eval_runs.jsonl
```

## 5.6 API

```text
GET  /api/v1/evaluation-center/datasets
GET  /api/v1/evaluation-center/metrics
GET  /api/v1/evaluation-center/runs
GET  /api/v1/evaluation-center/runs/{run_id}
GET  /api/v1/evaluation-center/scorecard
POST /api/v1/evaluation-center/run
```

`POST /run` 可以先不真正执行长任务，只读取已有 reports 并注册 summary。

## 5.7 前端 Evaluation Center

新增 panel：

1. 当前总分卡。
2. Per-schema scorecard。
3. Per-adapter scorecard。
4. 趋势图：
   - mapping recall
   - review-required
   - badcase violations
   - package verification
5. 最近 eval runs。
6. Failed gate 展示。
7. 打开原始 report 链接。

## 5.8 Regression Gate

新增：

```text
scripts/check_regression_gates.py
```

配置：

```json
{
  "gates": [
    {
      "metric": "badcase_violation_count",
      "op": "==",
      "value": 0
    },
    {
      "metric": "llm_auto_accepted_count",
      "op": "==",
      "value": 0
    },
    {
      "metric": "package_verification_rate",
      "op": ">=",
      "value": 1.0
    },
    {
      "metric": "adapter_trace_coverage",
      "op": ">=",
      "value": 0.95
    }
  ]
}
```

## 5.9 验收标准

```text
所有核心 evaluator 可以注册到 Evaluation Center
前端可查看 scorecard
regression gate 可运行
badcase violation 作为硬门禁
LLM auto accepted 作为硬门禁
旧 reports 仍可直接查看
```

---

# Phase 6：Downstream Contract Platform

## 6.1 目标

将现有 Package 从“生成 ZIP”升级为“版本化下游契约”。

当前 package 已包含：

```text
content.json
content.md
chunks.jsonl
mapping_report.json
transform_report.json
validation_report.json
content_organization_report.json
canonical.json
metadata.json
manifest.json
verifier_report.json
```

下一步要为不同下游明确 contract：

```text
RAG Corpus Contract
Training Corpus Contract
Structured CSV Contract
Database Insert Contract
Review System Contract
API Client Contract
```

## 6.2 Contract Manifest

新增：

```text
contracts/
  rag_corpus_contract_v1.json
  training_corpus_contract_v1.json
  structured_csv_contract_v1.json
  package_contract_v1_1.json
```

示例：

```json
{
  "contract_id": "rag_corpus_contract",
  "version": "1.0.0",
  "required_fields": [
    "chunk_id",
    "text",
    "source_links",
    "title_path",
    "summary",
    "keywords"
  ],
  "optional_fields": [
    "parent_chunk_id",
    "quality_tags"
  ]
}
```

## 6.3 Consumer Verifier

新增：

```text
scripts/verify_consumer_contract.py
```

用法：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_consumer_contract.py `
  --package reports\demo_standard_package.zip `
  --contract contracts\rag_corpus_contract_v1.json `
  --out reports\consumer_contract_report.json `
  --markdown reports\consumer_contract_report.md
```

## 6.4 Downstream Exporters

整理现有 exporter：

```text
scripts/export_structured_csv.py
scripts/export_rag_corpus.py
scripts/export_training_corpus.py
```

统一输出 report：

```json
{
  "exporter": "export_rag_corpus",
  "contract_id": "rag_corpus_contract",
  "input_package": "standard_package.zip",
  "output": "reports/exports/rag.jsonl",
  "record_count": 123,
  "contract_pass": true
}
```

## 6.5 验收标准

```text
至少 3 个 downstream contracts
每个 contract 有 verifier
real_world packages 可批量验证
consumer contract pass rate >= 0.95
package spec 不破坏
```

---

# Phase 7：Integration & Plugin Ecosystem

## 7.1 目标

让 SchemaPack 不只是一个本地 demo，而是可被其他系统集成。

## 7.2 CLI 工具

新增统一 CLI：

```text
schemapack
  convert-external
  import
  create-task
  execute-task
  download-package
  eval
  list-schemas
  list-adapters
```

可以先做为：

```text
scripts/schemapack_cli.py
```

后续再 package 化。

示例：

```powershell
backend\.venv\Scripts\python.exe scripts\schemapack_cli.py convert-external `
  --input examples\external_uir\topic11\sample.json `
  --out reports\converted.json `
  --route
```

## 7.3 SDK

生成 OpenAPI client 或手写最小 client：

```text
sdk/python/schemapack_client/
  __init__.py
  client.py
  models.py
```

最小能力：

```python
client.import_uir(...)
client.convert_external_uir(...)
client.create_task(...)
client.execute_task(...)
client.download_package(...)
```

## 7.4 Webhook

可选新增：

```text
POST /api/v1/webhooks
GET  /api/v1/webhooks
DELETE /api/v1/webhooks/{webhook_id}
```

事件：

```text
task.completed
task.failed
package.created
review.created
knowledge_pack.activated
```

注意：webhook payload 不得包含完整 UIR、API key、LLM key。

## 7.5 Adapter Plugin Template

新增：

```text
templates/adapter_plugin/
  adapter.py
  manifest.json
  fixtures/
  tests/
  README.md
```

`scaffold_adapter.py`：

```powershell
backend\.venv\Scripts\python.exe scripts\scaffold_adapter.py `
  --adapter-id enterprise_x `
  --out backend\app\adapters\builtin\enterprise_x_adapter.py
```

## 7.6 验收标准

```text
CLI 可完成 External UIR -> Package 的完整链路
SDK 可执行基础 API 调用
adapter scaffold 可生成模板
OpenAPI 无 drift
secrets 不泄露
```

---

# Phase 8：Optional Raw Document Upstream

## 8.1 目标

提供可选的原始文档上游接入，但不改变 SchemaPack 主定位。

推荐链路：

```text
PDF / Word / HTML / Image
        ↓
Docling / Unstructured / 课题 11
        ↓
External UIR JSON
        ↓
SchemaPack External UIR Adapter
        ↓
Standard UIRDocument
        ↓
SchemaPack Pipeline
```

## 8.2 实施原则

1. 不在 SchemaPack 主服务中直接实现 OCR。
2. 不要求默认安装 Docling/Unstructured。
3. 作为 optional offline tool 或 adapter 示例。
4. 输出仍然必须是 External UIR JSON 或标准 UIR。
5. 仍然经过 Convert -> Preview -> Import -> Create Task。

## 8.3 示例工具

新增：

```text
scripts/upstream_docling_to_external_uir.py
scripts/upstream_unstructured_to_external_uir.py
```

这些脚本可以先作为实验性工具，默认不进主 API。

## 8.4 验收标准

```text
optional dependency 不影响 verify_all
没有 OCR 依赖时主项目仍可运行
示例脚本可从 sample PDF 生成 External UIR JSON
生成结果仍走 External UIR API/UI
```

---

# DeepSeek 使用规范

## 9.1 允许使用场景

DeepSeek 可用于：

```text
External UIR adapter suggestion
字段命名 suggestion
字段聚类 suggestion
schema draft description suggestion
regex draft suggestion
mapping template draft suggestion
review explanation suggestion
```

## 9.2 禁止使用场景

DeepSeek 不得：

```text
自动 accepted mapping
自动创建 task
自动执行 task
自动 active schema/template
自动修改 base template
绕过 badcase filter
覆盖 deterministic standard_uir
把 key 写入 report
```

## 9.3 `.env` 配置

只允许本地 `.env`：

```env
EXTERNAL_UIR_LLM_ENABLED=true
EXTERNAL_UIR_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=20
DEEPSEEK_MAX_RETRIES=0
DEEPSEEK_MAX_SUGGESTIONS=20
```

注意：

- 不要提交 `.env`。
- `.env.example` 只放变量名，不放真实 key。
- 所有 reports 必须 redacted。
- 所有 audit logs 必须 redacted。

## 9.4 Prompt 约束

DeepSeek prompt 必须包含：

```text
你只能返回 JSON。
你不能决定最终 schema/template。
你不能激活规则。
你不能声明 suggestion 已被接受。
你必须为每条 suggestion 提供 source evidence。
缺少 evidence 时必须返回 review_required=true。
```

## 9.5 输出 JSON Schema

示例：

```json
{
  "suggestions": [
    {
      "suggestion_type": "field_alias",
      "source_label": "采购项目名称",
      "target_field": "project_name",
      "confidence": 0.86,
      "evidence": "metadata.title and table row label match",
      "source_paths": ["blocks[0].attributes.rows[1]"],
      "review_required": true,
      "risk_flags": []
    }
  ],
  "warnings": [],
  "must_not_auto_accept": true
}
```

Pydantic 校验失败时：

```text
记录 warning
丢弃 LLM suggestion
保留 deterministic result
不让 task fail，除非 strict mode
```

---

# 全局质量门禁

## 10.1 每阶段必须运行

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

后端小循环：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

前端：

```powershell
cd frontend
npm ci
npm run build
```

External UIR：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py `
  --fixtures examples\external_uir `
  --out reports\external_uir_adapter_eval_report.json `
  --markdown reports\external_uir_adapter_eval_report.md

backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py `
  --base-url http://127.0.0.1:8000 `
  --fixtures examples\external_uir `
  --out reports\external_uir_api_eval_report.json `
  --markdown reports\external_uir_api_eval_report.md
```

Core evaluations：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_production_like.py
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_llm_fallback_modes.py
```

## 10.2 关键指标

不可退化：

```text
badcase_violations = 0
llm_auto_accepted_count = 0
package_verification_rate 不下降
old_snapshot_unchanged = true
secret_leak_count = 0
```

可逐步提升：

```text
adapter_trace_coverage
schema_router_top1_accuracy
mapping_recall
review_required_count
required_missing_count
retrieval_recall@k
downstream_contract_pass_rate
```

## 10.3 失败处理原则

如果评估失败：

1. 保留失败报告。
2. 先定位失败原因。
3. 不要删除 gold labels。
4. 不要删除 badcases。
5. 不要放宽 required fields。
6. 不要禁用 safety checks。
7. 不要把 import failure 导致的 zero missing 当成成功。

---

# 建议 Codex 执行顺序

## 第一轮：Phase 1 + Phase 2

目标：

```text
Adapter Framework
Schema Router v2
```

优先做：

1. 新增 adapter base/registry。
2. 将现有 block-list/section-tree 迁入 registry。
3. 保持旧 API 行为兼容。
4. 新增 `/external-uir/adapters` 和 `/detect`。
5. 扩展 route report。
6. 前端增加 adapter selection / route evidence。
7. 新增 eval_adapters.py。
8. 跑全量验证。

## 第二轮：Phase 3

目标：

```text
Schema/Template Draft Generator
```

优先做：

1. Field discovery。
2. Draft schema generator。
3. Draft template generator。
4. Risk scan。
5. DeepSeek optional suggestion。
6. Draft Lab UI。
7. 只导出 draft，不 active。

## 第三轮：Phase 4 + Phase 5

目标：

```text
Review Workbench
Evaluation Center
```

优先做：

1. Impact preview。
2. Negative knowledge。
3. Pack diff/conflict/rollback。
4. Dataset registry。
5. Eval run registry。
6. Scorecard UI。
7. Regression gate。

## 第四轮：Phase 6 + Phase 7

目标：

```text
Downstream Contracts
SDK / CLI / Plugin Template
```

优先做：

1. Consumer contract manifests。
2. Consumer verifier。
3. Unified CLI。
4. Python SDK。
5. Adapter scaffold template。

## 第五轮：Phase 8

目标：

```text
Optional Raw Document Upstream
```

优先做：

1. Docling/Unstructured offline sample script。
2. 输出 External UIR。
3. 继续走 External UIR API/UI。
4. 不进入主服务默认依赖。

---

# 最终成熟形态总结

当全部路线完成后，SchemaPack Agent 应具备以下成熟特征：

1. **多源兼容**：通过 adapter framework 接收不同外部 UIR。
2. **Schema 治理**：schema/template 可版本化、可测试、可 diff、可 draft、可 review。
3. **证据化映射**：每条 mapping 都有 source evidence、risk、confidence 和 badcase protection。
4. **人审闭环**：review 不只是确认，而是形成可控知识增长。
5. **LLM 安全使用**：DeepSeek 只做 suggestion，不自动改变生产规则。
6. **可信成果包**：Package 有 manifest、hash、verifier、metadata、canonical、reports。
7. **持续评测**：Evaluation Center 量化每次改动影响。
8. **下游友好**：CSV、RAG JSONL、training corpus、consumer contract 可验证。
9. **可集成**：API、CLI、SDK、Webhook、Adapter plugin template。
10. **边界清晰**：不重造 OCR，不重造完整 RAG，不做企业级 SSO/多租户，除非作为后续部署工程。

---

# Codex 最终交付要求

每完成一个阶段，请提交：

```text
1. 修改文件列表
2. 新增 API 列表
3. 新增配置项
4. 新增测试
5. 运行过的命令
6. 关键指标
7. 是否影响主链路
8. 是否有 badcase violation
9. 是否有 LLM auto-accepted
10. 是否有 secret redaction 证据
11. 剩余问题
12. 下一阶段建议
```

交付摘要模板：

```text
## Phase X 完成摘要

### 修改范围
- ...

### 新增能力
- ...

### 安全边界
- LLM auto accepted: 0
- Badcase violations: 0
- Secret leak: 0

### 验证命令
[在这里粘贴 PowerShell 命令]

### 验证结果
- backend tests:
- ruff:
- frontend build:
- external uir eval:
- package verification:

### 已知限制
- ...

### 下一步
- ...
```

---

## 附录 A：推荐新增文件清单

```text
backend/app/adapters/base.py
backend/app/adapters/registry.py
backend/app/adapters/builtin/block_list_adapter.py
backend/app/adapters/builtin/section_tree_adapter.py
backend/app/adapters/builtin/topic11_adapter.py
backend/app/schemas/adapter.py
backend/app/services/schema_draft_service.py
backend/app/services/template_draft_service.py
backend/app/services/evaluation_center_service.py
backend/app/services/dataset_registry_service.py
backend/app/api/v1/schema_drafts.py
backend/app/api/v1/evaluation_center.py
backend/tests/test_adapter_registry.py
backend/tests/test_schema_draft_service.py
backend/tests/test_evaluation_center.py
scripts/eval_adapters.py
scripts/eval_schema_router.py
scripts/check_regression_gates.py
scripts/verify_consumer_contract.py
scripts/schemapack_cli.py
templates/adapter_plugin/
contracts/rag_corpus_contract_v1.json
contracts/training_corpus_contract_v1.json
contracts/structured_csv_contract_v1.json
```

## 附录 B：不要做的事情

```text
不要直接接收 PDF/Word/Excel/image 作为主服务输入
不要放宽标准 UIRDocument
不要把 DeepSeek 输出直接写入 accepted mapping
不要自动激活 schema/template
不要删除 required fields 提升指标
不要删除 badcase 提升 recall
不要让 external-uir/import 自动创建 task
不要让 external-uir/create-task 自动执行 task
不要把 API key 写入仓库
不要混入无关 npm lockfile 变化
```

## 附录 C：推荐最终项目宣传语

> SchemaPack Agent 是一个面向多源文档智能体的 Schema 化治理与可信成果包生成平台。它位于上游文档解析器和下游 RAG/训练/结构化消费之间，负责把不同来源的 UIR 规范化为可验证、可追溯、可人审演化、可持续评测的标准成果包。
