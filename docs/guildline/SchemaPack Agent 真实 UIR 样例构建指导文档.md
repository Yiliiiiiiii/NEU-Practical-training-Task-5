
# SchemaPack Agent 真实文档采集与真实 UIR 构建实施文档

> **历史执行文档**：本文保留数据集构建过程。当前 manifest 为 45 documents，最新状态见 [`../project_status.md`](../project_status.md)。

## 1. 任务背景

当前 SchemaPack Agent 已经完成课题 5 的核心链路：

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

现有系统已经具备：

* UIR 文档导入
* Schema / Template 版本治理
* 字段候选抽取
* 确定性字段映射
* 可选 LLM fallback
* 人工 review
* knowledge pack 激活
* canonical model 构建
* Markdown / JSON / chunks 渲染
* validation
* manifest
* package ZIP
* package verifier
* downstream smoke test
* training corpus export

但当前 production-like evaluation 数据集主要是合成样例。为了增强项目可信度、泛化能力和答辩说服力，需要补充一批来自真实公开文档的 UIR 输入样例。

本任务目标是新增一套独立的数据集构建工具链：

```text
公开网页 / 可复制 PDF / 可复制 Word
        ↓
文本和表格抽取
        ↓
规则清洗与结构化
        ↓
可选 GPT 辅助分块和字段候选生成
        ↓
真实 UIR JSON
        ↓
现有 SchemaPack Agent 导入与执行
        ↓
真实样例评测报告
```

本任务不得破坏现有主链路，不得把 SchemaPack Agent 改造成通用 PDF/OCR/Word 解析系统。

---

## 2. 总体目标

新增 `examples/real_world/` 数据集目录和相关脚本，从公开真实文档中构建可导入的 UIR JSON 样例。

最终应实现：

1. 从公开来源收集真实文档 URL。
2. 支持 HTML 和可复制文本 PDF 的轻量抽取。
3. 可选支持 docx 文本抽取。
4. 暂不支持扫描版 PDF OCR。
5. 生成项目兼容的真实 UIR JSON。
6. 每个 UIR 保留来源 URL、抓取时间、来源 hash、抽取方法。
7. 每个 UIR 可通过现有 `/api/v1/documents/import` 导入。
8. 每个 UIR 可创建 task 并执行。
9. 生成 mapping、validation、chunks、package、verifier 报告。
10. 生成真实数据集评测报告 `reports/real_world_eval_report.md`。

---

## 3. 关键边界

### 3.1 本任务要做什么

本任务做的是：

```text
真实公开文档 -> 真实 UIR 样例
```

具体包括：

* 网络搜索或人工配置真实公开文档 URL
* 下载 HTML / PDF / DOCX
* 抽取标题、正文、表格、元数据
* 转换成项目 UIR JSON 格式
* 对生成 UIR 做质量校验
* 把 UIR 接入现有任务执行链路
* 生成真实数据集评测报告

### 3.2 本任务不做什么

本任务不做：

* 不实现大规模爬虫
* 不绕过登录、验证码、付费墙、反爬限制
* 不抓取个人隐私数据
* 不抓取社交平台内容
* 不抓取新闻媒体长文作为主要样本
* 不做扫描版 PDF OCR 主线
* 不修改核心转换链路
* 不让 LLM 自动生成最终 gold truth
* 不让 LLM 自动激活知识规则
* 不把 raw PDF/HTML 大文件大量提交到 Git
* 不把完整长篇原文全文塞进 UIR

---

## 4. 可行性判断

### 4.1 让 Codex / GPT 直接解析 PDF 是否可行

可行，但不建议作为唯一方式。

原因：

1. PDF 类型复杂，包括可复制文本 PDF、扫描 PDF、双栏 PDF、表格 PDF、图片 PDF。
2. 直接让 GPT 解析容易出现漏字段、错表格、幻觉补字段。
3. 直接解析不可复现，不方便后续回归测试。
4. 项目当前主边界是 UIR 输入，不应把主系统改造成 PDF 解析系统。

### 4.2 推荐方案

推荐采用：

```text
确定性工具抽取 + 规则清洗 + GPT 辅助结构化 + UIR 校验
```

即：

```text
HTML / PDF
   ↓
requests / BeautifulSoup / PyMuPDF / pdfplumber
   ↓
标题、段落、列表、表格、日期、编号、金额抽取
   ↓
GPT 辅助分块和字段候选生成
   ↓
保存 UIR JSON
   ↓
validate_real_world_uir.py
   ↓
导入现有系统执行验证
```

GPT 可以参与，但必须受限：

* 可以辅助识别文档类型
* 可以辅助切分 blocks
* 可以辅助提取候选字段
* 可以辅助生成 summary / keywords
* 不得凭空补字段
* 不得把不确定内容写成确定字段
* 不得把 LLM 输出直接作为 gold truth
* 所有 LLM 辅助字段必须带 evidence、confidence、review_required 标记

---

## 5. 支持文件类型

### 5.1 第一阶段必须支持

第一阶段支持：

```text
HTML 网页
可复制文本 PDF
```

HTML 网页优先，因为结构相对清楚，抽取稳定。

可复制文本 PDF 次之，可以用 PyMuPDF 或 pdfplumber 抽取文本和表格。

### 5.2 第二阶段可选支持

可选支持：

```text
DOCX
TXT
Markdown
```

DOCX 可使用 `python-docx` 读取标题、段落、表格。

### 5.3 暂不支持

暂不支持：

```text
扫描版 PDF
图片
需要 OCR 的文档
需要登录或验证码的页面
付费文档
```

遇到这类来源时，不应强行解析，应标记为：

```json
{
  "status": "skipped",
  "reason": "unsupported_scanned_pdf_or_login_required"
}
```

---

## 6. 推荐公开数据来源

### 6.1 政策类 policy_doc

推荐来源：

* 国务院政策文件库
* 各部委政策文件栏目
* 地方政府公开政策文件
* 教育部、工信部、生态环境部、发改委等公开政策文件

推荐文档类型：

* 通知
* 意见
* 办法
* 条例
* 实施方案
* 工作要点
* 指南
* 规划

目标数量：

```text
第一阶段：5 个
完整阶段：8 到 10 个
```

### 6.2 采购 / 招标类 procurement_doc

推荐来源：

* 全国公共资源交易平台
* 政府采购网
* 各省公共资源交易中心
* 学校 / 医院 / 政府公开采购公告

推荐文档类型：

* 招标公告
* 中标公告
* 成交公告
* 更正公告
* 采购合同公告

目标数量：

```text
第一阶段：5 个
完整阶段：8 到 10 个
```

### 6.3 合同类 contract_doc

推荐来源：

* 政府采购合同公告
* 上市公司重大合同公告
* 公共资源交易平台合同公告
* SEC / 交易所公开披露文件中的合同摘要

目标数量：

```text
第一阶段：2 到 3 个
完整阶段：5 个
```

### 6.4 会议类 meeting_doc

推荐来源：

* 政府常务会议公开稿
* 委员会会议纪要
* 学校公开会议纪要
* 上市公司董事会决议公告

目标数量：

```text
第一阶段：2 到 3 个
完整阶段：5 个
```

### 6.5 普通业务文档 general_doc

推荐来源：

* 办事指南
* 操作说明
* 服务指南
* 项目申报指南
* 通知公告

目标数量：

```text
第一阶段：3 个
完整阶段：5 个
```

---

## 7. 数据集规模要求

### 7.1 最小可交付规模

最低完成：

```text
policy_doc: 5
procurement_doc: 5
meeting_doc: 3
general_doc: 3
合计: 16
```

### 7.2 推荐完整规模

推荐完成：

```text
policy_doc: 8
procurement_doc: 8
contract_doc: 5
meeting_doc: 5
general_doc: 5
合计: 31
```

### 7.3 样例分布要求

真实样例中应刻意包含：

* 纯正文文档
* 多标题层级文档
* 多表格文档
* 字段缺失文档
* 日期字段混杂文档
* 金额字段混杂文档
* 主体字段混杂文档
* 标题格式不规范文档

---

## 8. 新增目录结构

请新增以下目录：

```text
examples/
  real_world/
    README.md
    sources/
      source_manifest.json
    raw_cache/
      .gitkeep
    uir/
      policy/
      procurement/
      contract/
      meeting/
      general/
      _rejected/
    expectations_draft/
      policy/
      procurement/
      contract/
      meeting/
      general/
    reports/
      extraction_report.json
      extraction_report.md
      validation_report.json
      validation_report.md

scripts/
  collect_real_world_sources.py
  extract_html_to_uir.py
  extract_pdf_to_uir.py
  extract_docx_to_uir.py
  build_real_world_uir.py
  validate_real_world_uir.py
  eval_real_world_uir.py

docs/
  real_world_uir_dataset.md
```

说明：

* `raw_cache/` 用于本地运行缓存，不应提交大型原始文件。
* `source_manifest.json` 记录所有真实来源。
* `uir/` 存放最终生成的 UIR JSON。
* `_rejected/` 存放抽取失败或质量不合格的样例。
* `expectations_draft/` 存放可选的人工检查草稿，不作为 gold truth。
* `reports/` 存放抽取、校验和评测报告。

---

## 9. source_manifest.json 规范

新增：

```text
examples/real_world/sources/source_manifest.json
```

建议格式：

```json
{
  "dataset_version": "0.1.0",
  "created_at": "2026-06-29T00:00:00+09:00",
  "description": "Real-world public document sources for SchemaPack Agent UIR evaluation.",
  "items": [
    {
      "source_id": "real_policy_001",
      "doc_type": "policy_doc",
      "title": "公开文档标题",
      "source_url": "https://example.gov.cn/example.html",
      "source_site": "example.gov.cn",
      "source_format": "html",
      "retrieval_method": "requests_html",
      "status": "planned",
      "license_note": "public official webpage for coursework evaluation only",
      "notes": "官方公开政策文件"
    }
  ]
}
```

字段要求：

| 字段               | 必填 | 说明                                                                      |
| ---------------- | -- | ----------------------------------------------------------------------- |
| source_id        | 是  | 唯一来源 ID                                                                 |
| doc_type         | 是  | policy_doc / procurement_doc / contract_doc / meeting_doc / general_doc |
| title            | 是  | 来源文档标题                                                                  |
| source_url       | 是  | 来源 URL                                                                  |
| source_site      | 是  | 域名或站点名称                                                                 |
| source_format    | 是  | html / pdf / docx / txt                                                 |
| retrieval_method | 是  | 抓取方式                                                                    |
| status           | 是  | planned / fetched / extracted / validated / rejected / skipped          |
| license_note     | 是  | 来源使用说明                                                                  |
| notes            | 否  | 备注                                                                      |

---

## 10. UIR 文件命名规范

文件名：

```text
real_{doc_type}_{序号}_{简短英文slug}.json
```

示例：

```text
real_policy_001_emergency_plan.json
real_policy_002_industry_guideline.json
real_procurement_001_hospital_equipment_bid.json
real_contract_001_procurement_contract.json
real_meeting_001_board_resolution.json
real_general_001_service_guide.json
```

`uir_id` 必须与文件名主体一致：

```json
{
  "uir_id": "real_policy_001_emergency_plan"
}
```

---

## 11. UIR 结构要求

Codex 必须先检查当前项目已有 UIR 样例和 Pydantic schema，不得凭空设计完全不兼容的新格式。

优先检查：

```text
backend/app/schemas/
backend/app/services/
examples/demo/
examples/production_like/uir/
examples/production_like/
```

在兼容当前项目 UIR 格式的前提下，真实 UIR 至少应包含：

```json
{
  "uir_id": "real_policy_001_example",
  "doc_type": "policy_doc",
  "language": "zh-CN",
  "source_type": "real_world_public_document",
  "metadata": {
    "title": "文档标题",
    "source_url": "https://example.gov.cn/example.html",
    "source_site": "example.gov.cn",
    "retrieved_at": "2026-06-29T00:00:00+09:00",
    "source_format": "html",
    "source_sha256": "sha256 hash",
    "extraction_method": "html_rule_based",
    "extraction_version": "0.1.0"
  },
  "blocks": [
    {
      "block_id": "b001",
      "type": "heading",
      "level": 1,
      "text": "一级标题",
      "source_ref": {
        "url": "https://example.gov.cn/example.html",
        "selector": "h1"
      }
    },
    {
      "block_id": "b002",
      "type": "paragraph",
      "text": "正文片段",
      "source_ref": {
        "url": "https://example.gov.cn/example.html",
        "selector": "article p:nth-of-type(1)"
      }
    }
  ],
  "tables": [
    {
      "table_id": "t001",
      "title": "表格标题",
      "columns": ["字段1", "字段2"],
      "rows": [
        {
          "字段1": "值1",
          "字段2": "值2"
        }
      ],
      "source_ref": {
        "url": "https://example.gov.cn/example.html",
        "selector": "table:nth-of-type(1)"
      }
    }
  ],
  "hints": {
    "candidate_fields": [
      {
        "name": "issuer",
        "label": "发布机构",
        "value": "某某机构",
        "confidence": 0.85,
        "evidence_block_ids": ["b001", "b002"],
        "review_required": false
      }
    ]
  }
}
```

如当前项目实际字段不同，以项目已有 UIR 为准。

---

## 12. 元数据抽取要求

### 12.1 通用元数据

所有真实 UIR 必须尽量抽取：

```text
title
source_url
source_site
retrieved_at
source_format
source_sha256
language
doc_type
extraction_method
extraction_version
```

### 12.2 政策类 policy_doc 字段

建议抽取：

```text
title
issuer
publish_date
document_no
policy_type
effective_date
applicable_scope
responsible_departments
source_url
```

### 12.3 采购类 procurement_doc 字段

建议抽取：

```text
title
project_name
project_id
buyer
agency
budget
winner
winning_amount
publish_date
bid_open_date
region
source_url
```

### 12.4 合同类 contract_doc 字段

建议抽取：

```text
title
contract_name
party_a
party_b
contract_amount
sign_date
effective_date
term
subject_matter
risk_clauses
source_url
```

### 12.5 会议类 meeting_doc 字段

建议抽取：

```text
title
meeting_name
meeting_date
host
participants
topics
decisions
action_items
source_url
```

### 12.6 通用文档 general_doc 字段

建议抽取：

```text
title
issuer
publish_date
doc_type
summary
sections
key_items
source_url
```

---

## 13. 脚本一：collect_real_world_sources.py

### 13.1 目标

从 `source_manifest.json` 中读取 planned 来源，下载公开文档并记录抓取状态。

### 13.2 输入

```text
examples/real_world/sources/source_manifest.json
```

### 13.3 输出

```text
examples/real_world/raw_cache/
examples/real_world/reports/extraction_report.json
```

### 13.4 基本要求

脚本必须：

1. 支持 HTML、PDF、DOCX 下载。
2. 记录 HTTP 状态码。
3. 记录 content-type。
4. 记录文件大小。
5. 计算 SHA-256。
6. 每个域名请求间隔至少 2 秒。
7. 设置合理 User-Agent。
8. 设置 timeout。
9. 不绕过登录、验证码、付费限制。
10. 遇到失败时记录 error，不中断全局流程。

### 13.5 状态更新

状态可包括：

```text
planned
fetched
failed
skipped
unsupported
```

### 13.6 不允许

不允许：

* 多线程高频抓取
* 无限递归爬取
* 自动点击登录
* 自动破解验证码
* 抓取站内所有链接
* 未经筛选保存大量原文

---

## 14. 脚本二：extract_html_to_uir.py

### 14.1 目标

从 HTML 中抽取标题、元数据、正文块、列表、表格，生成 UIR。

### 14.2 推荐依赖

```text
requests
beautifulsoup4
lxml
python-dateutil
```

### 14.3 抽取策略

优先级：

```text
1. meta 标签
2. h1 / title
3. article / main / .content / .article / .TRS_Editor
4. h2 / h3 / p / li
5. table
6. 正则识别日期、文号、金额、项目编号
7. GPT 辅助字段候选
```

### 14.4 输出

```text
examples/real_world/uir/{doc_type}/{uir_id}.json
```

### 14.5 blocks 生成规则

HTML 元素映射建议：

```text
h1 -> heading level 1
h2 -> heading level 2
h3 -> heading level 3
p  -> paragraph
li -> list_item
table -> table
```

### 14.6 表格抽取

HTML table 应转为：

```json
{
  "table_id": "t001",
  "title": "表格标题",
  "columns": ["列1", "列2"],
  "rows": [
    {
      "列1": "值1",
      "列2": "值2"
    }
  ]
}
```

如果表格结构异常，应保留原始行文本，并标记：

```json
{
  "quality_flags": ["irregular_table_structure"]
}
```

---

## 15. 脚本三：extract_pdf_to_uir.py

### 15.1 目标

从可复制文本 PDF 中抽取文本和表格，生成 UIR。

### 15.2 推荐依赖

优先：

```text
PyMuPDF
pdfplumber
```

可选：

```text
pypdf
```

### 15.3 PDF 类型判断

脚本需要先判断 PDF 是否可复制文本：

```text
如果抽取文本字符数 >= 500，则视为可复制文本 PDF
如果抽取文本字符数 < 500，标记为 suspected_scanned_pdf
如果页面主要是图片，标记为 unsupported_scanned_pdf
```

### 15.4 不处理扫描 PDF

扫描版 PDF 暂不 OCR。

遇到扫描 PDF，输出：

```json
{
  "status": "skipped",
  "reason": "unsupported_scanned_pdf",
  "source_id": "xxx"
}
```

### 15.5 PDF blocks 规则

PDF 文本可按以下规则切分：

```text
1. 按页读取文本
2. 去除页眉页脚
3. 根据空行切分段落
4. 根据中文标题模式识别 heading
5. 根据项目符号识别 list_item
6. 根据表格抽取结果生成 tables
```

### 15.6 source_ref

PDF block 应保留页码：

```json
{
  "source_ref": {
    "url": "https://example.gov.cn/example.pdf",
    "page": 3
  }
}
```

---

## 16. 脚本四：extract_docx_to_uir.py

### 16.1 目标

可选支持 DOCX 文档抽取。

### 16.2 推荐依赖

```text
python-docx
```

### 16.3 抽取内容

抽取：

* 标题
* 段落
* 表格
* 列表
* 文档属性

### 16.4 输出

与 HTML / PDF 一致，保存到：

```text
examples/real_world/uir/{doc_type}/{uir_id}.json
```

---

## 17. 脚本五：build_real_world_uir.py

### 17.1 目标

统一调度 HTML / PDF / DOCX 抽取脚本。

### 17.2 职责

1. 读取 `source_manifest.json`。
2. 判断 `source_format`。
3. 调用对应抽取器。
4. 生成 UIR。
5. 写入 extraction report。
6. 更新 manifest 状态。

### 17.3 命令示例

```powershell
python scripts\build_real_world_uir.py --limit 5
python scripts\build_real_world_uir.py --doc-type policy_doc
python scripts\build_real_world_uir.py --source-id real_policy_001
python scripts\build_real_world_uir.py --all
```

---

## 18. GPT 辅助结构化要求

### 18.1 允许 GPT 做的事

GPT 可以用于：

```text
判断文档类型
提取候选字段
识别标题层级
把长段落切成 blocks
生成摘要
生成关键词
识别表格语义
识别字段别名
判断是否需要人工 review
```

### 18.2 禁止 GPT 做的事

GPT 不得：

```text
凭空补全文档没有的信息
编造发布日期、机构、金额、项目编号
把不确定字段写成确定字段
直接生成 gold truth
直接修改 schema/template active 版本
自动接受 review
自动激活 knowledge pack
保存 API key 或模型密钥
绕过项目现有 LLM 安全策略
```

### 18.3 GPT 输出格式

GPT 辅助输出必须带：

```json
{
  "field": "issuer",
  "value": "某某机构",
  "confidence": 0.82,
  "evidence_text": "原文短证据",
  "evidence_block_ids": ["b002"],
  "review_required": false,
  "reason": "字段标签明确出现"
}
```

低置信字段必须：

```json
{
  "review_required": true,
  "reason": "候选字段来自上下文推断，未出现明确标签"
}
```

---

## 19. 脚本六：validate_real_world_uir.py

### 19.1 目标

检查生成的 UIR 是否可用、可信、可导入。

### 19.2 检查项

必须检查：

```text
是否为合法 JSON
是否包含 uir_id
是否包含 doc_type
是否包含 metadata
是否包含 metadata.title
是否包含 metadata.source_url
是否包含 metadata.retrieved_at
是否包含 metadata.source_sha256
是否至少有 3 个 blocks
是否 blocks 中存在空 text
是否存在异常乱码
是否存在明显个人敏感信息
是否 source_url 合法
是否 doc_type 合法
是否能被现有 Pydantic schema 接受
```

### 19.3 隐私检查

需要正则检查并标记：

```text
手机号
身份证号
个人邮箱
详细住址
银行卡号
```

如果出现疑似敏感信息：

```json
{
  "status": "rejected",
  "reason": "possible_personal_sensitive_information"
}
```

### 19.4 输出

```text
examples/real_world/reports/validation_report.json
examples/real_world/reports/validation_report.md
```

### 19.5 不合格处理

不合格 UIR 移动到：

```text
examples/real_world/uir/_rejected/
```

并在报告中记录原因。

---

## 20. 脚本七：eval_real_world_uir.py

### 20.1 目标

将真实 UIR 接入现有 SchemaPack Agent 执行链路，验证真实样例是否能跑通。

### 20.2 基本流程

对每个 UIR 执行：

```text
1. 读取 UIR JSON
2. POST /api/v1/documents/import
3. 根据 doc_type 选择 schema_id / template_id
4. POST /api/v1/tasks
5. POST /api/v1/tasks/{task_id}/execute
6. GET mapping report
7. GET validation report
8. GET content_organization report
9. GET chunks report
10. GET package metadata
11. 下载 package ZIP
12. 校验 verifier_report
13. 汇总结果
```

### 20.3 schema/template 映射

初始建议：

```json
{
  "policy_doc": {
    "schema_id": "policy_doc",
    "template_id": "policy_doc_base_v1"
  },
  "contract_doc": {
    "schema_id": "contract_doc",
    "template_id": "contract_doc_base_v1"
  },
  "meeting_doc": {
    "schema_id": "meeting_doc",
    "template_id": "meeting_doc_base_v1"
  },
  "general_doc": {
    "schema_id": "general_doc",
    "template_id": "general_doc_base_v1"
  }
}
```

如果当前项目没有 `procurement_doc` schema，则先将采购类映射到：

```text
general_doc
```

或新增 procurement schema/template，但新增时必须保持向后兼容，不得影响现有测试。

### 20.4 输出报告

输出：

```text
reports/real_world_eval_report.json
reports/real_world_eval_report.md
reports/real_world_packages/
```

报告包含：

```json
{
  "dataset_size": 16,
  "by_doc_type": {
    "policy_doc": 5,
    "procurement_doc": 5,
    "meeting_doc": 3,
    "general_doc": 3
  },
  "import_pass_count": 16,
  "task_execute_pass_count": 15,
  "package_verify_pass_count": 15,
  "mapping_review_required_count": 8,
  "high_risk_mapping_count": 2,
  "validation_failed_cases": [],
  "skipped_cases": [],
  "notes": []
}
```

---

## 21. badcase 设计要求

真实样例中应主动包含 badcase，用于验证系统防错能力。

### 21.1 日期字段混淆

包含类似字段：

```text
发布日期
生效日期
截止日期
开标日期
签署日期
合同履行期限
```

目标：检查系统是否把日期字段乱映射。

### 21.2 金额字段混淆

包含类似字段：

```text
预算金额
最高限价
中标金额
成交金额
合同金额
保证金金额
```

目标：检查系统是否把不同金额字段误映射。

### 21.3 主体字段混淆

包含类似字段：

```text
采购人
招标人
代理机构
供应商
中标人
主管部门
责任部门
配合部门
```

目标：检查主体类字段是否误映射。

### 21.4 标题层级混乱

选择标题层级不规范的真实文档。

目标：检查 chunk organization 是否稳定。

### 21.5 表格结构复杂

选择多个表格、合并单元格、无表头表格文档。

目标：检查 table extraction 和 chunks 是否稳定。

---

## 22. 报告要求

### 22.1 extraction_report.md

内容包括：

```text
采集来源数量
成功下载数量
跳过数量
失败数量
HTML 数量
PDF 数量
DOCX 数量
每个 source_id 的状态
失败原因
```

### 22.2 validation_report.md

内容包括：

```text
UIR 总数
通过校验数量
失败数量
可疑敏感信息数量
乱码或空文档数量
字段缺失数量
每个失败样例原因
```

### 22.3 real_world_eval_report.md

内容包括：

```text
真实 UIR 总数
导入成功率
任务执行成功率
package verify 成功率
mapping review_required 数量
high risk mapping 数量
validation failed 数量
每类 doc_type 表现
典型成功案例
典型失败案例
下一步改进建议
```

---

## 23. 验收标准

### 23.1 最小验收标准

必须满足：

```text
1. 新增 examples/real_world/ 目录。
2. 至少生成 16 个真实公开文档 UIR。
3. 每个 UIR 包含 source_url、retrieved_at、source_sha256、doc_type、blocks。
4. 支持 HTML 抽取。
5. 支持可复制文本 PDF 抽取。
6. 扫描 PDF 能识别并跳过。
7. validate_real_world_uir.py 能运行并生成报告。
8. eval_real_world_uir.py 能运行并生成真实评测报告。
9. 至少 80% 的真实 UIR 能成功生成 package。
10. 所有失败样例都有明确失败原因。
```

### 23.2 推荐验收标准

推荐达到：

```text
1. 真实 UIR 数量达到 30 个以上。
2. 覆盖 policy_doc、procurement_doc、contract_doc、meeting_doc、general_doc。
3. 每类至少 3 个样例。
4. 至少包含 5 个 badcase 样例。
5. package verification pass rate >= 90%。
6. real_world_eval_report.md 可用于答辩展示。
7. docs/real_world_uir_dataset.md 说明数据来源、限制和复现方法。
```

---

## 24. 开发顺序

Codex 必须按以下顺序执行：

```text
1. 阅读当前 UIR schema 和 examples/production_like/uir。
2. 总结现有 UIR 必填字段和可选字段。
3. 新建 examples/real_world/ 目录结构。
4. 手工选择或搜索 5 个公开真实 URL 作为试点。
5. 实现 source_manifest.json。
6. 实现 collect_real_world_sources.py。
7. 实现 extract_html_to_uir.py。
8. 实现 extract_pdf_to_uir.py。
9. 实现 build_real_world_uir.py。
10. 生成 3 个 HTML UIR + 2 个 PDF UIR。
11. 实现 validate_real_world_uir.py。
12. 验证 5 个试点 UIR 是否能导入。
13. 调用现有 task API 执行 5 个试点。
14. 若闭环跑通，再扩展到 16 个以上样例。
15. 实现 eval_real_world_uir.py。
16. 生成 real_world_eval_report.md。
17. 更新 docs/real_world_uir_dataset.md。
18. 运行 pytest、ruff、frontend build 或 scripts/verify_all.py。
```

不要一开始就做 30 个样例。必须先跑通 5 个试点闭环。

---

## 25. 推荐依赖

后端 Python 可新增依赖：

```text
requests
beautifulsoup4
lxml
python-dateutil
PyMuPDF
pdfplumber
python-docx
```

注意：

* 新增依赖要写入 `backend/requirements.txt` 或项目实际依赖文件。
* 不要引入 Scrapy 等重型爬虫框架，除非确有必要。
* 如果 pdfplumber 依赖安装困难，可以先只用 PyMuPDF。
* 如果 python-docx 暂不需要，可以放到第二阶段。

---

## 26. API 验证流程

假设后端运行在：

```text
http://127.0.0.1:8000
```

导入 UIR：

```powershell
$uir = Get-Content examples\real_world\uir\policy\real_policy_001_example.json -Raw | ConvertFrom-Json
$body = @{ uir = $uir } | ConvertTo-Json -Depth 100

$document = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/documents/import `
  -ContentType "application/json" `
  -Body $body
```

创建任务：

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "policy_doc"
  schema_version = "1.0.0"
  template_id = "policy_doc_base_v1"
  template_version = "1.0.0"
  options = @{
    content_organization = @{
      chunk_strategy = "heading_aware"
      target_tokens = 768
      min_tokens = 128
      max_tokens = 1024
      overlap_tokens = 80
      protect_tables = $true
      protect_lists = $true
      protect_code_blocks = $true
      enable_parent_child = $false
      enable_light_semantic_boundary = $true
      summary_mode = "deterministic"
      keyword_mode = "deterministic"
    }
  }
} | ConvertTo-Json -Depth 20

$task = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/tasks `
  -ContentType "application/json" `
  -Body $taskBody
```

执行任务：

```powershell
$result = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/execute"
```

读取报告：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

下载 package：

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "real_world_standard_package.zip"
```

---

## 27. 质量控制要求

每次生成 UIR 后，需要检查：

```text
1. 文档标题是否正确。
2. source_url 是否可追溯。
3. source_sha256 是否存在。
4. blocks 是否为空。
5. blocks 是否存在明显乱码。
6. 表格 rows 是否可解析。
7. metadata 是否包含关键字段。
8. hints.candidate_fields 是否有 evidence。
9. 低置信字段是否 review_required。
10. 是否存在个人敏感信息。
11. 是否可以成功导入。
12. 是否可以成功执行 task。
13. 是否可以生成 package。
14. package verifier 是否通过。
```

---

## 28. Git 提交要求

建议提交：

```text
examples/real_world/README.md
examples/real_world/sources/source_manifest.json
examples/real_world/uir/**/*.json
examples/real_world/reports/extraction_report.md
examples/real_world/reports/validation_report.md
scripts/collect_real_world_sources.py
scripts/extract_html_to_uir.py
scripts/extract_pdf_to_uir.py
scripts/build_real_world_uir.py
scripts/validate_real_world_uir.py
scripts/eval_real_world_uir.py
docs/real_world_uir_dataset.md
```

谨慎提交：

```text
examples/real_world/raw_cache/*
reports/real_world_packages/*
大型 PDF / HTML 原始文件
```

如果 raw cache 不提交，需要在 README 中说明如何重新生成。

---

## 29. 文档更新要求

新增：

```text
docs/real_world_uir_dataset.md
```

内容包括：

```text
1. 数据集目的
2. 数据来源范围
3. 支持文档类型
4. 不支持文档类型
5. UIR 生成流程
6. 质量校验规则
7. 真实样例数量
8. 各 doc_type 分布
9. badcase 设计
10. 如何重新运行采集
11. 如何运行真实评测
12. 当前限制
13. 后续扩展方向
```

更新 README，可增加一节：

```text
Real-world UIR Dataset
```

说明：

```text
本项目核心仍然从 UIR 开始。
real_world 工具链只是为了构建真实公开文档 UIR 样例。
该工具链不改变主系统边界。
```

---

## 30. 最终交付物清单

最终应交付：

```text
examples/real_world/README.md
examples/real_world/sources/source_manifest.json
examples/real_world/uir/**/*.json
examples/real_world/reports/extraction_report.json
examples/real_world/reports/extraction_report.md
examples/real_world/reports/validation_report.json
examples/real_world/reports/validation_report.md

scripts/collect_real_world_sources.py
scripts/extract_html_to_uir.py
scripts/extract_pdf_to_uir.py
scripts/build_real_world_uir.py
scripts/validate_real_world_uir.py
scripts/eval_real_world_uir.py

docs/real_world_uir_dataset.md

reports/real_world_eval_report.json
reports/real_world_eval_report.md
```

---

## 31. Codex 执行提示词

可以直接给 Codex 使用：

```text
请根据当前 SchemaPack Agent 项目实现一个“真实公开文档 -> 真实 UIR 数据集”的独立工具链。

重要边界：
1. 不要修改现有 UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP 主链路。
2. 当前项目主输入仍然是 UIR。真实文档解析只作为 examples/real_world 数据集构建工具。
3. 优先支持 HTML 和可复制文本 PDF。
4. 暂不支持扫描 PDF OCR，遇到扫描 PDF 直接标记 skipped。
5. GPT/LLM 只能辅助结构化，不能凭空补字段，不能直接生成 gold truth，不能自动接受 review，不能自动激活 knowledge pack。
6. 每个 UIR 必须包含 source_url、retrieved_at、source_format、source_sha256、extraction_method、doc_type、blocks。
7. 低置信字段必须标记 review_required，并保留 evidence。
8. 先完成 3 个 HTML + 2 个 PDF 的试点闭环，再扩展到至少 16 个真实样例。
9. 每个样例必须能走现有 /api/v1/documents/import、/api/v1/tasks、/api/v1/tasks/{task_id}/execute 流程。
10. 生成 reports/real_world_eval_report.md，总结真实样例导入成功率、任务执行成功率、package verify 成功率、失败原因和后续改进建议。

请按以下步骤执行：
1. 阅读 backend/app/schemas、backend/app/services、examples/production_like/uir，确认现有 UIR 格式。
2. 新建 examples/real_world/ 目录结构。
3. 新建 source_manifest.json。
4. 实现 collect_real_world_sources.py。
5. 实现 extract_html_to_uir.py。
6. 实现 extract_pdf_to_uir.py。
7. 实现 build_real_world_uir.py。
8. 实现 validate_real_world_uir.py。
9. 生成 5 个试点真实 UIR。
10. 调用现有 API 验证导入、任务执行、报告读取、package 下载。
11. 跑通后扩展到至少 16 个真实样例。
12. 实现 eval_real_world_uir.py。
13. 生成 docs/real_world_uir_dataset.md 和 reports/real_world_eval_report.md。
14. 运行 pytest、ruff、frontend build 或 scripts/verify_all.py。
```

---

## 32. 答辩表述建议

完成后可以这样说明：

```text
原系统已经完成课题 5 的核心链路：UIR 到 Schema 驱动标准输出包。
本轮增强没有改变主系统边界，而是在输入侧增加了真实公开文档 UIR 数据集构建工具。
该工具支持从官方公开网页和可复制 PDF 中抽取结构化信息，生成可追溯的真实 UIR。
每个真实 UIR 都保留 source_url、retrieved_at、source_sha256 和 extraction_method。
生成后的真实 UIR 会进入现有导入、映射、转换、校验、打包链路。
这样既验证了系统对真实文档的适应能力，又避免把课题 5 扩展成通用 OCR 或 PDF 解析系统。
```

---

## 33. 总结

本任务的核心不是“让 GPT 直接读 PDF 并凭感觉整理”，而是构建一条可复现、可校验、可追溯的真实 UIR 生成链路。

推荐最终架构：

```text
公开真实 URL
   ↓
HTML / PDF 下载
   ↓
确定性文本与表格抽取
   ↓
规则清洗
   ↓
GPT 辅助字段候选和分块
   ↓
真实 UIR JSON
   ↓
UIR 校验
   ↓
现有 SchemaPack Agent 执行
   ↓
真实评测报告
```

这样既符合课题 5 的边界，也能显著提升项目的真实度和答辩说服力。
