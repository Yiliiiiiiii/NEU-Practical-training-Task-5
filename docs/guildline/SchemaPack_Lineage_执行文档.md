# SchemaPack-Lineage 可信转换链路执行文档

> 适用项目：SchemaPack Agent 课题 5 成熟化创新扩展  
> 目标读者：Codex / 后续开发执行者  
> 文档目标：在不改变生产边界、不引入 OCR/RAG/模型训练、不破坏现有安全门的前提下，为 SchemaPack Agent 增加一套 **SchemaPack-Lineage 可信转换链路** 能力，使每个目标字段、chunk、package artifact 都可以追溯到源 UIR / External UIR、adapter trace、candidate、mapping decision、review decision、knowledge pack、schema/template snapshot 与最终 package 文件。

---

## 0. 当前项目背景

当前项目已经具备以下基础能力：

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical -> Render -> Content Organization
-> Validate -> Manifest -> ZIP -> Verify
```

当前已实现并验证：

- 标准 UIR 导入、Task 创建、显式执行、报告读取、Package ZIP 下载。
- 5 类内置 catalog family：`contract_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`procurement_doc`。
- 确定性 mapping：exact / alias / regex / type / fuzzy。
- confidence tier、evidence、risk flags、review-required reason、badcase filter。
- Human Review、Knowledge Pack、snapshot preservation。
- External UIR Adapter：block-list / section-tree，当前 fixtures 已扩展到 18 个。
- Schema Router v2、Schema/Template Draft Lab、Review Workbench、Evaluation Center。
- Package 1.1、RAG/training/CSV consumer contracts、CLI、Python SDK、Adapter scaffold。
- Optional offline Docling/Unstructured upstream，但不是 backend runtime API。

本次新增的 SchemaPack-Lineage 不是新增一条转换主链路，而是围绕现有主链路增加一套 **可追溯、可解释、可审计、可展示** 的 lineage 层。

---

## 1. 一句话目标

实现一个字段级、块级、chunk 级、artifact 级的可信转换链路：

```text
External UIR field / Standard UIR block
  -> Adapter Trace
  -> UIR Block
  -> Field Candidate
  -> Mapping Decision
  -> Review Decision / Knowledge Pack
  -> Target Schema Field
  -> Canonical Field
  -> Rendered content.json / content.md / chunks.jsonl
  -> Package Manifest Entry
  -> Downstream Consumer Contract
```

最终用户在前端可以点开任意一个字段或 chunk，看到：

```text
这个结果从哪里来？
经过了哪个 adapter？
对应哪个 UIR block？
候选字段是什么？
为何映射到当前 target field？
是否经过人工 Review？
是否受 Knowledge Pack 影响？
属于哪个 schema/template version？
最后写入了 package 的哪个文件？
是否通过 package contract / regression gate？
```

---

## 2. 核心原则

### 2.1 不改变主生产边界

本项目生产输入仍然是：

```text
UIR 或 External UIR JSON
```

不得新增生产级 raw PDF / Word / Excel / image / OCR upload API。

Optional Docling / Unstructured 仍保持离线工具，不进入 backend 默认依赖。

### 2.2 Lineage 是旁路记录，不是转换决策来源

Lineage 不应该改变 mapping、transform、validation、package 的结果。

Lineage 只记录：

- 输入来源；
- 中间决策；
- 证据路径；
- 版本快照；
- artifact 引用；
- 风险与 review 状态。

### 2.3 不自动接受 LLM suggestion

Lineage 可以记录 LLM suggestion 的来源、prompt hash、response hash、review_required 状态，但不能让 LLM suggestion 自动变成 accepted mapping。

必须保持：

```text
LLM auto accepted = 0
```

### 2.4 不绕过 badcase filter

Lineage 应显式记录 badcase filter 的结果。

如果一个 mapping 被 badcase 阻断，Lineage 应展示为：

```text
mapping_status = blocked
blocked_by = badcase_filter
review_required = true
```

不得为了让链路“完整”而把危险映射补成 accepted。

### 2.5 不污染 source_anchor

当前 `SourceAnchor` 只允许 `page` 与 `bbox`。External path 证据继续放在：

```text
adapter_report.trace_items[]
block.attributes.external_path
lineage.links[].source_path
```

不得写入未定义的：

```text
source_anchor.external_path
```

---

## 3. 非目标

本次不要实现以下内容：

1. 不做 OCR。
2. 不做完整 RAG/vector DB。
3. 不做模型训练或 fine-tuning。
4. 不做企业级 SSO / tenant / RBAC。
5. 不让 LLM 自动激活 schema/template。
6. 不让 lineage 图改变 mapping 结果。
7. 不把 lineage 作为必须通过的语义正确性证明。
8. 不将所有 Review 强行自动化。
9. 不修改历史 package 的结果内容。
10. 不删除 required fields 来提高 strict pass。

---

## 4. 总体架构

建议新增一套 Lineage 层，插入现有主链路的报告生成与 package 生成阶段。

```text
                         ┌────────────────────┐
                         │ External UIR JSON   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ External Adapter    │
                         │ adapter_report      │
                         └─────────┬──────────┘
                                   │
                                   ▼
┌──────────────┐     ┌────────────────────┐
│ UIRDocument  │────►│ CandidateService    │
└──────┬───────┘     └─────────┬──────────┘
       │                       │
       ▼                       ▼
┌──────────────┐     ┌────────────────────┐
│ Schema/      │────►│ MappingService      │
│ Template     │     │ mapping_report      │
│ Snapshot     │     └─────────┬──────────┘
└──────┬───────┘               │
       │                       ▼
       │             ┌────────────────────┐
       │             │ Review / Knowledge │
       │             └─────────┬──────────┘
       │                       │
       ▼                       ▼
┌─────────────────────────────────────────┐
│ Transform / Canonical / Render / Chunk   │
└─────────────────────┬───────────────────┘
                      │
                      ▼
            ┌──────────────────────┐
            │ LineageGraphService   │
            │ lineage_graph.json    │
            │ lineage_summary.json  │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ PackageService        │
            │ manifest + ZIP        │
            └──────────────────────┘
```

---

## 5. 建议新增文件

### 5.1 Backend schemas

新增：

```text
backend/app/schemas/lineage.py
```

建议包含：

```python
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


LineageNodeType = Literal[
    "external_field",
    "adapter_trace",
    "uir_block",
    "field_candidate",
    "mapping_decision",
    "review_decision",
    "knowledge_pack",
    "schema_field",
    "canonical_field",
    "rendered_artifact",
    "chunk",
    "package_manifest_entry",
    "consumer_contract",
]

LineageEdgeType = Literal[
    "derived_from",
    "converted_to",
    "candidate_for",
    "mapped_to",
    "reviewed_by",
    "influenced_by",
    "validated_against",
    "rendered_as",
    "contained_in",
    "verified_by",
]

LineageStatus = Literal[
    "accepted",
    "review_required",
    "blocked",
    "failed",
    "warning",
    "informational",
]


class LineageEvidence(BaseModel):
    evidence_id: str
    evidence_type: Literal[
        "source_text",
        "source_path",
        "adapter_trace",
        "candidate_value",
        "mapping_evidence",
        "review_note",
        "knowledge_rule",
        "manifest_hash",
        "contract_check",
    ]
    text: str | None = None
    path: str | None = None
    block_id: str | None = None
    artifact_path: str | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageNode(BaseModel):
    node_id: str
    node_type: LineageNodeType
    label: str
    status: LineageStatus = "informational"
    doc_id: str | None = None
    task_id: str | None = None
    schema_id: str | None = None
    schema_version: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    field_name: str | None = None
    block_id: str | None = None
    chunk_id: str | None = None
    artifact_path: str | None = None
    confidence: float | None = None
    confidence_tier: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    review_required_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: LineageEdgeType
    confidence: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageGraph(BaseModel):
    graph_id: str
    doc_id: str
    task_id: str | None = None
    package_id: str | None = None
    schema_id: str | None = None
    template_id: str | None = None
    generated_at: str
    lineage_version: str = "1.0"
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    evidence: list[LineageEvidence]
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class LineageQueryResult(BaseModel):
    root_node_id: str
    direction: Literal["upstream", "downstream", "both"]
    max_depth: int
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    evidence: list[LineageEvidence]
    summary: dict[str, Any] = Field(default_factory=dict)
```

### 5.2 Backend services

新增：

```text
backend/app/services/lineage_graph_service.py
backend/app/services/lineage_query_service.py
```

### 5.3 API routes

新增：

```text
backend/app/api/v1/lineage.py
```

并在：

```text
backend/app/api/v1/router.py
```

注册。

### 5.4 Frontend

新增或修改：

```text
frontend/src/components/LineagePanel.tsx
frontend/src/components/LineageGraphView.tsx
frontend/src/components/LineageNodeDetails.tsx
frontend/src/types.ts
frontend/src/styles.css
frontend/src/__tests__/LineagePanel.test.tsx
```

如果当前前端是单文件结构，也可以先在 `frontend/src/App.tsx` 内部实现 MVP，再拆组件。

### 5.5 Scripts

新增：

```text
scripts/eval_lineage_graph.py
scripts/build_lineage_demo_report.py
```

### 5.6 Reports

新增输出：

```text
reports/lineage_eval_report.json
reports/lineage_eval_report.md
reports/lineage_demo_report.json
reports/lineage_demo_report.md
```

### 5.7 Package artifacts

在 package 中新增可选 artifact：

```text
lineage_graph.json
lineage_summary.json
```

注意：如果加入 required artifact，需要同步 package spec、PackageVerifierService、consumer contract。MVP 建议先作为 optional artifact，等稳定后再进入 required contract。

---

## 6. LineageGraph 生成策略

### 6.1 从 External UIR Adapter 生成 lineage

当任务来源于 External UIR 时，应从 adapter report 中生成：

```text
external_field nodes
adapter_trace nodes
uir_block nodes
converted_to edges
```

映射关系示例：

```json
{
  "external_path": "payload.document.sections[0].heading",
  "canonical_path": "blocks[0].text",
  "strategy": "rule",
  "confidence": 1.0,
  "evidence": ["section heading preserved as UIR heading block"]
}
```

应生成：

```text
external_field: payload.document.sections[0].heading
adapter_trace: trace item id
uir_block: blocks[0]
external_field -> adapter_trace -> uir_block
```

### 6.2 从 UIR blocks 生成 lineage

每个 UIR block 生成一个 `uir_block` node。

字段：

```text
node_id = lineage:uir_block:{block_id}
node_type = uir_block
label = block_type + block_id
block_id = block.block_id
metadata.text_preview = first 120 chars
metadata.source_anchor = page/bbox if exists
metadata.external_path = block.attributes.external_path if exists
```

### 6.3 从 CandidateService 生成 lineage

每个 FieldCandidate 生成 `field_candidate` node。

边：

```text
uir_block -> field_candidate
```

如果 candidate 来源于 metadata，则可生成 metadata pseudo-node 或直接在 evidence 中记录：

```text
source_path = metadata.xxx
```

### 6.4 从 MappingService 生成 lineage

每个 mapping decision 生成 `mapping_decision` node。

应记录：

```text
target_field
source_field/source_candidate
strategy
confidence
confidence_tier
risk_flags
review_required
review_required_reason
badcase_filter
```

边：

```text
field_candidate -> mapping_decision
mapping_decision -> schema_field
```

如果 mapping 被 badcase 阻断：

```text
mapping_decision.status = blocked
risk_flags includes badcase_blocked
```

### 6.5 从 Review / Knowledge 生成 lineage

如果 mapping 进入 Review：

```text
mapping_decision -> review_decision
```

如果 Review 生成候选知识：

```text
review_decision -> knowledge_pack
knowledge_pack -> mapping_decision 或 schema_field
```

注意：

- draft pack 不影响当前 task，应标记为 `status=informational`。
- active pack 只影响 future task，应在 task snapshot 中记录其有效上下文。
- rejected candidate 应记录为 negative knowledge，但不能影响 accepted mapping。

### 6.6 从 Transform / Canonical 生成 lineage

每个 canonical field 生成 `canonical_field` node。

边：

```text
schema_field -> canonical_field
mapping_decision -> canonical_field
```

如果该字段来自 default 或 transform rule：

```text
metadata.transform_rule = ...
metadata.default_applied = true/false
```

### 6.7 从 Render / Chunk 生成 lineage

对于 `content.json`：

```text
canonical_field -> rendered_artifact(content.json)
```

对于 `content.md`：

```text
canonical_field / uir_block -> rendered_artifact(content.md)
```

对于 `chunks.jsonl`：

每个 chunk 生成 `chunk` node。

边：

```text
uir_block -> chunk
canonical_field -> chunk   # 如果可确定字段参与 chunk
chunk -> rendered_artifact(chunks.jsonl)
```

chunk node 应记录：

```text
chunk_id
source_block_ids
title_path
strategy
granularity
summary/keywords if exists
quality_tags
```

### 6.8 从 Manifest / Package 生成 lineage

每个 manifest entry 生成 `package_manifest_entry` node。

边：

```text
rendered_artifact -> package_manifest_entry
package_manifest_entry -> consumer_contract
```

记录：

```text
path
role
media_type
sha256
bytes
required
```

---

## 7. API 设计

### 7.1 获取 task lineage graph

```text
GET /api/v1/tasks/{task_id}/lineage
```

返回：

```json
{
  "graph_id": "lineage_task_xxx",
  "doc_id": "...",
  "task_id": "...",
  "lineage_version": "1.0",
  "nodes": [],
  "edges": [],
  "evidence": [],
  "summary": {
    "node_count": 100,
    "edge_count": 120,
    "field_count": 12,
    "review_required_count": 4,
    "badcase_blocked_count": 0,
    "artifact_count": 11,
    "lineage_coverage": 0.98
  },
  "warnings": []
}
```

### 7.2 查询某个字段的 lineage

```text
GET /api/v1/tasks/{task_id}/lineage/fields/{field_name}
```

支持 query params：

```text
direction=upstream|downstream|both
max_depth=8
```

返回 `LineageQueryResult`。

### 7.3 查询某个 chunk 的 lineage

```text
GET /api/v1/tasks/{task_id}/lineage/chunks/{chunk_id}
```

返回该 chunk 来自哪些 block、哪些字段，最终在哪个 package artifact 中。

### 7.4 查询 package artifact lineage

```text
GET /api/v1/tasks/{task_id}/lineage/artifacts/{artifact_path}
```

注意 path 需要 URL encode，例如：

```text
content.json
chunks.jsonl
mapping_report.json
```

### 7.5 获取 lineage summary

```text
GET /api/v1/tasks/{task_id}/lineage/summary
```

用于前端卡片展示。

---

## 8. Storage 与 package 集成

### 8.1 Task report storage

Task 执行完成后，在 task reports 目录写入：

```text
lineage_graph.json
lineage_summary.json
```

建议路径：

```text
storage/tasks/{task_id}/reports/lineage_graph.json
storage/tasks/{task_id}/reports/lineage_summary.json
```

具体路径以当前 StorageService 实现为准。

### 8.2 Package 中包含 lineage

MVP 建议把：

```text
lineage_graph.json
lineage_summary.json
```

作为 optional package artifact 加入 metadata 和 manifest。

如果 PackageVerifierService 当前要求 manifest entries 与 package files 严格一致，则需要：

1. 更新 ManifestService role map；
2. 更新 PackageService 写入逻辑；
3. 更新 PackageVerifierService 允许 lineage artifacts；
4. 更新 `docs/package_spec.md`，说明 lineage 是 traceability artifact；
5. 更新 consumer contract，如果选择把 lineage 加入 contract。

建议先设为：

```json
{
  "path": "lineage_graph.json",
  "required": false,
  "media_type": "application/json",
  "role": "lineage_graph"
}
```

---

## 9. Frontend 设计

### 9.1 新增 Lineage 面板

在工作台中新增：

```text
Lineage / 可信链路
```

建议放在 report inspection 区域，靠近 Mapping Evidence / Validation / Package 面板。

### 9.2 四个核心视图

#### 视图 A：Lineage Summary

展示卡片：

```text
Lineage coverage
Fields traced
Chunks traced
Artifacts traced
Review-required nodes
Badcase-blocked nodes
Knowledge-influenced nodes
Warnings
```

#### 视图 B：Field Lineage

用户选择 target field，例如：

```text
issuer
publish_date
meeting_date
topics
award_amount
```

展示：

```text
Source evidence
Candidate
Mapping decision
Review status
Knowledge influence
Canonical field
Rendered artifact
Package entry
```

#### 视图 C：Chunk Lineage

用户选择 chunk，展示：

```text
chunk_id
title_path
source_block_ids
source text preview
canonical fields if linked
package artifact
```

#### 视图 D：Graph View MVP

不要求第一版做复杂力导向图。

MVP 可以用分层列表：

```text
External Field
  -> Adapter Trace
    -> UIR Block
      -> Candidate
        -> Mapping Decision
          -> Schema Field
            -> Canonical Field
              -> Artifact
                -> Package Manifest
```

后续再考虑 SVG / React Flow。

### 9.3 视觉状态

建议状态：

```text
accepted：正常
review_required：黄色提示
blocked：红色提示
warning：橙色提示
informational：灰色
```

前端不要用颜色作为唯一信息，必须显示文字标签。

### 9.4 固定说明文字

前端必须显示：

```text
Lineage proves traceability and decision history. It does not by itself prove strict semantic correctness. Check validation, review, badcase, and evaluation reports separately.
```

中文可写：

```text
Lineage 证明来源、证据和决策链路可追溯；它不等同于字段语义严格正确。请同时查看 Validation、Review、Badcase 和 Evaluation 报告。
```

---

## 10. Evaluation 设计

新增 evaluator：

```text
scripts/eval_lineage_graph.py
```

### 10.1 输入

```text
--packages-root reports/real_world_packages
--tasks-root storage/tasks 或从 API 获取
--out reports/lineage_eval_report.json
--markdown reports/lineage_eval_report.md
```

如果本地 storage path 不稳定，可以支持 API 模式：

```text
--base-url http://127.0.0.1:8000
```

### 10.2 指标

必须输出：

```text
lineage_graph_count
lineage_parse_pass_count
field_lineage_coverage
chunk_lineage_coverage
artifact_lineage_coverage
mapping_decision_link_rate
review_link_rate
knowledge_pack_link_rate
badcase_blocked_visible_count
manifest_link_rate
orphan_node_count
broken_edge_count
secret_leak_count
llm_auto_accepted_count
```

建议阈值：

```text
lineage_parse_pass_rate = 1.0
field_lineage_coverage >= 0.90
chunk_lineage_coverage >= 0.90
artifact_lineage_coverage >= 0.95
broken_edge_count = 0
secret_leak_count = 0
llm_auto_accepted_count = 0
```

### 10.3 Regression gate

把以下指标接入 Evaluation Center regression gates：

```text
lineage_parse_pass_rate >= 1.0
lineage_broken_edges == 0
lineage_secret_leaks == 0
lineage_field_coverage >= 0.90
```

更新：

```text
reports/evaluation_center/current_metrics.json
reports/evaluation_center/regression_gates.json
```

如果 current_metrics 是由脚本生成，必须修改生成脚本，不要手工改最终报告。

---

## 11. 测试计划

### 11.1 Backend unit tests

新增：

```text
backend/tests/test_lineage_schema.py
backend/tests/test_lineage_graph_service.py
backend/tests/test_lineage_query_service.py
```

测试项：

```text
test_lineage_node_schema_accepts_expected_types
test_lineage_edge_rejects_missing_source_or_target
test_builds_uir_block_nodes
test_links_candidates_to_blocks
test_links_mapping_decisions_to_schema_fields
test_badcase_blocked_mapping_is_visible
test_review_required_mapping_is_visible
test_package_manifest_entries_are_linked
test_no_secret_like_values_in_lineage_metadata
test_query_field_lineage_upstream
test_query_chunk_lineage_upstream
test_query_artifact_lineage_downstream
```

### 11.2 API tests

新增：

```text
backend/tests/test_lineage_api.py
```

测试项：

```text
test_get_task_lineage_returns_graph
test_get_lineage_summary_returns_counts
test_get_field_lineage_returns_subgraph
test_get_chunk_lineage_returns_subgraph
test_unknown_task_returns_404
test_unknown_field_returns_empty_or_404_consistently
test_lineage_api_does_not_expose_secrets
```

### 11.3 Package tests

修改或新增：

```text
backend/tests/test_package_lineage_artifacts.py
```

测试项：

```text
test_package_contains_optional_lineage_artifacts
test_manifest_records_lineage_artifacts
test_verifier_accepts_lineage_artifacts
test_verifier_fails_if_required_lineage_artifact_declared_but_missing
```

如果 lineage artifact 暂不放入 package，可跳过 package tests，但必须在文档中说明 MVP 只提供 API/report，不进入 ZIP。

### 11.4 Frontend tests

新增：

```text
frontend/src/__tests__/LineagePanel.test.tsx
```

测试项：

```text
renders_lineage_summary_cards
renders_field_lineage_path
renders_review_required_status_text
renders_blocked_status_text
shows_traceability_not_semantic_correctness_warning
handles_api_error_gracefully
```

### 11.5 Evaluator tests

新增：

```text
backend/tests/test_eval_lineage_graph_script.py
```

测试项：

```text
test_eval_lineage_graph_outputs_json_and_markdown
test_eval_detects_broken_edges
test_eval_detects_orphan_nodes
test_eval_detects_secret_like_values
test_eval_computes_coverage_rates
```

---

## 12. 分阶段实施计划

### Phase 0：审计现有报告结构

Codex 先阅读：

```text
backend/app/services/task_execution_service.py
backend/app/services/mapping_service.py
backend/app/services/candidate_service.py
backend/app/services/external_uir_adapter_service.py
backend/app/services/package_service.py
backend/app/services/manifest_service.py
backend/app/services/package_verifier_service.py
backend/app/schemas/reports.py
backend/app/schemas/package.py
backend/app/schemas/mapping.py
backend/app/schemas/uir.py
```

确认：

```text
mapping_report 中 mapping decisions 的结构
candidate source_path/source_blocks 字段
validation_report 结构
canonical.json 结构
chunks.jsonl 结构
manifest.json 结构
adapter_report 结构
```

产出：

```text
reports/lineage_design_audit.md
```

### Phase 1：定义 Lineage schema

实现：

```text
backend/app/schemas/lineage.py
backend/tests/test_lineage_schema.py
```

验收：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_lineage_schema.py -q
```

### Phase 2：实现 LineageGraphService MVP

实现：

```text
backend/app/services/lineage_graph_service.py
backend/tests/test_lineage_graph_service.py
```

MVP 先覆盖：

```text
uir_block
field_candidate
mapping_decision
schema_field
canonical_field
rendered_artifact
package_manifest_entry
```

暂不要求 External UIR / Review / Knowledge 完整覆盖，但要预留字段。

### Phase 3：接入 TaskExecutionService

在 task execution 末尾生成：

```text
lineage_graph.json
lineage_summary.json
```

要求：

- 生成失败不能让原本成功的 task 失败，除非显式 strict lineage mode。
- 失败应写入 warning。
- lineage 中不得包含 API keys 或 LLM keys。

建议 task option：

```json
{
  "enable_lineage": true,
  "strict_lineage": false
}
```

默认可以开启 `enable_lineage=true`，但 `strict_lineage=false`。

### Phase 4：Package optional artifact 集成

将 lineage artifacts 加入 package。

修改：

```text
backend/app/services/package_service.py
backend/app/services/manifest_service.py
backend/app/services/package_verifier_service.py
docs/package_spec.md
```

MVP 可选：先只在 reports 中生成，不进 ZIP。如果进 ZIP，必须保证 verifier 和 manifest 一致。

### Phase 5：Lineage API

实现：

```text
backend/app/api/v1/lineage.py
backend/tests/test_lineage_api.py
```

新增 endpoints：

```text
GET /api/v1/tasks/{task_id}/lineage
GET /api/v1/tasks/{task_id}/lineage/summary
GET /api/v1/tasks/{task_id}/lineage/fields/{field_name}
GET /api/v1/tasks/{task_id}/lineage/chunks/{chunk_id}
GET /api/v1/tasks/{task_id}/lineage/artifacts/{artifact_path}
```

更新：

```powershell
backend\.venv\Scripts\python.exe scripts\export_openapi.py
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

注意：OpenAPI paths 数量会增加，不要手工固定为 58。

### Phase 6：External UIR / Adapter trace 接入

增强 LineageGraphService：

```text
adapter_trace nodes
external_field nodes
external_field -> adapter_trace -> uir_block edges
```

如果 task 并非来源于 External UIR，则不生成 external_field nodes，但应保证 graph 有 warning 或 metadata 说明：

```text
source_mode = standard_uir
```

### Phase 7：Review / Knowledge 接入

增强：

```text
review_decision nodes
knowledge_pack nodes
mapping_decision -> review_decision
review_decision -> knowledge_pack
knowledge_pack -> mapping_decision/schema_field
```

必须区分：

```text
draft pack
active pack
rejected candidate
negative knowledge
badcase-blocked candidate
```

### Phase 8：Frontend Lineage Panel

实现：

```text
frontend/src/components/LineagePanel.tsx
frontend/src/components/LineageGraphView.tsx
frontend/src/components/LineageNodeDetails.tsx
frontend/src/__tests__/LineagePanel.test.tsx
```

MVP 可在 `App.tsx` 中集成：

```text
Task 执行完成后显示 Lineage tab
```

前端验收：

```powershell
Push-Location frontend
npm.cmd test
npm run build
Pop-Location
```

### Phase 9：Lineage evaluator 与 Evaluation Center 接入

实现：

```text
scripts/eval_lineage_graph.py
backend/tests/test_eval_lineage_graph_script.py
```

输出：

```text
reports/lineage_eval_report.json
reports/lineage_eval_report.md
```

接入：

```text
Evaluation Center metrics
Regression Gates
Scorecard
```

### Phase 10：文档与 demo

更新：

```text
docs/developer_guide.md
docs/package_spec.md
docs/api_usage_examples.md
docs/demo_workflow.md
docs/交接/final_demo_script.md
docs/交接/project_status.md
docs/交接/final_handoff_status.md
README.md
```

新增：

```text
docs/lineage.md
```

---

## 13. 验收标准

### 13.1 功能验收

| 项目 | 标准 |
| --- | --- |
| Lineage graph 生成 | Task 执行后生成 `lineage_graph.json` 与 `lineage_summary.json` |
| Field lineage | 至少可查询 target field upstream path |
| Chunk lineage | 至少可查询 chunk 对应 source blocks |
| Artifact lineage | 至少可查询 package artifact 的 manifest/hash/role |
| External UIR lineage | External UIR task 能展示 adapter trace |
| Review lineage | review-required mapping 能展示 review 状态 |
| Knowledge lineage | active/draft/rejected/badcase 知识状态可区分 |
| API | lineage endpoints 可用并写入 OpenAPI |
| Frontend | Lineage Panel 可展示 summary 与字段链路 |
| Package | lineage artifacts 若进入 ZIP，verifier 必须通过 |

### 13.2 指标验收

| 指标 | 阈值 |
| --- | --- |
| lineage parse pass rate | 1.0 |
| broken edge count | 0 |
| secret leak count | 0 |
| field lineage coverage | >= 0.90 |
| chunk lineage coverage | >= 0.90 |
| artifact lineage coverage | >= 0.95 |
| badcase violations | 0 |
| LLM auto accepted | 0 |
| package verification | 1.0 |

### 13.3 回归验收

必须运行：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
npm run build
Pop-Location
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

建议运行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
backend\.venv\Scripts\python.exe scripts\eval_external_uir_adapter.py --fixtures examples\external_uir --out reports\external_uir_adapter_eval_report.json --markdown reports\external_uir_adapter_eval_report.md
backend\.venv\Scripts\python.exe scripts\eval_external_uir_api.py --base-url http://127.0.0.1:8000 --fixtures examples\external_uir --out reports\external_uir_api_eval_report.json --markdown reports\external_uir_api_eval_report.md
backend\.venv\Scripts\python.exe scripts\eval_lineage_graph.py --base-url http://127.0.0.1:8000 --out reports\lineage_eval_report.json --markdown reports\lineage_eval_report.md
```

---

## 14. 安全检查

### 14.1 Secret redaction

Lineage metadata 不得包含：

```text
api_key
secret
token
password
authorization
bearer
sk-
```

测试与 evaluator 都要检查 secret-like patterns。

### 14.2 LLM 安全

Lineage 可以记录：

```text
llm_mode
provider_name
suggestion_id
prompt_hash
response_hash
review_required
```

不得记录：

```text
raw API key
完整 prompt 中的敏感内容
完整 provider credential
```

不得让 LLM suggestion 变成 accepted mapping。

### 14.3 Badcase 安全

必须能展示 forbidden mapping 被阻断。

例如：

```text
预算金额 -> award_amount
控制价 -> award_amount
主持人 -> attendees
联系人 -> attendees
成文日期 -> publish_date
retrieved_at -> effective_date
```

如出现自动接受，直接失败。

---

## 15. 推荐 demo 叙事

给评审者展示时，不要把 Lineage 讲成“又一个可视化页面”，而要讲成：

> SchemaPack-Lineage 解决的是标准化转换中的可信追溯问题。它把 External UIR、标准 UIR、字段候选、映射决策、人审、知识包、Schema 快照、Canonical 输出和 Package artifact 串成一条可审计链路。这样下游使用者不仅能拿到结果，还能知道结果从哪里来、为什么这样映射、是否经过人审、是否可复现。

推荐演示路径：

```text
1. External UIR Adapter 面板导入一个 external UIR fixture。
2. Convert & Preview，展示 adapter trace。
3. Import Standard UIR。
4. Create Task 并 Execute。
5. 打开 Mapping Evidence，查看某字段。
6. 切到 Lineage Panel，选择同一个 target field。
7. 展示 external path -> UIR block -> candidate -> mapping -> schema field -> canonical -> package。
8. 打开某个 chunk，展示 chunk 来自哪些 source blocks。
9. 打开 manifest artifact，展示 hash、role、media type。
10. 切到 Evaluation Center，展示 lineage gate 通过。
```

---

## 16. 给 Codex 的直接执行提示词

将以下内容直接交给 Codex：

```text
你现在要在 SchemaPack Agent 项目中实现 SchemaPack-Lineage 可信转换链路。请严格遵守以下要求：

1. 不改变现有主链路：UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping -> Transform -> Canonical -> Render -> Content Organization -> Validate -> Manifest -> ZIP -> Verify。
2. 不新增生产级 raw PDF/Word/Excel/image/OCR upload API。Optional Docling/Unstructured 仍是离线工具。
3. LLM suggestion 只能记录为 review-required，不得自动接受 mapping，不得激活 schema/template。
4. badcase filters 不得关闭，任何 forbidden mapping 自动接受都应失败。
5. Lineage 是旁路记录，不得改变 mapping/transform/package 结果。
6. 实现 backend/app/schemas/lineage.py，定义 LineageNode、LineageEdge、LineageEvidence、LineageGraph、LineageQueryResult。
7. 实现 backend/app/services/lineage_graph_service.py，从 UIR blocks、candidate、mapping_report、schema/template snapshot、canonical、chunks、manifest、adapter_report、review/knowledge 信息生成 lineage graph。
8. 实现 backend/app/services/lineage_query_service.py，支持按 field、chunk、artifact 查询子图。
9. 在 task execution 完成后生成 lineage_graph.json 与 lineage_summary.json。默认 enable_lineage=true，strict_lineage=false；lineage 失败应记录 warning，不应破坏成功 task。
10. 尽量把 lineage_graph.json 和 lineage_summary.json 作为 optional package artifacts 写入 ZIP，并同步 manifest/verifier/package spec；如果风险过高，先只作为 task reports，并在文档中说明。
11. 新增 API：
    - GET /api/v1/tasks/{task_id}/lineage
    - GET /api/v1/tasks/{task_id}/lineage/summary
    - GET /api/v1/tasks/{task_id}/lineage/fields/{field_name}
    - GET /api/v1/tasks/{task_id}/lineage/chunks/{chunk_id}
    - GET /api/v1/tasks/{task_id}/lineage/artifacts/{artifact_path}
12. 更新 OpenAPI，运行 verify_all.py --check-openapi。
13. 新增前端 Lineage Panel，至少支持 summary cards、field lineage、chunk lineage、artifact lineage、review_required/blocked 状态显示，并固定展示“Lineage 不等于 strict semantic correctness”的说明。
14. 新增 scripts/eval_lineage_graph.py，输出 reports/lineage_eval_report.json 和 .md，指标至少包含 parse pass、field coverage、chunk coverage、artifact coverage、broken edges、orphan nodes、secret leaks、LLM auto accepted。
15. 将 lineage 指标接入 Evaluation Center regression gates。
16. 补充 backend tests、frontend tests、evaluator tests。测试必须覆盖 secret redaction、badcase visible、review_required visible、field/chunk/artifact query。
17. 最后运行：
    backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
    Push-Location frontend; npm.cmd test; npm run build; Pop-Location
    backend\.venv\Scripts\python.exe scripts\check_regression_gates.py --metrics reports\evaluation_center\current_metrics.json --gates reports\evaluation_center\regression_gates.json --out reports\evaluation_center\regression_gate_report.json
18. 更新 docs/developer_guide.md、docs/package_spec.md、docs/api_usage_examples.md、docs/demo_workflow.md、docs/交接/final_demo_script.md、docs/交接/project_status.md、docs/交接/final_handoff_status.md、README.md，并新增 docs/lineage.md。
19. 不要手工伪造指标；所有 reports/*.json 和 reports/*.md 必须由脚本生成或明确说明是静态文档。
20. 保持当前项目安全指标：badcase violations = 0，LLM auto accepted = 0，package verification = 1.0。
```

---

## 17. 实施后的预期效果

实现后，项目将从：

```text
可验证的 Schema 化转换平台
```

升级为：

```text
可追溯、可解释、可审计的 Schema 化转换平台
```

它的创新点会更清楚：

```text
不是只输出标准包，而是输出标准包背后的证据链。
不是只告诉你映射成功，而是告诉你字段为什么这样映射。
不是只支持 External UIR，而是能追溯 External UIR 到最终 package 的完整路径。
不是只依赖 LLM，而是把 LLM suggestion 放进人审和安全门之下。
```

这非常贴合课题 5 的深度拓展方向，也不会越界到 OCR、RAG 或模型训练。
