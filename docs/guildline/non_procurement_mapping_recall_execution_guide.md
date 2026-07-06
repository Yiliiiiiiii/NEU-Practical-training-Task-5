# SchemaPack Agent 非采购类 Mapping Recall 提升执行文档

> **历史执行文档**：本文保留优化前基线与目标。最新非采购结果为 35/35 packages、average recall `0.5677551020408163`；当前状态见 [`../project_status.md`](../交接/project_status.md)。

> 交给 Codex 执行。任务重点：继续攻 `non-procurement mapping recall`，优先处理当前扩展数据集中 `review-required 145` 里出现频率最高的字段别名、缺失候选、低置信映射和 Schema 不适配问题。  
> 当前基线：扩展后非采购类 `strict pass = 4/20`，`required missing = 18`，`review-required = 145`，`average recall = 0.349`。  
> 核心要求：不能靠删除必填字段、关闭 badcase、直接改报告、或把低置信映射强行自动通过来“刷指标”。

---

## 1. 本任务的目标、边界与验收口径

### 1.1 目标

本任务的目标是提升 `general_doc`、`meeting_doc`、`policy_doc` 三类非采购文档的字段映射召回率、严格验证通过率和人审前自动映射能力。

必须形成如下闭环：

```text
评测基线 -> 缺口分析 -> 高频问题归类 -> 候选提取增强 -> 模板别名/正则增强 -> Schema/Transform 调整 -> badcase 回归 -> 专项评测 -> 文档更新
```

### 1.2 不变边界

项目生产边界仍然是：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

不要在本任务中实现：

- 原始 PDF / Word / Excel 生产级解析；
- OCR；
- 完整 RAG / vector database runtime；
- 模型训练；
- LLM 自动激活映射规则；
- 大规模重构主链路。

### 1.3 禁止事项

严禁：

1. 删除大量 required 字段来制造 strict pass。
2. 把所有 fuzzy / low-confidence 结果直接 auto-accept。
3. 关闭 badcase filter。
4. 把 review-required 计作 strict pass。
5. 人工直接修改评测结果 JSON。
6. 移除失败样本。
7. 用没有 source evidence 的字段映射。
8. 让新模板或知识包影响旧任务 snapshot。

### 1.4 第一阶段验收目标

当前基线较低，不要求一步达到 0.75 recall。第一阶段目标为：

```text
non_procurement_average_recall >= 0.50
review_required_count <= 115
required_missing_count <= 14
badcase_violation_count == 0
all_package_verify_pass == true
backend tests pass
frontend build pass
verify_all pass
```

如果未达到，必须在报告中如实说明原因，不能写成“已完全解决”。

### 1.5 第二阶段目标

```text
non_procurement_average_recall >= 0.60
review_required_count <= 95
required_missing_count <= 10
strict_pass_count >= 8/20
badcase_violation_count == 0
```

### 1.6 后续伸展目标

```text
non_procurement_average_recall >= 0.75
strict_pass_count >= 12/20
review_required_count <= 70
required_missing_count <= 6
badcase_violation_count == 0
```

---

## 2. 执行阶段总览

按以下阶段执行，不要跳过基线与分析阶段：

```text
Phase 0  基线确认与冻结
Phase 1  新增非采购类 gap analysis 脚本
Phase 2  诊断 review-required 145 的高频模式
Phase 3  增强 CandidateService 候选提取
Phase 4  增强 general_doc / meeting_doc / policy_doc 模板
Phase 5  合理调整 Schema required / optional 规则
Phase 6  增强 Transform 类型归一
Phase 7  扩充 badcase 与回归测试
Phase 8  新增非采购类专项评测脚本
Phase 9  更新报告与文档
Phase 10 跑完整验收命令
```

---

## 3. Phase 0：基线确认与冻结

### 3.1 检查分支和工作区

在仓库根目录执行：

```powershell
git branch --show-current
git status --short
```

要求：

```text
当前分支明确；
没有不相关未提交改动；
如有改动，先记录来源，不要覆盖。
```

### 3.2 跑统一验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

如果失败，先修基础验证，不进入 mapping recall 优化。

### 3.3 启动后端

开一个终端：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 3.4 跑当前真实数据评测

另开终端：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
```

如果已有专项脚本，也执行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
```

### 3.5 保存基线

新增或更新：

```text
reports/non_procurement_baseline_report.json
reports/non_procurement_baseline_report.md
```

基线至少记录：

```json
{
  "dataset_size": 30,
  "non_procurement_dataset_size": 20,
  "strict_pass_count": 4,
  "required_missing_count": 18,
  "review_required_count": 145,
  "average_recall": 0.349,
  "badcase_violation_count": 0
}
```

如果实际脚本结果与上述数字不同，以实际脚本为准，并在报告中说明差异。

---

## 4. Phase 1：新增非采购类 Gap Analysis 脚本

### 4.1 新增文件

```text
scripts/analyze_non_procurement_gaps.py
```

用途：扫描真实评测包中的 mapping、validation、gold labels 和 badcases，自动统计非采购类文档的字段缺口。

### 4.2 命令形式

脚本应支持：

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\non_procurement_gap_analysis.json `
  --markdown reports\non_procurement_gap_analysis.md
```

参数：

```text
--packages-root  真实评测生成的 package 根目录
--gold           mapping gold label jsonl
--badcases       badcase jsonl
--doc-types      默认 general_doc,meeting_doc,policy_doc
--out            JSON 输出
--markdown       Markdown 输出
--top-n          高频问题数量，默认 30
```

### 4.3 文件发现逻辑

不要写死 package 目录层级。脚本应递归查找包含以下文件的目录：

```text
metadata.json
mapping_report.json
validation_report.json
content.json
canonical.json
```

每个 package 优先读取：

```text
metadata.json
mapping_report.json
validation_report.json
content.json
canonical.json
content_organization_report.json
chunks.jsonl
```

### 4.4 过滤范围

只统计：

```python
NON_PROCUREMENT_DOC_TYPES = {"general_doc", "meeting_doc", "policy_doc"}
```

排除：

```text
procurement_doc
contract_doc
```

### 4.5 gap 分类

脚本必须将问题分为 6 类。

#### 4.5.1 candidate_not_extracted

定义：gold 期望字段在原文中存在，但候选提取阶段没有提取出对应 source candidate。

常见原因：

```text
标题只在 heading 中；
发文机关在正文首段；
会议日期在自然语言中；
办理材料在列表中；
政策措施在小标题下的段落中。
```

推荐修复：增强 CandidateService。

#### 4.5.2 alias_missing

定义：候选已存在，但 source name 与 target field 未能通过 exact / alias / regex / type / fuzzy 映射。

常见原因：

```text
“印发机关”未映射 issuer；
“参会同志”未映射 attendees；
“办理依据”未映射 legal_basis；
“申报主体”未映射 target_audience。
```

推荐修复：增加 template aliases。

#### 4.5.3 regex_missing

定义：字段不是明确 key/value，但可以由稳定文本模式抽取。

常见原因：

```text
自 2026 年 7 月 1 日起施行；
联系电话：xxxx；
文号：沪府办发〔2026〕12号；
会议于 2026 年 6 月 30 日召开。
```

推荐修复：增加 regex rule 或 paragraph regex candidate。

#### 4.5.4 schema_too_strict

定义：目标 Schema 对某类文档要求过强，真实文档中经常不存在该字段，且没有稳定证据可抽取。

常见原因：

```text
general_doc 要求所有普通文档都有 contact_phone；
policy_doc 要求 effective_date，但很多政策只给 publish_date；
meeting_doc 要求 location，但公开纪要未披露地点。
```

推荐修复：将字段改为 optional、warning，或引入 required_any。不能滥用。

#### 4.5.5 transform_type_error

定义：候选和映射都存在，但 transform 或 validation 因类型失败。

常见原因：

```text
中文日期未转 ISO；
attendees 是顿号分隔字符串，但 schema 要 array；
联系电话带空格或括号；
政策措施是列表文本，但 schema 要 array。
```

推荐修复：增强 TransformService。

#### 4.5.6 badcase_sensitive

定义：看似可自动映射，但存在高风险混淆。

常见原因：

```text
发布日期 ≠ 生效日期；
主持人 ≠ 参会人员；
联系人 ≠ 参会人员；
承办单位 ≠ 发布机构；
控制价 ≠ 中标金额。
```

推荐修复：保留 review-required，增加 forbidden mapping 和 badcase。

### 4.6 JSON 输出结构

`reports/non_procurement_gap_analysis.json` 应包含：

```json
{
  "summary": {
    "documents_total": 20,
    "overall": {
      "strict_pass_count": 0,
      "review_required_count": 0,
      "required_missing_count": 0,
      "average_recall": 0.0,
      "badcase_violation_count": 0
    },
    "by_doc_type": {
      "general_doc": {},
      "meeting_doc": {},
      "policy_doc": {}
    }
  },
  "top_missing_required_fields": [],
  "top_review_required_fields": [],
  "candidate_extraction_gaps": [],
  "alias_gaps": [],
  "regex_gaps": [],
  "schema_gaps": [],
  "transform_gaps": [],
  "badcase_sensitive_items": [],
  "recommended_plan": []
}
```

每个 gap item 至少包含：

```json
{
  "doc_type": "policy_doc",
  "doc_id": "...",
  "target_field": "publish_date",
  "gap_type": "alias_missing",
  "count": 3,
  "candidate_source_names": [],
  "candidate_value_samples": [],
  "source_block_ids": [],
  "review_required_reason": "low_confidence",
  "recommended_action": "add_alias"
}
```

### 4.7 Markdown 输出结构

`reports/non_procurement_gap_analysis.md`：

```markdown
# Non-procurement Mapping Gap Analysis

## Summary
## By Document Type
## Top Missing Required Fields
## Top Review-required Fields
## Candidate Extraction Gaps
## Alias Gaps
## Regex Rule Gaps
## Schema Required-field Gaps
## Transform / Type Normalization Gaps
## Badcase-sensitive Items
## Recommended Fix Plan
## Do-not-auto-accept List
```

---

## 5. Phase 2：诊断 review-required 145 的高频模式

### 5.1 生成并阅读报告

执行：

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\non_procurement_gap_analysis.json `
  --markdown reports\non_procurement_gap_analysis.md

Get-Content reports\non_procurement_gap_analysis.md -Encoding UTF8
```

### 5.2 新增修复计划文档

新增：

```text
docs/non_procurement_mapping_improvement_plan.md
```

结构：

```markdown
# Non-procurement Mapping Improvement Plan

## Baseline

## High-frequency Fix Items

| ID | doc_type | target_field | count | gap_type | action | files_to_change | risk | expected_gain |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |

## Candidate Extraction Fixes
## Template Alias Fixes
## Regex Rule Fixes
## Schema Adjustments
## Transform Fixes
## Badcase Additions
## Verification Commands
```

### 5.3 修复优先级

优先处理：

```text
高频 + 低风险 + 有 source evidence + 可规则化
```

顺序：

1. 高频 alias_missing。
2. 高频 regex_missing。
3. 明显 candidate_not_extracted。
4. transform_type_error。
5. schema_too_strict。
6. badcase_sensitive 只加保护，不自动通过。

---

## 6. Phase 3：增强 CandidateService 候选提取

### 6.1 定位文件

优先查找：

```text
backend/app/services/candidate_service.py
```

搜索命令：

```powershell
Get-ChildItem backend\app -Recurse -Filter "*candidate*.py"
Select-String -Path backend\app\**\*.py -Pattern "class CandidateService"
```

### 6.2 必须支持的候选来源

确认或新增：

```text
metadata fields
table rows
block attributes.field_name
heading blocks
title_path
paragraph key/value
list item under heading
regex extracted values
```

### 6.3 候选 evidence 要求

每个候选必须保留：

```text
source_path
source_blocks
value_sample
candidate_origin 或 evidence.origin
extraction_confidence 或 confidence_hint
```

没有 source block 的候选不得进入自动映射。

### 6.4 新增 heading 候选

当 block 是 heading/title 或 attributes 表明 heading level：

```json
{
  "source_name": "title",
  "value_sample": "原 heading 文本",
  "source_path": "blocks[n].text",
  "source_blocks": ["block_id"],
  "candidate_origin": "heading"
}
```

首个高等级 heading 可额外生成：

```text
document_title
policy_title
meeting_title
guide_title
```

### 6.5 新增中文 key/value 候选

支持：

```text
字段名：字段值
字段名: 字段值
（一）字段名：字段值
1. 字段名：字段值
```

规则：

```text
2 <= key length <= 20
1 <= value length <= 1000
```

过滤噪声 key：

```text
附件
目录
正文
说明
备注
注
```

### 6.6 新增 list item 候选

如果列表前一个 heading 是：

```text
申请材料
办理材料
办理流程
申报流程
会议决定
议定事项
政策措施
工作要求
```

则将列表合并为候选：

```json
{
  "source_name": "申请材料",
  "value_sample": "列表内容拼接",
  "candidate_origin": "list_item"
}
```

### 6.7 新增 paragraph regex 候选

保守增加以下模式。

#### 日期

```regex
\d{4}年\d{1,2}月\d{1,2}日
```

#### 文号

```regex
[\u4e00-\u9fa5]{1,10}[〔\[]\d{4}[〕\]]\d{1,5}号
```

#### 联系方式

```regex
(?:联系电话|联系方式|咨询电话)[:：]?\s*([0-9\-]{7,20})
```

#### 发文机关

```regex
(?:发布机构|发文机关|印发机关|制定机关)[:：]?\s*([^\n。；;]{2,50})
```

#### 会议时间

```regex
(?:会议时间|召开时间|会议于)[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日[^，。；;]*)
```

### 6.8 测试

新增或补充：

```text
backend/tests/test_candidate_service_non_procurement.py
```

至少测试：

1. heading 提取 title candidate。
2. 中文冒号 key/value 被提取。
3. list under heading 被提取。
4. policy 文号 regex 被提取。
5. meeting date regex 被提取。
6. 空 block 不崩溃。
7. source_blocks 不为空。
8. 噪声 key 不被提取。
9. badcase 文本不会被自动当作高置信目标字段，只作为候选。

执行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_service_non_procurement.py -q
cd ..
```

---

## 7. Phase 4：增强非采购类 Mapping Template

### 7.1 定位模板文件

搜索：

```powershell
Get-ChildItem -Recurse -Path . -Include "*general*template*.json","*meeting*template*.json","*policy*template*.json"
Get-ChildItem -Recurse -Path . -Include "*general_doc*.json","*meeting_doc*.json","*policy_doc*.json"
```

根据项目实际路径修改。

### 7.2 修改原则

只添加：

```text
aliases
regex_rules
transform/default hints
```

不要写硬编码 doc_id。

所有 target field 必须存在于对应 schema。

### 7.3 general_doc alias 池

按真实 schema 字段名适配，不存在的 target 不要写。

#### title / document_title

```text
标题
事项名称
服务事项
办事事项
项目名称
通知标题
指南名称
业务名称
```

#### issuer / source_org / department

```text
发布机构
主管部门
办理部门
受理部门
责任单位
牵头单位
实施单位
服务机构
```

#### publish_date

```text
发布日期
发布时间
公开日期
印发日期
成文日期
```

`更新日期` 有风险，不要默认映射为 publish_date，除非 schema 有 updated_date。

#### service_object / target_audience

```text
服务对象
适用对象
面向对象
申请对象
办理对象
支持对象
申报对象
```

#### conditions / requirements

```text
申请条件
办理条件
申报条件
受理条件
资格条件
基本条件
```

#### materials

```text
申请材料
办理材料
申报材料
所需材料
提交材料
材料清单
```

#### process_steps

```text
办理流程
办理程序
申报流程
申请流程
办事流程
操作流程
流程说明
```

#### legal_basis

```text
办理依据
政策依据
设定依据
法律依据
文件依据
依据文件
```

#### contact

```text
联系电话
联系方式
咨询电话
咨询方式
联系地址
```

注意：`联系人` 不应映射到 `contact_phone`，除非 schema 有 `contact_person`。

### 7.4 meeting_doc alias 池

#### title / meeting_title

```text
会议名称
会议标题
会议纪要
会议主题
专题会议
常务会议
```

#### meeting_date

```text
会议时间
召开时间
会议日期
时间
会议于
```

#### location

```text
会议地点
召开地点
地点
会场
```

#### attendees

```text
参会人员
参会同志
出席人员
出席同志
参加人员
与会人员
列席人员
参会单位
```

注意：`主持人` 不应直接映射到 attendees。

#### host / chairperson

```text
主持人
主持
会议主持
召集人
```

#### agenda

```text
会议议题
会议议程
审议事项
研究事项
讨论事项
```

#### decisions / resolutions / action_items

```text
会议决定
议定事项
会议要求
工作部署
决定事项
形成意见
下一步工作
任务分工
```

### 7.5 policy_doc alias 池

#### title / policy_title

```text
政策名称
文件名称
通知名称
标题
政策标题
文件标题
```

#### issuer / issuing_authority

```text
发布机构
发文机关
印发机关
制定机关
主管部门
牵头部门
责任部门
```

#### document_number

```text
文号
发文字号
文件编号
政策编号
通知编号
```

#### publish_date

```text
发布日期
发布时间
印发日期
成文日期
公开日期
```

#### effective_date

```text
施行日期
实施日期
生效日期
执行日期
自...起施行
自...起实施
```

注意：不要把 `发布日期` 自动映射为 `effective_date`，除非文本明确“自发布之日起施行”。

#### target_audience / applicable_scope

```text
适用对象
适用范围
支持对象
扶持对象
服务对象
申报主体
面向对象
```

#### policy_measures / key_measures

```text
政策措施
支持措施
扶持措施
主要措施
重点任务
工作措施
具体措施
```

#### requirements / obligations

```text
工作要求
申报要求
执行要求
管理要求
有关要求
具体要求
```

#### application_materials

```text
申报材料
申请材料
提交材料
材料要求
材料清单
```

#### application_process

```text
申报流程
申请流程
办理流程
操作流程
实施流程
```

#### contact

```text
联系方式
联系电话
咨询电话
联系单位
```

#### legal_basis

```text
政策依据
制定依据
法律依据
文件依据
依据
```

### 7.6 regex rules 建议

按现有 MappingTemplate schema 格式实现。

#### document_number

```json
{
  "target_field": "document_number",
  "pattern": "(?P<value>[\\u4e00-\\u9fa5]{1,10}[〔\\[]\\d{4}[〕\\]]\\d{1,5}号)",
  "confidence": 0.90
}
```

#### publish_date

```json
{
  "target_field": "publish_date",
  "pattern": "(?:发布日期|发布时间|印发日期|成文日期)[:：\\s]*(?P<value>\\d{4}年\\d{1,2}月\\d{1,2}日)",
  "confidence": 0.88
}
```

#### effective_date

```json
{
  "target_field": "effective_date",
  "pattern": "(?:自|从)(?P<value>\\d{4}年\\d{1,2}月\\d{1,2}日|发布之日|印发之日)起(?:施行|实施|执行)",
  "confidence": 0.86
}
```

`发布之日` 需要 transform 结合 publish_date，否则应 review-required。

#### contact_phone

```json
{
  "target_field": "contact_phone",
  "pattern": "(?:联系电话|联系方式|咨询电话)[:：\\s]*(?P<value>[0-9\\-]{7,20})",
  "confidence": 0.92
}
```

#### meeting_date

```json
{
  "target_field": "meeting_date",
  "pattern": "(?:会议于|召开时间|会议时间)[:：\\s]*(?P<value>\\d{4}年\\d{1,2}月\\d{1,2}日)",
  "confidence": 0.88
}
```

### 7.7 模板测试

新增：

```text
backend/tests/test_non_procurement_templates.py
```

测试：

1. general_doc 高频 alias 能加载。
2. meeting_doc 高频 alias 能加载。
3. policy_doc 高频 alias 能加载。
4. 每个 alias target field 在 schema 中存在。
5. regex target field 在 schema 中存在。
6. forbidden/badcase pair 不因 alias 增强被 auto-accept。
7. template version activation 不破坏旧 snapshot。

---

## 8. Phase 5：合理调整 Schema required / optional 规则

### 8.1 原则

Schema 调整是最后手段。只有字段在真实文档中经常不存在，且无法稳定抽取时，才考虑 optional 或 required_any。

### 8.2 不应轻易移除的核心字段

#### general_doc

```text
title
doc_type 或 document_type
source / issuer / organization 中至少一个
content / main_text / sections 中至少一个
```

#### meeting_doc

```text
title 或 meeting_title
meeting_date 或 publish_date 中至少一个
decisions / agenda / summary 中至少一个
```

#### policy_doc

```text
title 或 policy_title
issuer 或 issuing_authority 中至少一个
publish_date 或 document_number 中至少一个
policy_measures / requirements / content 中至少一个
```

### 8.3 可考虑 optional 的字段

```text
location
contact_phone
effective_date
application_deadline
fees
attachments
specific_address
host
attendees
```

### 8.4 建议 required_any

如果系统支持，添加：

```text
policy_doc:
  required_any:
    - [publish_date, document_number]
    - [issuer, issuing_authority]
    - [policy_measures, requirements, content]

meeting_doc:
  required_any:
    - [meeting_date, publish_date]
    - [decisions, agenda, summary]

general_doc:
  required_any:
    - [issuer, source_org, department]
    - [materials, process_steps, content]
```

如果系统不支持，不要大改底层；可先在 ValidationService 中轻量支持或使用 schema metadata hints。

### 8.5 Schema 调整报告

新增：

```text
reports/non_procurement_schema_adjustments.md
```

格式：

```markdown
| doc_type | field | old_rule | new_rule | reason | affected_docs | risk | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

### 8.6 测试

新增：

```text
backend/tests/test_non_procurement_schema_validation.py
```

测试：

1. 核心字段缺失仍失败。
2. 可选字段缺失不失败。
3. required_any 满足时通过。
4. required_any 全缺失时失败。
5. procurement_doc 不被本次调整影响。

---

## 9. Phase 6：增强 Transform 类型归一

### 9.1 中文日期归一

支持：

```text
2026年7月1日 -> 2026-07-01
2026 年 7 月 1 日 -> 2026-07-01
2026.7.1 -> 2026-07-01
2026/7/1 -> 2026-07-01
```

缺少年份的日期不要猜，进入 review-required 或 warning。

### 9.2 数组字段归一

如果 schema 要 array，而源值是中文字符串，支持切分：

```text
、
；
;
\n
```

适用字段：

```text
attendees
materials
process_steps
policy_measures
requirements
```

### 9.3 联系方式归一

```text
021 - 12345678 -> 021-12345678
```

不要把联系人姓名放入 phone 字段。

### 9.4 文号归一

文号保持原始格式，不要转成数字或拆坏。

### 9.5 测试

新增：

```text
backend/tests/test_non_procurement_transform.py
```

测试：

1. 中文日期转 ISO。
2. 中文顿号字符串转 array。
3. 联系电话清理。
4. 文号保留。
5. 无法确定的日期产生 warning/review，而不是乱填。

---

## 10. Phase 7：扩充 badcase 与安全保护

### 10.1 修改文件

优先定位：

```text
examples/real_world/gold/real_world_badcases.jsonl
```

或项目当前实际 badcase 文件。

### 10.2 必须新增的 badcase 类型

#### 日期混淆

```text
发布日期 ≠ 生效日期
印发日期 ≠ 截止日期
更新时间 ≠ 发布日期，除非字段就是 updated_date
```

#### 人员混淆

```text
主持人 ≠ 参会人员
联系人 ≠ 参会人员
责任人 ≠ 联系电话
```

#### 机构混淆

```text
承办单位 ≠ 发布机构，除非目标字段是 organizer
联系电话附近的单位 ≠ issuer
```

#### 采购金额残留混淆

```text
预算金额 ≠ 中标金额
控制价 ≠ 中标金额
```

即便本任务是非采购类，也不能破坏原采购类保护。

### 10.3 测试

新增：

```text
backend/tests/test_non_procurement_badcases.py
```

测试：

1. badcase source-target pair 被 blocked。
2. badcase 不因 alias 增强变成 auto-accepted。
3. badcase 可以进入 review-required。
4. badcase violation count 仍为 0。

---

## 11. Phase 8：新增非采购类专项评测脚本

### 11.1 新增文件

```text
scripts/eval_non_procurement_mapping.py
```

### 11.2 命令

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md
```

### 11.3 流程

脚本应：

1. 读取 `examples/real_world/uir/` 下所有 UIR。
2. 过滤 `general_doc`、`meeting_doc`、`policy_doc`。
3. 调用 API import。
4. 创建 task。
5. 执行 task。
6. 读取 mapping report。
7. 读取 validation report。
8. 读取 package metadata。
9. 根据 gold labels 计算 recall。
10. 根据 validation report 统计 strict pass。
11. 根据 mapping report 统计 review-required。
12. 根据 badcases 统计 violation。
13. 输出 JSON/Markdown 报告。

### 11.4 JSON 报告结构

```json
{
  "summary": {
    "dataset_size": 20,
    "strict_pass_count": 0,
    "strict_pass_rate": 0.0,
    "average_recall": 0.0,
    "review_required_count": 0,
    "required_missing_count": 0,
    "badcase_violation_count": 0,
    "package_verify_pass_count": 0
  },
  "by_doc_type": {
    "general_doc": {},
    "meeting_doc": {},
    "policy_doc": {}
  },
  "by_field": [],
  "typical_improvements": [],
  "remaining_gaps": [],
  "failed_cases": []
}
```

### 11.5 Markdown 报告结构

```markdown
# Non-procurement Mapping Evaluation Report

## Summary
## Metrics By Document Type
## Field-level Recall
## Strict Validation
## Review-required Analysis
## Required Missing Analysis
## Badcase Safety
## Typical Improvements
## Remaining Gaps
## Commands
```

### 11.6 baseline 对比

支持参数：

```powershell
--baseline reports\non_procurement_baseline_report.json
```

输出 delta：

```json
{
  "delta": {
    "average_recall": "+0.151",
    "review_required_count": "-35",
    "required_missing_count": "-4",
    "strict_pass_count": "+4"
  }
}
```

---

## 12. Phase 9：文档更新

### 12.1 必须更新

```text
README.md
docs/交接/final_handoff_status.md
docs/交接/requirement_mapping.md
docs/real_world_uir_dataset.md
docs/交接/badcase_analysis.md
docs/developer_guide.md
```

### 12.2 建议新增

```text
docs/non_procurement_mapping_improvement_plan.md
reports/non_procurement_gap_analysis.md
reports/non_procurement_mapping_eval_report.md
reports/non_procurement_schema_adjustments.md
reports/non_procurement_acceptance_report.md
```

### 12.3 表述模板

如果第一阶段达成：

```markdown
本轮非采购类 mapping recall 优化完成第一阶段目标。系统新增非采购类 gap analysis、候选提取增强、模板别名/正则规则、Schema 调整记录和 badcase 保护。评测显示 average recall 从 0.349 提升到 X，review-required 从 145 降至 Y，required missing 从 18 降至 Z，strict pass 从 4/20 提升到 N/20，badcase violation 仍为 0。
```

如果未达成：

```markdown
本轮已完成 gap analysis 和部分规则增强，但第一阶段目标未完全达成。当前 average recall 为 X，review-required 为 Y，required missing 为 Z。主要瓶颈为 A/B/C，后续需继续增强 CandidateService 与 domain template。
```

禁止写：

```text
已完全解决非采购类映射问题
字段映射准确率已达 85%
所有非采购文档均严格通过
```

除非报告真实支持。

---

## 13. Phase 10：完整验证命令

### 13.1 后端测试与 lint

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
cd ..
```

### 13.2 前端构建

```powershell
cd frontend
npm ci
npm run build
cd ..
```

### 13.3 统一验证

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

### 13.4 API-backed evaluators

确保后端运行后执行：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
```

### 13.5 Gap analysis

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\non_procurement_gap_analysis.json `
  --markdown reports\non_procurement_gap_analysis.md
```

### 13.6 其他回归

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_strategy_comparison.py
backend\.venv\Scripts\python.exe scripts\eval_summary_faithfulness.py
backend\.venv\Scripts\python.exe scripts\eval_content_tag_quality.py
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

---

## 14. Codex 执行提示词

把下面内容直接发给 Codex：

```text
你现在要继续推进 SchemaPack Agent 的 non-procurement mapping recall 优化任务。请严格按 docs/non_procurement_mapping_recall_execution_guide.md 执行。

当前基线：扩展数据集后 non-procurement strict pass 4/20，required missing 18，review-required 145，average recall 0.349。目标不是刷指标，而是建立可复现的 gap analysis -> 修复 -> 回归评测闭环。

执行要求：
1. 先跑 verify_all.py --check-openapi 和当前真实数据评测，冻结 baseline。
2. 新增 scripts/analyze_non_procurement_gaps.py，扫描 reports/real_world_packages、mapping_report、validation_report、mapping_gold、badcases，输出 reports/non_procurement_gap_analysis.json/md。
3. 根据 gap analysis 分类问题：candidate_not_extracted、alias_missing、regex_missing、schema_too_strict、transform_type_error、badcase_sensitive。
4. 只优先处理高频、低风险、有 source evidence 的问题。
5. 增强 CandidateService：heading、title_path、中文 key/value、list item、段落 regex 候选。
6. 增强 general_doc、meeting_doc、policy_doc templates：aliases 和 regex rules。所有 target field 必须存在于 schema。
7. 谨慎调整 schema required 字段，不得通过删除大量 required 来刷 strict pass。所有调整写入 reports/non_procurement_schema_adjustments.md。
8. 增强 transform：中文日期、数组字段、联系方式、文号归一。
9. 增加 badcase 保护，尤其日期混淆、人员混淆、机构混淆、采购金额残留混淆。
10. 新增 scripts/eval_non_procurement_mapping.py，输出 reports/non_procurement_mapping_eval_report.json/md。
11. 新增/补充 pytest：candidate、template、schema validation、transform、badcase。
12. 最后运行：backend pytest、ruff、frontend build、verify_all.py --check-openapi、eval_real_world_uir.py、eval_real_world_mapping.py、eval_non_procurement_mapping.py、analyze_non_procurement_gaps.py。
13. 更新 README、final_handoff_status、requirement_mapping、real_world_uir_dataset、badcase_analysis、developer_guide。
14. 如果指标未达成，必须如实写明，不得把部分通过写成完全通过。

第一阶段验收目标：average recall >= 0.50，review-required <= 115，required missing <= 14，badcase violation == 0，package verify all pass，verify_all pass。
请按阶段提交改动，并在每个阶段说明修改文件、运行命令、结果和剩余风险。
```

---

## 15. 最终验收清单

```markdown
# Non-procurement Mapping Recall 验收清单

## 基线
- [ ] 已记录 baseline strict pass
- [ ] 已记录 baseline average recall
- [ ] 已记录 baseline review-required
- [ ] 已记录 baseline required missing

## Gap Analysis
- [ ] 已生成 reports/non_procurement_gap_analysis.json
- [ ] 已生成 reports/non_procurement_gap_analysis.md
- [ ] 高频问题已分类
- [ ] badcase-sensitive items 已列出

## CandidateService
- [ ] 支持 heading candidate
- [ ] 支持 title_path candidate
- [ ] 支持中文 key/value candidate
- [ ] 支持 list item candidate
- [ ] 支持 paragraph regex candidate
- [ ] 每个候选有 source evidence

## Templates
- [ ] general_doc aliases 增强
- [ ] meeting_doc aliases 增强
- [ ] policy_doc aliases 增强
- [ ] regex rules 增强
- [ ] 所有 target fields 均存在
- [ ] 无 badcase auto-accept

## Schema / Transform
- [ ] schema 调整有报告
- [ ] 核心 required 字段未被滥删
- [ ] 中文日期归一
- [ ] array 字段归一
- [ ] phone/contact 归一
- [ ] 文号保留

## Badcase
- [ ] 日期混淆 badcase
- [ ] 人员混淆 badcase
- [ ] 机构混淆 badcase
- [ ] 采购金额残留 badcase
- [ ] badcase violation == 0

## Evaluation
- [ ] eval_non_procurement_mapping.py 可运行
- [ ] non_procurement_mapping_eval_report.json 已生成
- [ ] non_procurement_mapping_eval_report.md 已生成
- [ ] average recall 有提升
- [ ] review-required 有下降
- [ ] required missing 有下降
- [ ] strict pass 有提升

## Verification
- [ ] backend pytest passed
- [ ] ruff clean
- [ ] frontend build passed
- [ ] verify_all.py --check-openapi passed
- [ ] real_world_eval passed
- [ ] package verification passed

## Documentation
- [ ] README updated
- [ ] final_handoff_status updated
- [ ] requirement_mapping updated
- [ ] real_world_uir_dataset updated
- [ ] badcase_analysis updated
- [ ] developer_guide updated
- [ ] acceptance report generated
```
