# SchemaPack Agent 课题 5 后续深化执行文档（不含答辩验收事项）

> **历史执行文档**：本文保留当时的深化计划；当前实现与验证基线见 [`../project_status.md`](../project_status.md)。

> 适用对象：Codex / 代码执行模型  
> 项目边界：继续深化课题 5「数据格式标准化转换智能体」，不横向实现课题 2/3/4/6/11 的完整能力。  
> 当前基线：项目已完成核心 `UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP` 链路，并已有 FastAPI 后端、React/Vite 前端、Review/Knowledge、Package Verifier、Docker Compose、生产化 evaluator 与下游 smoke 脚本。  
> 本文目标：给 Codex 一份可直接执行的详细开发蓝图，聚焦“内容组织深化、映射可信度、成果包协议、轻量生产化治理、工程稳定性”。

---

## 0. 给 Codex 的总指令

请先完整阅读本仓库中的以下文件，再开始修改代码：

```text
README.md
docs/service_migration_plan.md
docs/requirement_mapping.md
docs/badcase_analysis.md
docs/demo_workflow.md
docs/deployment.md
docs/api_usage_examples.md
docs/final_handoff_status.md
```

执行时必须遵守：

1. **不破坏现有主链路**：现有 demo、evaluator、package smoke、frontend build 必须继续可运行。
2. **不把项目扩展成其他课题**：不实现原始 PDF/Word/Excel/OCR 解析，不实现完整清洗/归一/质检/全量 RAG/模型训练平台。
3. **默认确定性**：新增能力默认使用确定性规则，不依赖外部大模型。LLM 只能作为可选 review-required suggestion，不得自动写入生产映射。
4. **保持向后兼容**：已有 API、已有 report name、已有 package 文件名尽量不变；新增字段必须以 optional/兼容方式加入。
5. **先测试后收口**：每个 Phase 完成后至少运行对应单元测试；全部完成后运行完整验证命令。
6. **每个 Phase 都要能单独提交**：不要一次性做过多跨层改动；后端 schema、service、API、frontend、docs、tests 分阶段推进。

---

## 1. 当前项目能力基线

根据现有文档，当前项目已经具备：

```text
UIR document import
Schema/template catalog governance
Field candidate extraction
Deterministic mapping
Transform
Canonical model build
Render to content.json/content.md/chunks.jsonl
Chunk organization summaries/keywords/tags/source links
Validation
Manifest
Package ZIP creation
Package verifier
Review approve/reject
Knowledge candidates and packs
Effective template resolution
Optional LLM fallback adapter
Frontend workbench
Docker Compose deployment
Downstream package smoke scripts
Training-corpus JSONL export
Production-like evaluator
```

因此后续开发不应该重写主链路，而应该在以下位置做增强：

```text
backend/app/schemas/*
backend/app/services/chunk_organizer_service.py 或同类内容组织服务
backend/app/services/mapping_service.py
backend/app/services/package_service.py
backend/app/services/package_verifier_service.py
backend/app/services/manifest_service.py
backend/app/api/v1/*
frontend/src/*
scripts/*
docs/*
examples/production_like/*
tests/*
```

实际文件名以仓库当前结构为准。修改前请用搜索确认已有类名、函数名、字段名，不要凭空创建重复服务。

---

## 2. 总体开发目标

本轮开发不处理答辩材料和验收报告，只做工程深化。目标分为 5 个主方向：

1. **内容组织深化**  
   在现有 chunk organization 基础上增强结构感知分段、表格/列表/代码保护、父子块、多策略配置、chunk 质量标记，但不实现完整课题 11。

2. **字段映射可信度与复核体验增强**  
   为每条 mapping 增加 evidence、confidence、risk_flags、review_required_reason，让人工复核更可解释。

3. **成果包协议规范化与严格校验**  
   固化 `standard_package.zip` 内部文件协议、manifest 版本、role/media type、严格 verifier 模式、package spec 文档。

4. **轻量生产化治理**  
   增加可选 API Key 鉴权、操作审计日志、包下载访问控制、artifact retention 清理脚本；保持默认本地 demo 不受影响。

5. **工程稳定性收口**  
   增加统一验证脚本、CI、OpenAPI 更新、文档更新，降低后续交给低智能模型维护时的风险。

---

## 3. 明确不做的事项

以下事项本轮禁止实现，最多保留接口说明或 TODO：

```text
1. 原始 PDF / Word / Excel / PPT / 图片 / OCR 解析。
2. 完整数据清洗、脱敏、术语归一、实体链接。
3. 完整向量数据库、完整 RAG 问答服务、线上检索问答 UI。
4. 自动生成训练数据的大规模平台。
5. 让 LLM 自动激活知识规则或自动接受字段映射。
6. 多租户复杂权限系统、SSO、TLS 终止、企业级密钥管理平台。
7. 大规模数据库迁移框架重构，除非当前项目已有迁移机制。
```

边界解释：课题 5 的核心是“标准化转换与成果包封装”。它可以为 RAG 和训练语料输出数据，但不负责建设完整 RAG 或训练平台。

---

# Phase 23：内容组织深化

## 23.1 目标

增强当前 `ChunkOrganizerService` 或同等服务，使它从“基础 chunk 增强”升级为“可配置、结构感知、可追溯、可下游消费”的内容组织模块。

本 Phase 不要求真实语义 embedding，也不要求完整 RAG。优先做 deterministic heuristic：标题层级、source block、文本长度、句子边界、表格/列表/代码块保护。

## 23.2 预期输出

完成后，每个 `chunks.jsonl` row 应尽量包含以下字段。若已有字段同义，则复用已有字段；不要随意破坏旧字段。

```json
{
  "chunk_id": "chunk_task_xxx_0001",
  "parent_chunk_id": null,
  "doc_id": "doc_xxx",
  "task_id": "task_xxx",
  "schema_id": "policy_doc",
  "schema_version": "1.0.0",
  "template_id": "policy_doc_base_v1",
  "template_version": "1.0.0",
  "title": "制度总则",
  "title_path": ["制度文件", "制度总则"],
  "chunk_index": 1,
  "strategy": "heading_aware",
  "text": "...",
  "token_estimate": 356,
  "char_count": 928,
  "source_block_ids": ["block_001", "block_002"],
  "source_links": [
    {
      "block_id": "block_001",
      "source_path": "blocks[0]",
      "page": 1,
      "anchor": null
    }
  ],
  "content_tags": ["制度", "管理"],
  "management_tags": ["schema:policy_doc", "template:policy_doc_base_v1"],
  "quality_tags": ["source_linked", "length_ok"],
  "entity_tags": [],
  "summary": "...",
  "keywords": ["制度", "审批", "管理"],
  "quality_flags": [],
  "created_by": "ChunkOrganizerService",
  "organization_trace": {
    "split_reason": "heading_boundary",
    "merge_reason": null,
    "protected_blocks": []
  }
}
```

注意：字段名称要结合现有实现调整；不要重复产生两个含义相同但名称不同的字段。

## 23.3 新增配置

为 task options 增加内容组织配置。建议结构如下：

```json
{
  "content_organization": {
    "chunk_strategy": "heading_aware",
    "target_tokens": 768,
    "min_tokens": 128,
    "max_tokens": 1024,
    "overlap_tokens": 80,
    "protect_tables": true,
    "protect_lists": true,
    "protect_code_blocks": true,
    "enable_parent_child": false,
    "enable_light_semantic_boundary": true,
    "summary_mode": "deterministic",
    "keyword_mode": "deterministic"
  }
}
```

默认值必须保持旧行为兼容。若用户没有传 options，现有 demo 不应报错。

建议支持的 `chunk_strategy`：

```text
fixed_window
heading_aware
source_block_aware
table_protect
parent_child
```

其中：

- `fixed_window`：作为 baseline，按字符/估算 token 切分，尽量不破句。
- `heading_aware`：优先按标题层级和段落边界组合 chunk。
- `source_block_aware`：优先保持 UIR block 不被拆散。
- `table_protect`：表格、列表、代码块作为不可截断单元，必要时整体成为一个 chunk。
- `parent_child`：生成父 chunk 与子 chunk，父 chunk 用于上下文聚合，子 chunk 用于精细检索。

## 23.4 后端实现步骤

### 23.4.1 检查现有 schema

先搜索：

```powershell
rg "Chunk" backend/app
rg "content_organization" backend/app
rg "ChunkOrganizer" backend/app
rg "chunks" backend/app/services backend/app/schemas
```

确认当前 chunk row 的 Pydantic 模型位置。如果已有模型，扩展它；如果目前是 dict，也优先新增一个内部 dataclass/Pydantic model 进行约束，但不要大规模重构所有服务。

### 23.4.2 新增或扩展内容组织选项模型

可能位置：

```text
backend/app/schemas/output_profile.py
backend/app/schemas/reports.py
backend/app/schemas/package.py
backend/app/schemas/content_organization.py  # 若已有类似文件则不要新建重复概念
```

建议模型：

```python
class ContentOrganizationOptions(BaseModel):
    chunk_strategy: Literal[
        "fixed_window",
        "heading_aware",
        "source_block_aware",
        "table_protect",
        "parent_child",
    ] = "heading_aware"
    target_tokens: int = 768
    min_tokens: int = 128
    max_tokens: int = 1024
    overlap_tokens: int = 80
    protect_tables: bool = True
    protect_lists: bool = True
    protect_code_blocks: bool = True
    enable_parent_child: bool = False
    enable_light_semantic_boundary: bool = True
    summary_mode: Literal["none", "deterministic"] = "deterministic"
    keyword_mode: Literal["none", "deterministic"] = "deterministic"
```

校验要求：

```text
min_tokens > 0
max_tokens >= min_tokens
target_tokens between min_tokens and max_tokens
overlap_tokens >= 0
overlap_tokens < target_tokens
```

### 23.4.3 token 估算函数

不要引入大型 tokenizer 依赖。新增轻量函数：

```python
def estimate_tokens(text: str) -> int:
    # 中文按字符粗略估计，英文按词粗略估计
    # 简单、确定性、无外部依赖
```

建议策略：

```text
- 空文本：0
- 中文字符：每 1.5~2 个汉字约 1 token，可用 len(cjk_chars) // 2
- 英文/数字：按 whitespace split 估算
- 标点符号少量计入
```

不要求非常准，要求稳定、可解释。

### 23.4.4 结构识别辅助函数

在服务内部新增小函数，避免把逻辑写成大块 if：

```python
def is_heading_block(block) -> bool: ...
def is_table_block(block) -> bool: ...
def is_list_block(block) -> bool: ...
def is_code_block(block) -> bool: ...
def get_title_path(block, current_heading_stack) -> list[str]: ...
def get_source_link(block) -> dict: ...
def safe_join_blocks(blocks) -> str: ...
def split_on_sentence_boundary(text, max_tokens) -> list[str]: ...
```

兼容不同 UIR block 字段名。读取 block 属性时用 `getattr` 或模型字段，不要对不存在字段直接索引。

### 23.4.5 table/list/code 保护

保护规则：

```text
1. 如果 block 类型为 table/list/code，默认不切开。
2. 如果单个 protected block 超过 max_tokens，不强行切碎，标记 quality_flags: ["oversized_protected_block"]。
3. 保护块与前后文本是否合并由 token 长度决定；超过 max_tokens 时独立成 chunk。
4. content_organization_report 中统计 protected_blocks_count 和 oversized_protected_blocks_count。
```

### 23.4.6 parent-child chunk

当 `enable_parent_child=true` 或 `chunk_strategy=parent_child` 时：

```text
1. 父 chunk：按一级/二级标题聚合，文本可较长，但要保留 max_tokens 质量标记。
2. 子 chunk：按 heading/source block/table protect 策略切分。
3. 每个子 chunk 的 parent_chunk_id 指向父 chunk。
4. 父 chunk 和子 chunk 都写入 chunks.jsonl，但 role 或 granularity 要区分。
```

建议字段：

```json
{
  "granularity": "parent" | "child"
}
```

若已有 chunk schema 不方便加字段，可放入 `metadata` 或 `organization_trace`。

### 23.4.7 content_organization_report 扩展

报告新增：

```json
{
  "strategy": "heading_aware",
  "options": {},
  "summary": {
    "chunk_count": 12,
    "parent_chunk_count": 0,
    "child_chunk_count": 12,
    "avg_token_estimate": 530,
    "min_token_estimate": 120,
    "max_token_estimate": 990,
    "length_ok_count": 10,
    "oversized_count": 1,
    "empty_chunk_count": 0,
    "source_linked_count": 12,
    "protected_blocks_count": 3,
    "oversized_protected_blocks_count": 0
  },
  "quality_flags_summary": {
    "oversized_chunk": 1
  },
  "chunks": [
    {
      "chunk_id": "...",
      "token_estimate": 530,
      "quality_flags": [],
      "source_block_ids": ["..."]
    }
  ]
}
```

不要把完整 chunk text 在报告中重复大量写入，避免报告过大。可只放 preview 或摘要。

## 23.5 前端实现步骤

前端 workbench 增加内容组织配置区，建议放在 task creation 或 execute options 附近。

### 23.5.1 UI 控件

新增：

```text
Chunk strategy 下拉框：fixed_window / heading_aware / source_block_aware / table_protect / parent_child
Target tokens 输入框
Min tokens 输入框
Max tokens 输入框
Overlap tokens 输入框
Protect tables checkbox
Protect lists checkbox
Protect code blocks checkbox
Enable parent-child checkbox
```

默认值与后端一致。

### 23.5.2 Chunk preview 增强

Chunk preview 卡片显示：

```text
chunk_id
strategy
granularity
parent_chunk_id
title_path
token_estimate
source_block_ids
content_tags
management_tags
quality_tags
quality_flags
summary
keywords
text preview
```

如果 `quality_flags` 非空，用明显但不夸张的样式提示。

## 23.6 测试要求

新增或扩展测试：

```text
test_chunk_options_defaults_are_backward_compatible
test_heading_aware_chunks_preserve_title_path
test_table_blocks_are_not_split
test_oversized_protected_block_gets_quality_flag
test_parent_child_chunks_have_parent_ids
test_content_organization_report_summary_is_stable
test_package_verifier_accepts_enriched_chunks
test_task_execute_with_content_organization_options
```

运行：

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..\frontend
npm run build
```

## 23.7 完成标准

```text
1. 无 options 时旧 demo 继续正常运行。
2. 新 options 可通过 API task options 传入。
3. chunks.jsonl 包含增强元数据。
4. content_organization_report 有策略、统计和质量标记。
5. PackageVerifier 不因新增字段失败。
6. 前端可以选择策略并查看增强 chunk preview。
7. 后端测试、ruff、前端 build 通过。
```

---

# Phase 24：字段映射可信度与复核体验增强

## 24.1 目标

让 mapping report 从“告诉用户映射结果”升级为“解释为什么这样映射、风险在哪里、是否需要复核”。

这对课题 5 非常关键：字段语义对齐歧义多，必须能够展示规则来源、置信度、证据、风险标记，并保持 badcase 防护。

## 24.2 预期字段

为每条 mapping decision 增加或补齐：

```json
{
  "target_field": "effective_date",
  "source_field": "生效时间",
  "source_path": "metadata.effective_date",
  "value_sample": "2026-06-01",
  "strategy": "alias",
  "confidence": 0.95,
  "confidence_tier": "high",
  "status": "accepted" | "review_required" | "failed",
  "evidence": [
    {
      "type": "alias_match",
      "message": "Source field matched alias '生效时间' for target field 'effective_date'.",
      "weight": 0.95
    }
  ],
  "risk_flags": [],
  "badcase_filter": {
    "checked": true,
    "blocked": false,
    "reason": null
  },
  "review_required_reason": null,
  "llm_metadata": null
}
```

风险标记建议：

```text
low_confidence
conflicting_candidates
type_mismatch
required_field_unmapped
fuzzy_match
llm_suggestion
badcase_blocked
ambiguous_alias
missing_value_sample
archived_template_blocked
```

置信度等级：

```text
high: confidence >= 0.90
medium: 0.70 <= confidence < 0.90
low: confidence < 0.70
```

规则可调整，但必须集中定义，不能散落在多个文件。

## 24.3 后端实现步骤

### 24.3.1 搜索现有 mapping 模型

```powershell
rg "FieldMapping" backend/app
rg "MappingReport" backend/app
rg "confidence" backend/app/services backend/app/schemas
rg "review_required" backend/app/services backend/app/schemas
```

确认是否已有字段。优先扩展现有模型，不要引入重复模型。

### 24.3.2 新增 MappingEvidence 模型

建议位置：

```text
backend/app/schemas/mapping.py
```

示例：

```python
class MappingEvidence(BaseModel):
    type: str
    message: str
    weight: float | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

如已有 Evidence/Trace 模型，请复用。

### 24.3.3 新增 MappingRisk/Confidence 工具函数

建议在 `MappingService` 内或独立 helper：

```python
def confidence_tier(confidence: float | None) -> str:
    ...

def risk_flags_for_mapping(mapping, candidate, schema_field, context) -> list[str]:
    ...

def review_reason_for_mapping(risk_flags, confidence, strategy) -> str | None:
    ...
```

规则示例：

```text
1. strategy == exact 且类型兼容：high，无 review。
2. strategy == alias 且 alias 来源于 active template/knowledge pack：high 或 medium。
3. strategy == regex：取决于 regex rule confidence，默认 medium-high。
4. strategy == type：默认 medium 或 low，通常需要结合唯一候选判断。
5. strategy == fuzzy：默认 review_required，除非已有非常高相似度且无冲突；建议仍保守。
6. strategy == llm：永远 review_required，risk_flags 包含 llm_suggestion。
7. 出现 badcase 命中：必须 review_required 或 blocked，不得 accepted。
8. required target 未映射：status failed/review_required，risk_flags 包含 required_field_unmapped。
```

### 24.3.4 MappingReport summary 稳定化

当前文档中提到 `MappingReport.summary` 是 flexible dict，未来可能漂移。此 Phase 应锁定常用 key：

```json
{
  "total_target_fields": 10,
  "mapped_count": 8,
  "accepted_count": 6,
  "review_required_count": 2,
  "failed_count": 0,
  "required_unmapped_count": 0,
  "avg_confidence": 0.87,
  "strategy_counts": {
    "exact": 3,
    "alias": 2,
    "regex": 1,
    "type": 1,
    "fuzzy": 1,
    "llm": 0
  },
  "risk_flag_counts": {
    "fuzzy_match": 1,
    "low_confidence": 1
  },
  "badcase_blocked_count": 0,
  "llm_suggestion_count": 0
}
```

不要删除旧 summary key；如果必须重命名，保留兼容 alias。

### 24.3.5 Review record 关联 evidence

Review API 中的 pending review item 应能展示：

```text
target_field
source_field
value_sample
confidence
strategy
evidence
risk_flags
review_required_reason
```

如果当前 review record 不存这些字段，可通过 mapping report 动态读取，或将关键快照写入 review record metadata。

注意：历史 review record 不应因缺少 evidence 而读取失败。

## 24.4 前端实现步骤

### 24.4.1 Mapping Review Table

在前端 mapping report 区域增加表格：

```text
Target Field | Source Field | Value Sample | Strategy | Confidence | Status | Risk Flags | Review Reason | Actions
```

交互要求：

```text
1. 点击行展开 evidence 列表。
2. risk_flags 非空时显示 badge。
3. confidence 用数字 + tier 文本展示，不需要复杂图表。
4. LLM suggestion 显示“需要人工复核”，不得显示为自动通过。
5. failed/required unmapped 明显提示。
```

### 24.4.2 Review Queue 增强

Review queue item 增加：

```text
strategy
confidence
risk_flags
review_required_reason
evidence preview
```

Approve/Reject 逻辑沿用现有 API。

## 24.5 测试要求

新增或扩展：

```text
test_exact_mapping_has_high_confidence_evidence
test_alias_mapping_records_alias_evidence
test_fuzzy_mapping_is_review_required_with_risk_flag
test_llm_suggestion_is_always_review_required
test_badcase_blocked_mapping_is_not_accepted
test_required_unmapped_field_has_risk_flag
test_mapping_summary_contains_stable_keys
test_review_records_include_mapping_evidence_snapshot
```

前端：

```text
npm run build
```

如项目已有前端测试框架，则补基本组件测试；若没有，不强制引入。

## 24.6 完成标准

```text
1. mapping_report 中每条 mapping 都有 evidence/risk/confidence 信息。
2. review_required 的原因可解释。
3. badcase 与 LLM suggestion 继续保持不可自动接受。
4. 前端可读性明显提升。
5. 旧 evaluator 不因新增字段失败。
6. 后端测试、ruff、前端 build 通过。
```

---

# Phase 25：成果包协议规范化与严格校验

## 25.1 目标

把当前成果包从“能生成、能下载、能 smoke test”升级为“有正式协议、有版本、有严格校验、有下游读取说明”。

这不只是写文档，也要让 PackageVerifier 支持 strict mode。

## 25.2 标准包结构

固定标准成果包结构，建议写入 `docs/package_spec.md`：

```text
standard_package.zip
├── manifest.json
├── content.json
├── content.md
├── chunks.jsonl
├── canonical.json
├── mapping_report.json
├── transform_report.json
├── validation_report.json
├── content_organization_report.json
├── verifier_report.json
└── metadata.json                 # 新增，可选但推荐
```

如果当前已生成其他文件，不要删除；可作为 optional artifact 写入 manifest。

## 25.3 manifest 增强

manifest 建议包含：

```json
{
  "manifest_version": "1.1.0",
  "package_format": "schemapack.standard_package",
  "package_version": "1.1.0",
  "created_at": "2026-xx-xxTxx:xx:xxZ",
  "generator": {
    "name": "SchemaPack Agent",
    "version": "..."
  },
  "task": {
    "task_id": "...",
    "doc_id": "...",
    "schema_id": "...",
    "schema_version": "...",
    "template_id": "...",
    "template_version": "...",
    "execution_snapshot_hash": "..."
  },
  "files": [
    {
      "path": "content.json",
      "role": "machine_readable_content",
      "media_type": "application/json",
      "size_bytes": 1234,
      "sha256": "...",
      "required": true
    }
  ]
}
```

role 建议枚举：

```text
manifest
machine_readable_content
human_readable_content
chunks
canonical_model
mapping_report
transform_report
validation_report
content_organization_report
verifier_report
metadata
auxiliary_report
```

media type 建议：

```text
application/json
text/markdown
application/x-ndjson
text/plain
application/zip
```

## 25.4 metadata.json

新增 `metadata.json`，用于给下游快速识别包，不必读取全部报告：

```json
{
  "package_format": "schemapack.standard_package",
  "package_version": "1.1.0",
  "doc_id": "...",
  "task_id": "...",
  "schema": {
    "schema_id": "policy_doc",
    "version": "1.0.0"
  },
  "template": {
    "template_id": "policy_doc_base_v1",
    "version": "1.0.0"
  },
  "content": {
    "chunk_count": 12,
    "has_markdown": true,
    "has_structured_json": true
  },
  "quality": {
    "validation_passed": true,
    "verifier_passed": true,
    "review_required_count": 0,
    "quality_flags": []
  }
}
```

## 25.5 PackageVerifier strict mode

当前 verifier 已检查文件、checksum、JSON、JSONL、Markdown、chunk fields。新增 strict mode：

```python
verify_package(package, strict: bool = False)
```

strict=false：保持旧行为，兼容 demo。

strict=true：额外检查：

```text
1. manifest_version 存在且符合 semver-like 格式。
2. required files 全部存在。
3. 每个 manifest file 都有 path/role/media_type/size_bytes/sha256/required。
4. role 必须在允许枚举中。
5. media_type 与文件扩展名基本匹配。
6. manifest 中 required=true 的文件不能为空。
7. chunks.jsonl 每行必须有 chunk_id/text/source_links 或 source_block_ids。
8. content.json、canonical.json、metadata.json 必须能 parse。
9. verifier_report.json 不能把自己校验为通过后再写入 checksum 产生循环错误。若当前逻辑已处理，保留。
10. manifest 中 sha256 必须和实际文件一致。
```

对第 9 点，如果 verifier_report 是后写入的，manifest 生成顺序可能需要调整：

```text
方案 A：先生成除 verifier_report 外的 manifest，运行 verifier，写 verifier_report，再生成最终 manifest，再可选再次 quick verify。
方案 B：manifest 中允许 verifier_report role，但 verifier_report 只记录前一轮校验结果。
```

优先保持当前可运行逻辑，不要为追求理论完美重构过大。

## 25.6 文档新增

新增：

```text
docs/package_spec.md
```

内容必须包括：

```text
1. 包格式名称与版本。
2. 目录结构。
3. 每个文件用途。
4. manifest 字段说明。
5. chunks.jsonl 字段说明。
6. content.json 与 content.md 的一致性约定。
7. checksum 规则。
8. 下游读取建议。
9. 向后兼容策略。
10. strict verifier 规则。
```

同时更新：

```text
README.md
docs/api_usage_examples.md
docs/deployment.md（如新增 env）
```

## 25.7 下游脚本更新

检查：

```text
scripts/smoke_rag_ingest.py
scripts/export_training_corpus.py
```

要求：

```text
1. 能读取 metadata.json；如果没有则 fallback 到 manifest。
2. 能读取增强 chunks 字段。
3. 不因新增 parent/child chunk 失败。
4. 可选择只导出 granularity=child 的 chunks。
```

建议新增参数：

```text
--granularity child|parent|all
--strict
```

## 25.8 测试要求

```text
test_manifest_has_package_version_and_roles
test_package_contains_metadata_json
test_package_verifier_strict_passes_current_package
test_package_verifier_strict_fails_missing_required_file
test_package_verifier_strict_fails_bad_checksum
test_package_verifier_strict_fails_invalid_jsonl
test_smoke_rag_ingest_supports_enriched_chunks
test_export_training_corpus_supports_granularity_filter
```

## 25.9 完成标准

```text
1. package spec 文档完整。
2. standard_package.zip 包含 metadata.json。
3. manifest 文件 role/media_type/checksum 信息完整。
4. strict verifier 可用。
5. 下游 smoke/export 脚本兼容增强 chunk。
6. 旧 demo 和 evaluator 不受破坏。
```

---

# Phase 26：轻量生产化治理

## 26.1 目标

在不引入复杂企业级权限系统的前提下，补足当前文档中明确缺失的生产化硬化能力：

```text
可选 API Key 鉴权
操作审计日志
包下载访问控制
artifact retention 清理脚本
敏感信息与密钥不落日志
```

必须保持默认本地开发体验不变：不开启鉴权时，现有 demo、tests、frontend 继续运行。

## 26.2 配置项

在配置文件中新增：

```text
API_KEY_AUTH_ENABLED=false
API_KEYS=
AUDIT_LOG_ENABLED=true
AUDIT_LOG_BODY_MAX_CHARS=2000
ARTIFACT_RETENTION_ENABLED=false
ARTIFACT_RETENTION_DAYS=30
ARTIFACT_RETENTION_DRY_RUN=true
PACKAGE_DOWNLOAD_REQUIRES_AUTH=true
```

说明：

```text
1. API_KEY_AUTH_ENABLED=false 时不要求 X-API-Key。
2. API_KEYS 支持逗号分隔多个 key。
3. 日志中不得记录 API_KEYS 原文，只能记录 key hash prefix。
4. PACKAGE_DOWNLOAD_REQUIRES_AUTH 仅在 API_KEY_AUTH_ENABLED=true 时生效。
5. ARTIFACT_RETENTION 默认关闭，避免误删用户数据。
```

## 26.3 API Key 鉴权

### 26.3.1 鉴权规则

当 `API_KEY_AUTH_ENABLED=true`：

```text
1. /health 可匿名访问。
2. /docs、/openapi.json 是否开放由当前 FastAPI 配置决定；建议开发环境开放，生产环境可关闭。
3. /api/v1/* 需要 Header: X-API-Key。
4. key 与 API_KEYS 中任一值匹配则通过。
5. 缺失或错误返回 401。
```

不要实现用户登录、JWT、OAuth、RBAC。

### 26.3.2 实现方式

优先用 FastAPI dependency 或 middleware：

```python
def require_api_key(request: Request, settings: Settings = Depends(...)) -> None:
    ...
```

为了避免改每个 route，可在 router include 时加 dependency，或用中间件按 path 判断。

注意：测试中要能覆盖 auth disabled/enabled。

## 26.4 审计日志

### 26.4.1 AuditLog 数据结构

如果项目已有 SQLAlchemy models，新增表：

```text
audit_logs
```

字段建议：

```text
id / audit_id
created_at
action
entity_type
entity_id
actor_type
actor_id
api_key_hash_prefix
request_id
trace_id
method
path
status_code
success
error_code
metadata_json
```

不要记录：

```text
API key 原文
LLM_API_KEY
请求中的大文本正文全文
上传的完整 UIR 内容
包文件内容
```

metadata_json 可记录摘要：

```json
{
  "schema_id": "policy_doc",
  "template_id": "policy_doc_base_v1",
  "task_id": "...",
  "report_name": "mapping",
  "body_preview": "... truncated ..."
}
```

### 26.4.2 需要审计的动作

至少覆盖：

```text
POST /api/v1/documents/import
POST /api/v1/schemas
POST /api/v1/schemas/{schema_id}/versions/{version}/activate
POST /api/v1/schemas/{schema_id}/versions/{version}/archive
POST /api/v1/templates
POST /api/v1/templates/{template_id}/versions/{version}/activate
POST /api/v1/templates/{template_id}/versions/{version}/archive
POST /api/v1/tasks
POST /api/v1/tasks/{task_id}/execute
POST /api/v1/reviews/{review_id}/approve
POST /api/v1/reviews/{review_id}/reject
POST /api/v1/knowledge/candidates/{candidate_id}/accept
POST /api/v1/knowledge/candidates/{candidate_id}/reject
POST /api/v1/knowledge/packs
POST /api/v1/knowledge/packs/{pack_id}/activate
POST /api/v1/knowledge/packs/{pack_id}/archive
GET  /api/v1/tasks/{task_id}/package/download
```

GET 类查询一般不强制审计，包下载除外。

### 26.4.3 审计日志查询 API

新增只读 API：

```text
GET /api/v1/audit-logs
```

查询参数：

```text
entity_type optional
entity_id optional
action optional
success optional
limit default 50 max 200
offset default 0
```

返回按 created_at desc。

若开启鉴权，该 API 也需要 API key。

### 26.4.4 前端审计视图

简单实现即可：

```text
1. 新增 Audit Logs 面板或任务详情中的 Audit 子面板。
2. 支持按 task_id/entity_id 查询。
3. 显示 created_at/action/entity/status/success/path。
4. metadata 可折叠 JSON。
```

不要做复杂权限 UI。

## 26.5 包下载访问控制

当鉴权开启时：

```text
GET /api/v1/tasks/{task_id}/package/download
```

必须要求 API key。下载事件写入 audit log：

```text
action = package.download
entity_type = task
entity_id = task_id
success = true/false
```

如果鉴权关闭，行为与当前一致。

## 26.6 Artifact retention 清理脚本

新增：

```text
scripts/retention_cleanup.py
```

功能：

```text
1. 扫描 storage/reports/packages 等运行时输出目录。
2. 根据 ARTIFACT_RETENTION_DAYS 或命令行 --days 判断过期文件。
3. 默认 --dry-run，只打印将删除的文件。
4. 只有传入 --delete 才真正删除。
5. 不删除 examples/、docs/、source code、当前 active package。
6. 支持输出 JSON summary。
```

命令示例：

```powershell
python scripts\retention_cleanup.py --days 30 --dry-run
python scripts\retention_cleanup.py --days 30 --delete
python scripts\retention_cleanup.py --days 30 --dry-run --json
```

安全规则：

```text
1. 只能删除配置的 STORAGE_ROOT 下文件。
2. 删除前 resolve path，防止路径穿越。
3. 只删除已知 runtime artifact 后缀或目录。
4. 删除空目录可以做，但必须在 storage root 下。
```

## 26.7 测试要求

```text
test_api_key_auth_disabled_allows_existing_requests
test_api_key_auth_enabled_rejects_missing_key
test_api_key_auth_enabled_accepts_valid_key
test_package_download_requires_auth_when_enabled
test_audit_log_created_for_task_execute
test_audit_log_redacts_api_key_and_llm_key
test_audit_log_query_filters_by_entity
test_retention_cleanup_dry_run_does_not_delete
test_retention_cleanup_delete_removes_only_storage_files
test_retention_cleanup_rejects_path_outside_storage_root
```

## 26.8 文档更新

更新：

```text
docs/deployment.md
.env.example
.env.production.example
README.md
```

说明新增环境变量和示例：

```powershell
$headers = @{ "X-API-Key" = "your-dev-key" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/tasks
```

## 26.9 完成标准

```text
1. 默认不开启鉴权时，所有旧流程无变化。
2. 开启鉴权时，/api/v1/* 受保护，/health 可访问。
3. 关键写操作与包下载有 audit log。
4. audit log 不泄露密钥和大正文。
5. retention cleanup 默认 dry-run 安全可用。
6. 后端测试、ruff、前端 build 通过。
```

---

# Phase 27：工程稳定性与交付维护能力

## 27.1 目标

让项目更容易被后续模型/成员维护：一条命令验证、一份 CI、OpenAPI 保持更新、文档同步。

## 27.2 统一验证脚本

新增：

```text
scripts/verify_all.py
```

功能：

```text
1. 运行 backend pytest。
2. 运行 backend ruff check。
3. 运行 frontend npm run build。
4. 可选运行 production-like evaluator。
5. 可选运行 OpenAPI export 并检查 docs/openapi.json 是否有变更。
```

命令：

```powershell
python scripts\verify_all.py
python scripts\verify_all.py --include-evaluator
python scripts\verify_all.py --skip-frontend
python scripts\verify_all.py --check-openapi
```

实现要求：

```text
1. Windows 友好。
2. 命令失败时打印清楚失败阶段。
3. 不吞 stdout/stderr。
4. 返回正确 exit code。
```

## 27.3 OpenAPI 更新流程

确认当前已有：

```text
scripts/export_openapi.py
docs/openapi.json
```

修改 API 后必须运行：

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

新增文档：

```text
docs/openapi_workflow.md
```

内容：

```text
1. 何时需要重新导出 OpenAPI。
2. 如何导出。
3. 如何检查 diff。
4. API Key 开启时如何调用。
5. 常见问题。
```

## 27.4 CI

如果仓库使用 GitHub，新增：

```text
.github/workflows/ci.yml
```

建议 job：

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install backend dependencies
        run: |
          cd backend
          python -m pip install -r requirements.txt
      - name: Ruff
        run: |
          cd backend
          python -m ruff check .
      - name: Pytest
        run: |
          cd backend
          python -m pytest -q

  frontend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
      - name: Build frontend
        run: |
          cd frontend
          npm run build
```

如果项目没有 package-lock 或 npm ci 不可用，则用 npm install。Codex 需要检查实际 frontend 文件后决定。

是否把 evaluator 放入 CI：

```text
默认不放入每次 CI，避免耗时和不稳定。
可新增 manual job 或 nightly job。
```

## 27.5 文档索引更新

更新 README 的文档索引：

```text
docs/package_spec.md
docs/openapi_workflow.md
docs/deployment.md
docs/api_usage_examples.md
docs/badcase_analysis.md
docs/demo_workflow.md
```

新增 `docs/developer_guide.md`，建议包括：

```text
1. 项目目录结构。
2. 后端服务层说明。
3. 前端 workbench 说明。
4. 如何新增 schema/template。
5. 如何新增 mapping rule。
6. 如何新增 chunk strategy。
7. 如何更新 package spec。
8. 如何运行测试。
9. 常见故障。
```

## 27.6 完成标准

```text
1. scripts/verify_all.py 可运行。
2. CI 文件存在且命令与项目实际结构匹配。
3. OpenAPI 流程文档完整。
4. README 能引导新开发者找到关键文档。
5. 后端测试、ruff、前端 build 通过。
```

---

# Phase 28：可选 LLM 运营安全增强（低优先级，可跳过）

## 28.1 目标

当前 LLM fallback 已经默认关闭、可 stub、可 OpenAI-compatible、始终 review-required。本 Phase 只做运营安全增强，不改变“不得自动接受”的原则。

若时间不足，可跳过 Phase 28。

## 28.2 增强点

```text
1. LLM request timeout 配置。
2. LLM retry 次数配置，默认 0 或 1。
3. 每次 task 最大 LLM suggestion 数量。
4. prompt hash / response hash 已有则保留；没有则补。
5. LLM suggestion 必须进入 mapping evidence。
6. LLM error 不得导致整个 task 失败，除非用户显式设置 strict_llm=true。
7. LLM API key 不得写入 report/audit/log。
8. LLM mode/config 在 task snapshot 中只记录非敏感字段。
```

新增配置：

```text
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=0
LLM_MAX_SUGGESTIONS_PER_TASK=20
LLM_STRICT_FAILURE=false
```

## 28.3 测试要求

```text
test_llm_disabled_is_default
test_llm_stub_suggestion_is_review_required
test_llm_openai_compatible_timeout_records_warning_not_task_failure
test_llm_suggestion_count_is_capped
test_llm_api_key_not_in_reports_or_audit_logs
test_llm_suggestion_has_mapping_evidence
```

---

# 4. 跨 Phase 通用实现规范

## 4.1 向后兼容原则

新增字段：

```text
可以新增 optional 字段。
可以新增 metadata 子对象。
不要删除旧字段。
不要改变旧 report_name。
不要改变旧 package 文件名。
不要让旧 evaluator 因新增字段失败。
```

## 4.2 错误处理规范

所有新增服务错误应返回结构化信息：

```json
{
  "error_code": "PACKAGE_STRICT_VERIFY_FAILED",
  "message": "Required file content.json is missing.",
  "details": {}
}
```

不要只抛出裸字符串异常。

## 4.3 日志与敏感信息

禁止写入日志/报告/audit：

```text
API key 原文
LLM API key
完整大正文
完整 UIR 原文
用户上传的文件内容
```

可写入：

```text
hash
hash prefix
长度
文件名
task_id/doc_id/schema_id/template_id
错误类型
耗时
状态
```

## 4.4 数据库变更规范

如果当前项目没有迁移系统：

```text
1. 尽量只新增表，不改动旧表字段。
2. startup init 能创建新表。
3. 测试使用临时数据库。
4. 文档说明旧 SQLite 如有问题可 docker compose down -v 或手动删除 runtime db。
```

如果已有迁移机制，按现有机制执行。

## 4.5 前端规范

```text
1. 保持当前清爽风格，不引入大而重的 UI 框架，除非项目已有。
2. 新增配置项要有默认值，不让用户必须理解全部参数才能跑 demo。
3. Raw JSON 继续可折叠查看。
4. 表格信息不要塞得过密，优先使用展开行/卡片。
5. API 错误要显示明确 message。
```

## 4.6 文档规范

每新增一个外部可见能力，必须更新至少一个文档：

```text
API 行为变化：docs/api_usage_examples.md 或 docs/openapi_workflow.md
部署配置变化：docs/deployment.md、.env.example、.env.production.example
包格式变化：docs/package_spec.md
开发者工作流变化：docs/developer_guide.md
README 索引：README.md
```

---

# 5. 建议执行顺序

严格建议按以下顺序，不要跳着做：

```text
1. Phase 23：内容组织深化
2. Phase 24：映射可信度与复核体验
3. Phase 25：成果包协议与 strict verifier
4. Phase 26：轻量生产化治理
5. Phase 27：工程稳定性与 CI
6. Phase 28：LLM 运营安全增强（可选）
```

原因：

```text
Phase 23 和 24 是课题 5 能力深化核心。
Phase 25 固化输出协议，避免后续继续漂移。
Phase 26 是生产化补短板，但不应优先于核心能力。
Phase 27 用于最后收口，确保后续可维护。
Phase 28 只有在确实需要启用 LLM 时才有必要。
```

---

# 6. 每个 Phase 的提交建议

每个 Phase 推荐至少拆成这些 commit：

```text
1. backend schemas/options
2. backend service implementation
3. backend API integration
4. backend tests
5. frontend UI integration
6. docs update
```

Commit message 示例：

```text
feat(content): add configurable chunk organization options
feat(mapping): add evidence and risk flags to mapping report
feat(package): add package spec metadata and strict verifier
feat(security): add optional api key auth and audit logs
chore(ci): add verify_all script and github workflow
```

---

# 7. 全量验证命令

所有 Phase 完成后，从仓库根目录运行：

```powershell
# Backend tests
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..

# Frontend build
cd frontend
npm run build
cd ..

# OpenAPI export
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py

# Production-like evaluator
.\backend\.venv\Scripts\python.exe scripts\eval_production_like.py

# Downstream smoke, package path may need to match generated report
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "制度 管理"

# Training corpus export
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl

# Docker compose smoke
 docker compose up --build
```

如果实现了 `scripts/verify_all.py`，最终可改用：

```powershell
python scripts\verify_all.py --include-evaluator --check-openapi
```

---

# 8. 最终交付清单

本轮完成后，仓库应至少新增或更新：

```text
后端：
- 内容组织 options/schema
- chunk organization service 增强
- mapping evidence/risk/confidence 增强
- package metadata/manifest/strict verifier 增强
- optional API key auth
- audit log service/API
- retention cleanup script

前端：
- content organization options UI
- enhanced chunk preview
- mapping evidence review table
- audit log panel 或任务审计视图

脚本：
- scripts/retention_cleanup.py
- scripts/verify_all.py
- smoke/export 脚本兼容增强 chunk

文档：
- docs/package_spec.md
- docs/openapi_workflow.md
- docs/developer_guide.md
- README.md 更新
- docs/deployment.md 更新
- docs/api_usage_examples.md 更新
- .env.example / .env.production.example 更新

测试：
- 内容组织测试
- mapping evidence 测试
- strict verifier 测试
- auth/audit/retention 测试
- API 回归测试
```

---

# 9. 风险与处理策略

## 9.1 新增字段导致 evaluator 失败

处理：新增字段保持 optional；不要修改旧字段名；测试 evaluator。

## 9.2 PackageVerifier 与 manifest 自校验循环

处理：不要盲目重构；先理解当前生成顺序。必要时 strict mode 不强制 verifier_report 自包含 checksum，或采用二阶段 manifest。

## 9.3 前端 options 与后端 options 不一致

处理：后端定义默认值；前端只传用户修改项或传完整默认配置；API 错误清晰显示。

## 9.4 API Key 导致本地 demo 不可用

处理：默认 `API_KEY_AUTH_ENABLED=false`；测试覆盖 disabled 模式。

## 9.5 Audit log 记录过多敏感内容

处理：只记录摘要、ID、hash、长度；写 redaction 测试。

## 9.6 Retention 脚本误删

处理：默认 dry-run；限制在 STORAGE_ROOT；路径 resolve 校验；测试 path traversal。

## 9.7 Chunk 策略过度复杂

处理：先做 deterministic light 版本。不要引入 embedding、向量库、LLM semantic split。

---

# 10. Codex 最小完成路径

如果时间有限，按以下最小路径执行：

```text
1. Phase 23 只做 heading_aware + table_protect + enhanced chunk metadata。
2. Phase 24 只做 mapping evidence + risk_flags + frontend table。
3. Phase 25 只做 docs/package_spec.md + metadata.json + strict verifier 基础检查。
4. Phase 26 只做 API Key auth + audit log，不做 retention endpoint，只做脚本 dry-run。
5. Phase 27 只做 scripts/verify_all.py + README/docs 更新。
```

最小路径完成后，项目的“课题 5 深化程度”会明显提升，同时不会引入过多范围失控风险。

---

# 11. 给 Codex 的开始执行提示词

可以把下面这段直接交给 Codex：

```text
请按照 docs/topic5_followup_execution_plan.md 执行本轮开发。先阅读 README.md、docs/service_migration_plan.md、docs/requirement_mapping.md、docs/badcase_analysis.md、docs/demo_workflow.md、docs/deployment.md、docs/api_usage_examples.md、docs/final_handoff_status.md，确认当前项目结构与服务命名。然后从 Phase 23 开始逐阶段实施，每个 Phase 完成后运行对应测试，不要破坏现有 UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP 主链路。默认不启用 LLM，不实现原始文件解析、完整 RAG 或其他课题能力。每次修改要保持向后兼容，更新必要文档和 OpenAPI。
```
