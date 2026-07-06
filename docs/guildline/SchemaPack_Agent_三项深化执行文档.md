# SchemaPack Agent 深化执行文档：非采购质量、Human Review/Knowledge Pack、真实 UIR 数据集增强

> **历史执行文档**：本文保留实施目标与当时指标；当前实现与最新评测见 [`../project_status.md`](../交接/project_status.md)。

> 交付对象：Codex  
> 适用项目：SchemaPack Agent  
> 执行原则：在继续符合课题 5 与任务书整体要求的前提下，围绕现有主线做深，不扩大为 OCR/RAG/模型训练平台。  
> 核心边界：生产运行时仍以 **UIR input → schema-driven package output** 为边界。Raw PDF、Word、Excel、图片、扫描件 OCR 解析不进入 runtime 主链路。

---

## 0. 本轮目标概述

本轮不是重新做项目，也不是横向扩成大平台，而是在当前已符合课题 5 的基础上推进三个深化方向：

```text
1. 补强非采购文档质量
2. 强化 Human Review 与 Knowledge Pack 闭环
3. 把真实 UIR 数据集做得更有说服力
```

最终希望项目从：

```text
能跑通、能生成 verifier-passing package
```

推进到：

```text
非采购文档字段映射更稳；
Review 更有治理意义；
Knowledge Pack 能证明“人审经验影响未来任务但不污染历史结果”；
真实 UIR 数据集不仅正式、真实，而且覆盖更多格式差异、歧义字段和 badcase 场景。
```

---

## 1. 当前基线与必须保持的项目边界

### 1.1 当前核心链路

当前主链路保持不变：

```text
UIR
  -> Schema
  -> Mapping
  -> Transform
  -> Canonical
  -> Render
  -> Validate
  -> Manifest
  -> ZIP Package
```

不要把本轮工作改成：

```text
PDF/Word/OCR -> 自动解析 -> SchemaPack runtime
```

更合适的边界是：

```text
公开官方 HTML / text-layer PDF
        ↓
离线 collector / extractor / UIR builder
        ↓
生成 UIR
        ↓
SchemaPack Agent runtime
        ↓
Schema-governed Package ZIP
```

### 1.2 当前已知评估基线

当前证据大致为：

```text
Real-world dataset size: 30
Real-world pipeline: 30/30 import, 30/30 execution, 30/30 package verification
Real-world mapping recall: 0.48847926267281105
Real-world badcase violations: 0

Non-procurement API-backed evaluator:
- 20/20 package verification
- badcase violations: 0
- required missing: 12
- average recall: 0.4211309523809524
- review-required: 149
- Phase 1 未达标
```

本轮的主要短板不是“Package 生成失败”，而是：

```text
general_doc / meeting_doc / policy_doc 的字段自动映射质量仍不够强；
review-required 数量偏高；
required missing 仍有明显空间；
真实 UIR 数据集的非采购复杂样本和歧义样本还不够多。
```

### 1.3 严格禁止扩大或误报的能力

本轮不要实现或宣称：

```text
1. 生产级 OCR / scanned PDF recognition
2. 完整 RAG / vector database runtime
3. 模型训练 / fine-tuning
4. 自动激活 LLM 生成规则
5. 企业级 SSO / tenant system / TLS / hosted credential system
6. 所有字段语义严格正确
```

可以实现或增强的是：

```text
1. 离线 real-world source collection
2. 离线 UIR builder / validator
3. 非采购字段候选抽取
4. mapping template alias / regex / type / fuzzy 策略
5. Review required 场景治理
6. Knowledge Pack 的 draft / active / archive lifecycle
7. snapshot preservation 与 badcase protections
8. deterministic evaluation reports
```

---

## 2. 本轮总体验收指标

Codex 执行时，不要只看测试是否通过，还要看指标是否真正改善。

### 2.1 必须保持的底线指标

所有阶段都必须保持：

```text
backend tests: pass
ruff: clean
frontend build: successful
OpenAPI export/check: pass
package verification: 不下降
badcase violations: 0
old task snapshot: unchanged
LLM fallback: review-only，不自动接受 mapping
```

统一验证命令：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

### 2.2 本轮建议目标指标

可以根据实际情况微调，但建议把目标写入报告：

```text
Non-procurement average recall:
  从 0.4211 提升到 >= 0.55
  若改动顺利，争取 >= 0.60

Non-procurement review-required:
  从 149 降到 <= 120
  若改动顺利，争取 <= 100

Non-procurement required missing:
  从 12 降到 <= 6
  若改动顺利，争取 <= 4

Badcase violations:
  必须保持 0

Package verification:
  原有 20/20 或扩展后的全部 non-procurement package 均需通过

Real-world dataset:
  从 30 扩到 45–60
  重点增加 general_doc / meeting_doc / policy_doc
```

---

## 3. 第一部分：真实 UIR 数据集增强

### 3.1 目标

当前数据集已经有真实公开正式文档，但还需要补充：

```text
1. 非采购文档
2. 官方但格式不规整的文档
3. 字段表达方式变化大的文档
4. 需要 Review 的歧义样本
5. 可形成 Knowledge Pack 的 approved / rejected / badcase 样本
```

不要简单堆数量，而是做“定向扩充”和“难度扩充”。

### 3.2 推荐扩充规模

当前：

```text
total: 30
non-procurement: 20
procurement_doc: 10
```

建议第一阶段扩到：

```text
total: 45 左右
```

若时间允许，第二阶段扩到：

```text
total: 50–60
```

建议最终分布：

```text
procurement_doc: 10–12
general_doc: 12–15
meeting_doc: 10–12
policy_doc: 15–20
total: 50–60
```

采购文档不必大幅增加。重点放在非采购。

### 3.3 新增样本选择标准

必须满足：

```text
1. 公开官方来源
2. 无需登录
3. 无需付费
4. 无需 CAPTCHA
5. 无需绕过反爬
6. 优先 HTML 或 text-layer PDF
7. 能记录 source URL、source site、retrieval timestamp、source format、SHA-256、extraction method
8. 不含大量个人隐私信息
```

排除：

```text
1. private records
2. copied mirrors
3. news/social posts
4. paid material
5. personal-information-heavy sources
6. scanned PDFs
7. image-only documents
8. 需要 OCR 才能读取的材料
```

### 3.4 各文档类型扩充建议

#### 3.4.1 general_doc

优先收集：

```text
1. 办事指南
2. 政务服务事项页
3. 项目申报指南
4. 补贴/资助申请说明
5. 资格认定/备案指南
6. 服务流程说明
```

重点覆盖字段：

```text
service_object
application_conditions
required_materials
process
deadline
contact
department
service_scope
```

建议加入的格式变化：

```text
1. 字段以表格形式出现
2. 字段以分段标题出现
3. 字段以冒号结构出现
4. 字段被写在自然段中
5. 联系方式、办理地点、办理时限混在一起
6. 条件和材料分布在多个段落
```

#### 3.4.2 policy_doc

优先收集：

```text
1. 政策通知
2. 实施细则
3. 政策办法
4. 申报政策
5. 官方政策解读
6. 部门联合发文
```

重点覆盖字段：

```text
issuer
publish_date
effective_date
policy_target
policy_basis
application_conditions
responsible_department
document_number
policy_scope
```

建议加入的格式变化：

```text
1. 多个 issuer
2. 联合发文
3. 发布日期和实施日期同时出现
4. 标题中含年份但不是发布日期
5. 文号和日期挨得很近
6. 政策对象写在正文而不是显式字段
7. 政策依据分散在前言中
```

#### 3.4.3 meeting_doc

优先收集：

```text
1. 会议纪要
2. 会议记录
3. 专题会议摘要
4. 工作推进会摘要
5. 项目评审会纪要
6. 领导小组会议纪要
```

重点覆盖字段：

```text
meeting_date
meeting_number
attendees
topics
decisions
action_items
host
location
organizer
```

建议加入的格式变化：

```text
1. 会议时间写在正文首段
2. 会议编号缺失
3. 参会人员以列表出现
4. 参会人员以自然段出现
5. 议题和结论混写
6. action items 隐含在“要求”“强调”“决定”中
7. 多个日期同时出现，如发布时间、会议时间、落实期限
```

### 3.5 数据目录与文件要求

新增样本时，不要只加 UIR JSON。必须同步维护：

```text
examples/real_world/sources/source_manifest.json
examples/real_world/uir/
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
examples/real_world/gold/retrieval_queries.jsonl
examples/real_world/review_fixtures/
examples/real_world/reports/
reports/
```

每个新增样本至少要能追踪到：

```text
doc_id
doc_type
source_url
source_site
retrieval_timestamp
source_format
sha256
extraction_method
generated_uir_path
source_block_ids
expected mappings
review-required items
known badcases
retrieval queries
```

### 3.6 Source Manifest 字段建议

如果现有 manifest 字段已经不同，保持兼容；不要破坏旧数据。

建议每条 source 至少包含：

```json
{
  "doc_id": "real_policy_011_example",
  "doc_type": "policy_doc",
  "source_url": "https://example.gov.cn/...",
  "source_site": "example.gov.cn",
  "source_format": "html",
  "retrieval_timestamp": "2026-xx-xxTxx:xx:xxZ",
  "sha256": "lowercase_hex_sha256",
  "extraction_method": "html_text",
  "license_or_access_note": "public official page, no login required",
  "cache_path": "examples/real_world/cache/...",
  "generated_uir_path": "examples/real_world/uir/policy/real_policy_011_example.json"
}
```

### 3.7 UIR 生成要求

新增 UIR 必须满足：

```text
1. strict UIRDocument model
2. filename 与 doc_id 对齐
3. doc_type 正确
4. source URL 为 HTTP(S)
5. source traceability metadata 完整
6. SHA-256 形态正确
7. block IDs 唯一
8. text blocks 非空
9. tables 可 parse
10. 无明显 mojibake
11. 无高风险隐私模式
12. low-confidence candidates 必须进入 review-required
```

运行：

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

### 3.8 Gold Labels 要求

`mapping_gold.jsonl` 不能只标“正确答案”，还要服务于后续改进。

每条 gold row 建议包含：

```json
{
  "doc_id": "real_general_011_example",
  "doc_type": "general_doc",
  "source_path": "blocks[3].text",
  "source_block_ids": ["block_003"],
  "source_label": "申请条件",
  "source_value_excerpt": "申请单位应当...",
  "expected_target": "application_conditions",
  "expected_behavior": "auto_accept_or_review",
  "review_required": false,
  "reason": "explicit heading and field semantics match",
  "known_badcases": []
}
```

对于应进入 Review 的项目：

```json
{
  "doc_id": "real_policy_012_example",
  "doc_type": "policy_doc",
  "source_path": "blocks[5].text",
  "source_label": "联系人",
  "source_value_excerpt": "联系人：张三",
  "expected_target": "issuer",
  "expected_behavior": "reject_or_review",
  "review_required": true,
  "reason": "联系人不是发文机构，不能映射为 issuer"
}
```

### 3.9 Badcase 设计要求

新增 badcase 不要只做采购金额类。非采购也要有 badcase。

建议新增：

```text
policy_doc:
- 联系人 -> issuer：禁止自动接受
- 发布时间 -> effective_date：存在风险，需 evidence 或 review
- 标题中的年份 -> publish_date：禁止自动当作发布日期
- 解读单位 -> issuer：需要区分

general_doc:
- 办理地点 -> department：禁止简单等同
- 咨询电话 -> contact：可映射，但不能映射到 issuer/department
- 服务对象 -> application_conditions：需区分对象与条件
- 材料清单标题 -> required_materials：可接受，但具体材料应保留来源

meeting_doc:
- 发布时间 -> meeting_date：禁止自动接受
- 参会单位 -> attendees：可 review，但不能直接等同完整参会人
- 会议主题 -> decisions：禁止自动接受
- 工作要求 -> action_items：可 review，不应强制 auto-accept
```

### 3.10 Retrieval Queries 要求

`retrieval_queries.jsonl` 用于 deterministic chunk-ranking evidence，不是 full RAG。

每个新增样本至少补 1–3 条 query：

```json
{
  "query_id": "rq_policy_011_issuer",
  "doc_id": "real_policy_011_example",
  "query": "该政策由哪个单位发布？",
  "relevant_source_block_ids": ["block_001", "block_002"],
  "target_field": "issuer"
}
```

必须保证 relevant source block IDs 能回溯到 UIR。

---

## 4. 第二部分：补强非采购文档质量

### 4.1 目标

提高 `general_doc`、`meeting_doc`、`policy_doc` 的 mapping recall，减少 required missing 和无意义 Review，同时保持 badcase violations 为 0。

### 4.2 基线命令

先运行当前基线，不要直接修改代码：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json

backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
```

输出中要明确统计：

```text
average recall
review-required count
required missing count
badcase violations
per-doc-type recall
per-field gap count
gap type:
  candidate_not_extracted
  regex_missing
  wrong_alias
  type_conflict
  semantic_ambiguous
  over_eager_fuzzy
```

### 4.3 优先修复字段

#### general_doc

优先级：

```text
P0:
- application_conditions
- service_object
- required_materials

P1:
- process
- deadline
- contact
- department
```

候选抽取增强方向：

```text
1. 识别“申请条件”“办理条件”“申报条件”“受理条件”“支持条件”
2. 识别“服务对象”“适用对象”“申报主体”“申请主体”“支持对象”
3. 识别“申请材料”“所需材料”“提交材料”“材料清单”
4. 识别“办理流程”“申报流程”“办理程序”“操作流程”
5. 识别“咨询电话”“联系方式”“联系电话”“联系人”
```

#### policy_doc

优先级：

```text
P0:
- issuer
- publish_date
- effective_date

P1:
- policy_target
- application_conditions
- responsible_department
- document_number
```

候选抽取增强方向：

```text
1. 识别“发布单位”“发文机关”“制定机关”“印发单位”
2. 识别正文尾部落款单位
3. 识别联合发文单位
4. 区分 publish_date 与 effective_date
5. 区分 issuer、解读单位、联系人、责任部门
6. 文号识别，如“XX〔2024〕X号”
```

#### meeting_doc

优先级：

```text
P0:
- meeting_date
- topics
- decisions

P1:
- attendees
- action_items
- host
- location
- meeting_number
```

候选抽取增强方向：

```text
1. 识别“会议时间”“时间”“召开时间”
2. 从首段抽取会议日期
3. 识别“会议议题”“议题”“研究事项”“审议事项”
4. 识别“会议决定”“会议要求”“会议强调”“会议指出”
5. 识别“参会人员”“参会单位”“出席人员”“列席人员”
6. 区分发布时间和会议时间
```

### 4.4 代码改动建议

优先检查并修改：

```text
backend/app/services/candidate_service.py
backend/app/services/mapping_service.py
backend/app/services/effective_template_service.py
examples/production_like/mapping_templates/*.json
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
backend/tests/test_candidate_service_non_procurement.py
backend/tests/test_non_procurement_templates.py
backend/tests/test_mapping_service.py
```

如实际项目文件名不同，以现有服务与测试结构为准。

### 4.5 CandidateService 修改要求

不要用过度激进的 fuzzy 直接 auto-accept。推荐：

```text
1. 先增强 candidate extraction
2. 再补 alias / regex
3. 最后才考虑 fuzzy
4. fuzzy 低置信度必须 review-required
5. ambiguous source label 必须进入 Review
```

每个 candidate 建议包含：

```text
source_label
source_value
source_path
source_block_ids
detected_type
extraction_strategy
confidence
evidence
risk_flags
```

### 4.6 Mapping Template 修改要求

新增 alias / regex 时必须同步加 badcase tests。

示例：

```json
{
  "target_field": "issuer",
  "aliases": ["发布单位", "发文机关", "印发单位", "制定机关"]
}
```

但必须避免：

```text
联系人 -> issuer
联系电话 -> issuer
解读人 -> issuer
```

日期 regex 必须区分：

```text
发布日期
印发日期
实施日期
生效日期
会议时间
发布时间
```

不能只要看到日期就映射到某个 date 字段。

### 4.7 Review 降噪原则

Review-required 降低不是靠硬 auto-accept，而是靠：

```text
1. 更好的 source evidence
2. 更明确的 alias
3. 更可靠的 regex
4. 更准确的 type compatibility
5. 更细的 badcase filter
```

仍然必须 Review 的情况：

```text
1. source_label 含糊
2. source_value 语义不足
3. 多个 target field 都可能匹配
4. 日期字段不明确
5. 单位字段可能是 issuer / department / contact / organizer
6. badcase filter 命中
```

### 4.8 非采购质量验收

至少新增或更新报告：

```text
reports/non_procurement_mapping_eval_report.json
reports/non_procurement_mapping_eval_report.md
reports/non_procurement_gap_analysis.json
reports/non_procurement_gap_analysis.md
reports/non_procurement_acceptance_report.md
```

报告必须包含：

```text
before / after 对比
per-doc-type recall
per-field gap reduction
review-required count
required missing count
badcase violations
package verification count
remaining gaps
next steps
```

---

## 5. 第三部分：强化 Human Review 与 Knowledge Pack 闭环

### 5.1 目标

把 Review/Knowledge 从“有 API”推进到“能证明持续改进”的闭环。

需要证明：

```text
1. 低置信度、歧义或风险 mapping 会进入 Review
2. 人工 approve 的 candidate 可以进入 draft pack
3. 只有 active pack 影响 future task
4. rejected candidate 不会进入 active knowledge
5. badcase candidate 不能激活
6. old task snapshot 不会因为新 pack 激活而改变
7. 指标能展示激活前后变化
```

### 5.2 Review 场景设计

新增或完善 `examples/real_world/review_fixtures/`。

至少覆盖三类：

```text
A. 应该批准的 alias
B. 应该拒绝的错误映射
C. 应该阻断的 badcase
```

#### 应该批准的 alias 示例

```text
general_doc:
- “申报主体” -> service_object
- “办理条件” -> application_conditions
- “所需材料” -> required_materials

policy_doc:
- “发文机关” -> issuer
- “印发单位” -> issuer
- “施行日期” -> effective_date

meeting_doc:
- “研究事项” -> topics
- “会议要求” -> action_items
- “出席人员” -> attendees
```

#### 应该拒绝的映射示例

```text
policy_doc:
- “联系人” -> issuer
- “联系电话” -> issuer
- “解读单位” -> issuer，除非 evidence 明确说明其也是发文机关

meeting_doc:
- “发布时间” -> meeting_date
- “会议主题” -> decisions

general_doc:
- “服务对象” -> application_conditions
- “办理地点” -> department，若只是地点而非机构
```

#### 应该阻断的 badcase 示例

```text
1. rejected candidate 被尝试加入 active pack
2. forbidden source/target pair 被激活
3. badcase alias 与 approved alias 冲突
4. draft pack 未激活却影响 mapping
5. active pack 修改旧 task snapshot
```

### 5.3 Knowledge Pack 生命周期要求

必须测试：

```text
pending review
  -> approve / reject
  -> candidate accepted / rejected
  -> draft pack
  -> active pack
  -> effective template resolution
  -> future task uses active pack
  -> old task snapshot unchanged
```

API 示例可参考现有形式：

```powershell
$pending = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
$reviewToApprove = $pending.items[0].review_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/reviews/$reviewToApprove/approve"

$candidates = Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/candidates
$candidateId = $candidates.items[0].candidate_id

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/candidates/$candidateId/accept"

$packBody = @{
  schema_id = "policy_doc"
  template_id = "policy_doc_base_v1"
  name = "policy aliases from review"
  created_by = "demo_user"
} | ConvertTo-Json -Depth 5

$pack = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/knowledge/packs `
  -ContentType "application/json" `
  -Body $packBody

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/knowledge/packs/$($pack.pack_id)/activate"

Invoke-RestMethod "http://127.0.0.1:8000/api/v1/knowledge/effective-template?schema_id=policy_doc&template_id=policy_doc_base_v1"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/metrics
```

### 5.4 Knowledge 评估脚本要求

如果已有脚本可复用，扩展它们；不要另起完全重复脚本。

优先扩展：

```text
scripts/eval_real_world_knowledge_loop.py
scripts/eval_review_knowledge_growth.py
```

新增报告：

```text
reports/real_world_knowledge_loop_report.json
reports/real_world_knowledge_loop_report.md
reports/knowledge_loop_eval_report.json
reports/knowledge_loop_eval_report.md
reports/review_knowledge_growth_report.json
reports/review_knowledge_growth_report.md
```

报告必须包含：

```text
before_mapping_counts
after_mapping_counts
review_required_before
review_required_after
activated_aliases
rejected_candidates_count
badcase_blocked_count
draft_pack_no_effect: true
active_pack_effect: true
old_snapshot_unchanged: true
badcase_violations: 0
```

### 5.5 Knowledge Pack 测试要求

至少新增或更新测试：

```text
test_review_generates_candidates
test_approved_candidate_can_enter_draft_pack
test_rejected_candidate_never_activates
test_badcase_candidate_blocked_before_activation
test_draft_pack_does_not_affect_effective_template
test_active_pack_affects_future_task
test_old_task_snapshot_unchanged_after_pack_activation
test_effective_template_resolution_is_deterministic
test_knowledge_metrics_report_counts
```

---

## 6. 第四部分：三项工作的整合顺序

不要让 Codex 一次性大改。按以下阶段执行。

### Phase 0：基线确认

目标：确认当前状态，不修改代码。

执行：

```powershell
git branch --show-current
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
```

产物：

```text
reports/baseline_before_deepening.md
reports/baseline_before_deepening.json
```

报告要记录：

```text
tests
ruff
frontend build
OpenAPI paths
dataset size
package verification
non-proc recall
review-required
required missing
badcase violations
```

### Phase 1：扩充真实 UIR 数据集

目标：从 30 扩到 45 左右，重点非采购。

步骤：

```text
1. 按 3.3 的标准收集公开官方来源
2. 更新 source_manifest
3. 运行 collector
4. 运行 UIR builder
5. 运行 UIR validator
6. 补 mapping_gold.jsonl
7. 补 real_world_badcases.jsonl
8. 补 retrieval_queries.jsonl
9. 补 review_fixtures
10. 运行 real-world eval
```

验收：

```text
新增样本全部通过 UIR validation
新增样本全部可 import
新增样本全部可 execute
新增样本全部产生 verifier-passing package
badcase violations = 0
```

### Phase 2：补强非采购 Candidate Extraction 与 Mapping

目标：提升 recall，降低 review-required 和 required missing。

步骤：

```text
1. 分析 non_procurement_gap_analysis
2. 按高频字段排序修复
3. 先改 CandidateService
4. 再改 mapping templates
5. 最后调整 MappingService 的 review/risk 策略
6. 每个修复都加测试
7. 每轮运行非采购 eval
```

验收：

```text
average recall >= 0.55
review-required <= 120
required missing <= 6
badcase violations = 0
package verification 全通过
```

如果无法达到目标，报告中必须解释：

```text
哪些字段仍未达标
原因是什么
下一步如何修复
是否因为 gold label 或样本本身存在歧义
```

### Phase 3：Review/Knowledge Pack 闭环增强

目标：证明“人审经验可治理地影响未来任务”。

步骤：

```text
1. 构造 approved / rejected / badcase review fixtures
2. 执行初始 task，记录 before metrics
3. approve 部分 review
4. reject 部分 review
5. candidates accepted/rejected
6. draft pack 创建
7. 验证 draft pack 无影响
8. active pack 激活
9. 验证 future task 受影响
10. 验证 old snapshot unchanged
11. 验证 badcase blocked
12. 输出 knowledge-loop reports
```

验收：

```text
active pack affects future task: true
draft pack no effect: true
old snapshot unchanged: true
rejected candidate activation: 0
badcase activation: 0
badcase violations: 0
review-required after <= before
```

### Phase 4：整合报告与文档更新

目标：让成果能用于验收/答辩/项目交付。

更新：

```text
README.md
docs/real_world_uir_dataset.md
docs/non_procurement_mapping_improvement_plan.md
docs/real_world_knowledge_loop.md
docs/交接/badcase_analysis.md
docs/交接/requirement_mapping.md
docs/交接/final_handoff_status.md
docs/交接/final_demo_script.md
reports/non_procurement_acceptance_report.md
```

注意：文档必须诚实表述。

可以说：

```text
非采购文档 recall 提升；
review-required 下降；
badcase violations 仍为 0；
真实数据集扩展到 X；
active knowledge pack 影响 future task；
old snapshot preserved。
```

不能说：

```text
所有字段语义完全正确；
系统支持 OCR；
系统是完整 RAG；
LLM 能自动学习并激活规则；
Package verification 等于 strict field validity。
```

---

## 7. 最终验收命令清单

Codex 完成后必须运行以下命令。

### 7.1 统一验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

### 7.2 启动 backend

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 7.3 Real-world UIR 与 Mapping

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
```

### 7.4 Gap Analysis

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
```

### 7.5 Knowledge Loop

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
```

### 7.6 Retrieval / Content Organization

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
```

### 7.7 Downstream Contract

如项目已有 downstream verifier：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

---

## 8. 最终产物清单

完成后至少应有以下新增或更新产物。

### 8.1 数据集

```text
examples/real_world/sources/source_manifest.json
examples/real_world/uir/general/
examples/real_world/uir/meeting/
examples/real_world/uir/policy/
examples/real_world/gold/mapping_gold.jsonl
examples/real_world/gold/real_world_badcases.jsonl
examples/real_world/gold/retrieval_queries.jsonl
examples/real_world/review_fixtures/
```

### 8.2 代码

```text
backend/app/services/candidate_service.py
backend/app/services/mapping_service.py
backend/app/services/knowledge_service.py
backend/app/services/effective_template_service.py
backend/app/services/review_service.py
examples/production_like/mapping_templates/*.json
```

### 8.3 测试

```text
backend/tests/test_candidate_service_non_procurement.py
backend/tests/test_non_procurement_templates.py
backend/tests/test_mapping_service.py
backend/tests/test_review_knowledge_loop.py
backend/tests/test_effective_template_service.py
backend/tests/test_real_world_dataset_validation.py
```

### 8.4 报告

```text
reports/real_world_eval_report.json
reports/real_world_eval_report.md
reports/real_world_mapping_eval_report.json
reports/real_world_mapping_eval_report.md
reports/non_procurement_mapping_eval_report.json
reports/non_procurement_mapping_eval_report.md
reports/non_procurement_gap_analysis.json
reports/non_procurement_gap_analysis.md
reports/non_procurement_acceptance_report.md
reports/real_world_knowledge_loop_report.json
reports/real_world_knowledge_loop_report.md
reports/knowledge_loop_eval_report.json
reports/knowledge_loop_eval_report.md
```

### 8.5 文档

```text
README.md
docs/real_world_uir_dataset.md
docs/non_procurement_mapping_improvement_plan.md
docs/real_world_knowledge_loop.md
docs/交接/badcase_analysis.md
docs/交接/requirement_mapping.md
docs/交接/final_handoff_status.md
docs/交接/final_demo_script.md
```

---

## 9. 风险控制

### 9.1 防止过拟合

不要只为某一个样本硬编码。新增规则要至少满足：

```text
1. 有 source evidence
2. 有 doc_type 限定
3. 有 badcase 测试
4. 不破坏旧样本
5. 不让 review-required 异常下降但 badcase 上升
```

### 9.2 防止 Review 被错误消灭

Review-required 不是坏事。以下情况应保留 Review：

```text
1. 语义歧义
2. source label 不明确
3. 多个 target field 可匹配
4. 日期类型不明确
5. 单位类型不明确
6. badcase filter 命中
```

### 9.3 防止 Knowledge 污染

必须保证：

```text
1. rejected candidate 永不激活
2. badcase candidate 永不激活
3. draft pack 不影响 mapping
4. active pack 只影响 future task
5. old snapshot 不变
6. active pack activation 有报告和 metrics
```

### 9.4 防止文档误报

文档中必须区分：

```text
package verification
field semantic validation
review-required
strict validation
retrieval evidence
full RAG
offline UIR builder
runtime ingestion service
```

---

## 10. 建议提交顺序

如果 Codex 会分 commit，建议：

```text
commit 1: baseline report and current metrics
commit 2: real-world source manifest and UIR dataset expansion
commit 3: gold labels / badcases / retrieval queries / review fixtures
commit 4: candidate extraction improvements
commit 5: mapping template and badcase protection improvements
commit 6: review/knowledge loop enhancements
commit 7: evaluator/report updates
commit 8: docs and final handoff updates
```

每个 commit 后至少运行相关局部测试。最终再运行完整验证。

---

## 11. 给 Codex 的执行提示词

可以直接把下面这段发给 Codex：

```text
请在当前 SchemaPack Agent 项目中执行一次深化改造，目标是在不改变“UIR input -> schema-driven package output”生产边界的前提下，推进三个方向：

1. 补强非采购文档质量：
   - 重点提升 general_doc、meeting_doc、policy_doc 的 candidate extraction 与 mapping recall。
   - 优先修复 application_conditions、service_object、required_materials、issuer、publish_date、effective_date、meeting_date、topics、decisions、attendees 等字段。
   - 降低 review-required 和 required missing，但必须保持 badcase violations = 0。
   - 不允许靠过度 fuzzy auto-accept 牺牲安全性。
   - 每个新增 alias / regex / extraction rule 都要有测试和 badcase protection。

2. 强化 Human Review 与 Knowledge Pack 闭环：
   - 构造 approved / rejected / badcase review fixtures。
   - 证明 approve 的 candidate 可以进入 draft pack，active pack 只影响 future tasks。
   - 证明 rejected candidate 和 badcase candidate 不会激活。
   - 证明 draft pack 不影响 mapping，old task snapshot 在 active pack 后仍保持 unchanged。
   - 输出 before/after metrics 与 knowledge-loop reports。

3. 增强真实 UIR 数据集：
   - 当前数据集已有 30 个 UIR documents，本轮扩展到 45 左右；若时间允许扩展到 50–60。
   - 重点增加 general_doc、meeting_doc、policy_doc。
   - 新增样本必须来自公开官方 HTML 或 text-layer PDF，不需要登录、付费、CAPTCHA 或反爬绕过。
   - 不要加入 scanned PDF、OCR-only document、新闻转载、社交媒体、私密记录或大量个人信息材料。
   - 每个新增样本不仅要有 UIR，还要补 source_manifest、mapping_gold、badcases、retrieval_queries 和 review_fixtures。

执行顺序：
Phase 0 先运行 baseline，不改代码；
Phase 1 扩充数据集和 labels；
Phase 2 修复非采购 candidate extraction 与 mapping templates；
Phase 3 强化 review/knowledge loop；
Phase 4 更新 reports 和 docs。

最终必须运行：
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py

最终报告必须明确：
- dataset size
- import / execution / package verification
- real-world mapping recall
- non-procurement average recall
- review-required count
- required missing count
- badcase violations
- active pack effect
- draft pack no effect
- old snapshot unchanged
- remaining gaps

注意：
不要实现或宣称 OCR、完整 RAG、model training、自动激活 LLM 规则、企业级多租户/SSO。
Package verification 不等于字段语义完全正确，文档中必须诚实区分。
```

---

## 12. Definition of Done

本轮完成的标准不是“代码写完”，而是以下条件全部满足：

```text
1. 项目仍能通过 unified verification。
2. 真实 UIR 数据集扩展到至少 45 个，且新增样本全部可追溯。
3. 每个新增样本有 source manifest、UIR、gold labels、badcases、retrieval query 或 review fixture。
4. 非采购 average recall 明显提升。
5. review-required 和 required missing 明显下降。
6. badcase violations 保持 0。
7. Knowledge Pack 激活前后有可复现报告。
8. rejected / badcase candidate 不会污染 active knowledge。
9. old task snapshots 保持 immutable。
10. 文档更新完整，且没有夸大 runtime boundary。
```

## 
