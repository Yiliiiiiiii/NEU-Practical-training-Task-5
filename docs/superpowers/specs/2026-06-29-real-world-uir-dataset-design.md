# SchemaPack Agent 真实公开文档 UIR 数据集设计

> **Historical specification:** Preserved for design rationale. Current status: [`../../project_status.md`](../../project_status.md).

## 目标

在不修改现有 `UIR -> Schema -> Mapping -> Transform -> Canonical -> Render ->
Validate -> Manifest -> ZIP` 主链路的前提下，增加一套独立、可复现、可追溯的真实
公开文档数据集构建工具。工具从官方公开 HTML、可复制文本 PDF 和可选 DOCX 中提取
结构化内容，生成与现有 `UIRDocument` 兼容的 UIR JSON，并通过现有 API 完成导入、
任务执行、报告读取和 package verifier 验证。

最小交付规模为 16 个真实样例：

- `policy_doc`: 5
- `procurement_doc`: 5
- `meeting_doc`: 3
- `general_doc`: 3

实施采用门控式推进：先完成 3 个 HTML 和 2 个 PDF 的试点闭环；只有试点能够导入、
执行并生成 package 后，才扩展至 16 个样例。

## 边界

工具只服务于 `examples/real_world/` 数据集构建，不成为后端在线解析能力，也不改变
主系统输入仍为 UIR 的边界。

支持：

- 无需登录的官方公开 HTML
- 具有可提取文本层的 PDF
- 可选 DOCX
- 标题、段落、列表、表格和有限的确定性元数据抽取
- 来源 URL、抓取时间、原始内容 SHA-256、抽取方法和来源定位记录

不支持：

- 扫描 PDF OCR、图片 OCR
- 登录、验证码、付费墙或反爬绕过
- 个人隐私数据、社交平台内容或新闻长文
- LLM 凭空补全、自动生成 gold truth、自动接受 review 或激活 knowledge pack
- 将大型原始文件提交到 Git

## 与现有 UIR 的兼容设计

现有 `backend/app/schemas/uir.py` 使用严格 Pydantic 模型，顶层字段为：

- `uir_version`
- `doc_id`
- `source`
- `metadata`
- `blocks`
- `assets`
- `normalization_records`

因此指导文档中的建议字段按以下方式映射：

| 指导字段 | 实际存放位置 |
| --- | --- |
| `uir_id` | 使用现有顶层 `doc_id` |
| `doc_type` | `metadata.doc_type`，同时写入 `metadata.domain` |
| `language` | `metadata.language` |
| `source_type` | `source.source_type` |
| `source_url` | `metadata.source_url` |
| `source_site` | `metadata.source_site` |
| `retrieved_at` | `metadata.retrieved_at` |
| `source_format` | `metadata.source_format` |
| `source_sha256` | `metadata.source_sha256` |
| `extraction_method` | `metadata.extraction_method` |
| `hints` | `metadata.hints` |

`source` 固定使用：

```json
{
  "source_type": "real_world_public_document",
  "source_name": "<source_id>",
  "upstream_agents": ["real_world_uir_builder"]
}
```

文本块遵循现有 `UIRBlock`，表格放入 `attributes.rows`，列表放入
`attributes.items`。PDF 页码使用 `source_anchor.page`；HTML 的 DOM 路径、
表格表头和抽取说明放入 `attributes`，不扩展严格 schema。

## 目录与组件

### 数据目录

`examples/real_world/` 保存数据集清单、最终 UIR 和小型报告。`raw_cache/` 仅供本地
抓取缓存，通过 `.gitignore` 排除实际内容，仅保留 `.gitkeep`。

### 采集层

`scripts/collect_real_world_sources.py`：

- 读取 `source_manifest.json`
- 只处理 `planned`、`failed` 或显式指定的项目
- 限制超时、响应大小和重试次数
- 校验 HTTP 状态、Content-Type 与格式
- 保存原始响应并计算 SHA-256
- 原子更新 manifest 状态和抓取元数据
- 对登录页、扫描 PDF 和不支持格式记录明确跳过原因

### 抽取层

`scripts/extract_html_to_uir.py` 使用 BeautifulSoup：

- 移除脚本、样式、导航、页脚和重复空白
- 从 `main`、`article` 或正文候选容器提取内容
- 将标题、段落、列表和表格转换为 UIR blocks
- 从明确标签中抽取日期、机构、编号和金额候选

`scripts/extract_pdf_to_uir.py` 使用 PyMuPDF：

- 按页提取文本块及页码
- 根据文本量判断是否为扫描 PDF
- 识别字号/布局可用时生成标题，否则生成段落
- 扫描 PDF 返回结构化 `skipped` 结果，不调用 OCR

`scripts/extract_docx_to_uir.py` 使用 python-docx，实现指导文档要求的可选第二阶段
支持；段落样式映射为标题/正文，表格映射为 `attributes.rows`。

### 构建层

`scripts/build_real_world_uir.py` 是统一入口：

- 按 manifest 的 `source_format` 选择抽取器
- 生成稳定的 `doc_id`、block ID 和文件名
- 合并通用来源元数据、确定性候选字段和抽取结果
- 将失败样例写入 `_rejected/` 的状态记录
- 更新 extraction JSON/Markdown 报告

### 校验层

`scripts/validate_real_world_uir.py` 检查：

- JSON 可解析并通过现有 `UIRDocument.model_validate`
- `doc_id` 与文件名一致
- doc_type 合法
- 必需来源元数据齐全、URL 合法、SHA-256 格式正确
- 至少三个非空 blocks，block ID 唯一，表格 rows 可解析
- 不含明显乱码
- 不含手机号、身份证号、个人邮箱、银行卡号或疑似详细住址
- 候选字段具有 evidence、confidence 和 review_required

失败文件移动到 `_rejected/`，原因同时写入 JSON/Markdown 校验报告。为避免误移动
用户文件，移动操作仅允许源文件和目标文件均位于 `examples/real_world/uir/` 内。

### 评估层

`scripts/eval_real_world_uir.py` 使用可配置的 `--base-url` 调用现有 HTTP API：

1. 导入 UIR
2. 根据 doc_type 选择 schema/template
3. 创建并执行 task
4. 读取 mapping、validation、content-organization 和 chunks 报告
5. 读取 package metadata、下载 ZIP
6. 读取 verifier report
7. 汇总 JSON/Markdown 报告

`procurement_doc` 在现有项目没有专用 schema/template 时映射到
`general_doc/general_doc_base_v1`。其他类型使用同名 production-like catalog。
脚本接受可选 API key，但不记录密钥。

## 来源与数据策略

所有来源必须是可追溯的官方公开页面或其官方附件。manifest 保存来源标题、URL、
站点、格式、许可说明和状态。Git 中提交的是 URL、提取后的有限结构化内容和摘要，
不是完整长篇原文；原始 HTML/PDF/DOCX 只在本地缓存。

试点优先选择：

- 结构清晰的三份官方 HTML：政策、采购、会议/办事指南
- 两份官方可复制 PDF：政策/采购各一份

扩展阶段补齐最小分布，并主动包含日期、金额、主体、标题层级和复杂表格 badcase。

## 错误处理

每个来源独立处理，一个失败不终止整批任务。所有失败必须归入可机器读取的原因：

- `http_error`
- `unsupported_content_type`
- `unsupported_scanned_pdf`
- `login_or_verification_required`
- `content_too_large`
- `empty_extraction`
- `possible_personal_sensitive_information`
- `uir_schema_validation_failed`
- `api_import_failed`
- `task_execution_failed`
- `package_verification_failed`

报告保留 source_id、阶段、原因和安全截断后的错误信息，不记录 API key 或响应中的
敏感内容。

## 测试与验收

实现遵循测试优先：

- 使用本地固定 HTML/PDF/DOCX fixture 测试确定性抽取，不让单元测试依赖公网
- 先验证测试因缺少行为而失败，再写最小实现使其通过
- 使用现有 FastAPI `TestClient` 验证 UIR 导入兼容性
- 使用临时目录验证缓存、manifest 更新、拒绝文件和报告
- 对真实 5 个试点运行实际 HTTP API 闭环
- 试点通过后扩展至 16 个样例并重新运行评估

最终验证包括：

- 数据集单元/集成测试
- 后端完整 pytest
- Ruff
- 前端 build
- `scripts/verify_all.py`
- 16 个 UIR 的 schema 校验
- 实际评估报告中的 package 成功率不少于 80%

## 交付物

交付指导文档列出的 `examples/real_world/` 目录、七个脚本、数据集说明文档、
抽取/校验报告以及 `reports/real_world_eval_report.{json,md}`。现有主链路文件原则上
不修改；只有依赖清单、`.gitignore` 和根 README 在确有必要时做最小增量修改。
