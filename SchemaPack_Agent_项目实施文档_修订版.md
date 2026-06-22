# 课题 5 项目实施蓝本：数据格式标准化转换智能体（修订版 v2.0）

> 项目名称：SchemaPack Agent  
> 文档用途：开发实施、Codex 任务拆解、验收与产品化拓展  
> 核心边界：仅承担“字段映射 + 转换组织 + 双形态成果封装”，不越权实现解析、清洗、归一、完整质检或完整 RAG。



实施时严格按 P0 闭环优先：先完成 UIR → Schema → Mapping → Transform → Canonical → Render → Validate → Manifest → Zip 的可运行闭环。Phase 10 中的真实模型 fallback、配置快照、包外 verifier、独立评测集和安全强化属于验收增强项，在核心闭环稳定并通过 E2E 测试后再逐项实现。不得在第一轮开发中同时铺开所有产品化拓展能力。

本项目必须采用“样例驱动 + Codex 自动生成样本 + 分阶段扩充”的数据策略。开发初期不要求人工一次性准备完整评测集，而应由 Codex 在 Phase 0 / Phase 1 创建并填充 `examples/` 目录，自动生成一批符合项目 UIR、Target Schema 和 Mapping Template 规范的最小样本数据。Codex 首轮至少应生成 `examples/demo/` 下的两份 UIR 样本、两份 Target Schema 和两份 Mapping Template，用于 Pydantic 模型校验、UIR 导入、Schema / Template 管理、字段候选提取和端到端闭环测试。样本应覆盖 general document 与 policy document 两类场景，并刻意包含 exact_match、alias_match、regex_match、type_match、fuzzy_match、字段转换、日期格式转换、枚举映射、默认值填充和 required 校验等典型能力点。

`examples/` 用于保存 Codex 生成的开发样例、评测样本、金标数据和 badcase，应进入版本管理；`storage/` 只用于程序运行时生成的文档、任务、报告、成果包和临时文件，不得把运行产物当作固定测试样本。字段映射引擎开发前，Codex 应继续生成小规模 `gold_mappings_dev.jsonl`，用于验证 exact、alias、regex、type、fuzzy 等映射策略；主流程稳定后，再由 Codex 扩充 `examples/eval/` 与 `examples/badcases/`，分别存放冻结评测集、金标映射、期望转换结果、异常样例和期望错误。Codex 生成的金标数据可以作为初稿，但在最终验收前应由人工抽查和修正，避免用模型自动生成的未复核金标直接宣称准确率。

最终验收指标必须基于冻结的 eval 数据集计算，demo 样本只用于演示流程跑通，不能用于证明字段映射准确率。Codex 实施时应优先生成 demo 数据并跑通工程闭环，再生成 dev gold mappings 调试映射规则，之后生成 badcase 测试异常路径，最后生成并冻结 eval 集输出正式评测结果。不得在项目初期因准备大规模数据集而阻塞核心工程开发，也不得在没有经过复核的金标数据支撑时宣称字段映射准确率、字段转换正确率或端到端处理成功率。



## 0. 审查结论与本次修订说明

原实施蓝本已经较完整地覆盖了课题 5 的主流程、模块划分、数据模型、API、数据库、前端、测试、验收和风险控制，整体可直接作为开发蓝本使用。经对照任务书，本次修订重点补齐以下容易影响最终验收和产品化价值的内容：

1. **补强智能体属性**：验收版不能只保留 LLM mock，必须至少完成一条真实的“疑难字段映射”模型调用链，并保留规则版、模型版和人工复核版的对照结果。
2. **修正 Target Schema 与 `content.json` 的校验口径**：目标 Schema 校验 `content.json.data`，避免原设计中“目标 Schema 定义扁平对象，但成果文件又套一层 `fields`”的结构冲突。
3. **补齐摘要、标签、实体写入的责任边界**：文档级与 chunk 级摘要必须忠实；内容标签可由规则或模型生成；管理标签来自配置；质量标签只能来自本项目可证明的映射、Schema 和一致性结果；标准实体标签只消费上游归一结果。
4. **补齐可复现、可回放和配置快照**：保存输入哈希、Schema/模板版本、运行参数、模型与提示词版本、随机种子及程序版本，使同一输入与同一配置可重放。
5. **修正 Manifest 与一致性报告的循环依赖**：`manifest.json` 不记录自身哈希；包内 `consistency_report.json` 只检查内容一致性；Manifest 和 ZIP 的最终校验由包外 verifier 完成。
6. **提高评测可信度**：两个演示样例只能证明流程跑通，不能支撑“字段映射准确率 ≥ 85%”。增加独立金标评测集、规则基线与混合策略对比、badcase 分类和下游可读性 smoke test。
7. **补齐私有化与安全基线**：增加离线模式、网络出口开关、文件大小与 JSON 深度限制、路径穿越防护、ZIP 安全、正则超时、密钥管理和依赖锁定。
8. **补齐企业交付物**：除代码和 Demo 外，明确接口与数据规范、评测报告、失败案例、部署说明、技术报告和验收证据。

本修订版中的新增约束均位于课题 5 职责范围内；对课题 1、2、3、4、6、11、12 仍只保留标准接口、适配层或降级实现。


## 1. 项目总体定位

### 1.1 推荐项目名称

**SchemaPack Agent：数据格式标准化转换智能体**

可选中文名：**标准成果包转换智能体**

### 1.2 项目一句话定位

本项目接收上游已经治理好的统一中间表示 **UIR**，根据目标 **Schema** 与字段映射模板，完成字段映射、字段转换、字段重组、多形态渲染、一致性校验与标准成果包封装，输出可被业务系统与 RAG / 训练语料流程直接消费的标准成果包。

### 1.3 课题 5 在数据治理流水线中的位置

完整流水线：

    原始文件
      → 课题 2：解析
      → 课题 3：清洗
      → 课题 4：归一
      → 课题 5：标准化转换与成果封装
      → 课题 6：质量校验
      → 下游系统 / RAG / 训练语料

课题 5 处在“归一之后、质检之前”的转换组织环节，是治理成果进入下游消费系统前的标准化封装层。

### 1.4 本项目输入是什么

MVP 输入：

    UIR JSON
    目标 Target Schema
    Mapping Template
    内容组织参数

其中：

- **UIR JSON**：上游解析、清洗、归一后的统一中间表示；
- **Target Schema**：下游期望的数据结构；
- **Mapping Template**：源字段到目标字段的映射规则、别名、转换规则；
- **内容组织参数**：chunk 长度、标签体系、摘要开关、Markdown 渲染配置等。

### 1.5 本项目输出是什么

最终输出为 `standard_package.zip`。包内必需文件如下：

```text
standard_package/
├── manifest.json
├── metadata.json
├── config_snapshot.json
├── content.json
├── content.md
├── chunks.json
├── mapping_report.json
├── validation_report.json
├── consistency_report.json
├── trace.json
├── assets/
└── exports/                  # 可选：按输出 profile 生成 JSON/JSONL/CSV
```

其中：

- `content.json` 是标准机读成果，`data` 字段保存严格符合 Target Schema 的投影结果；
- `content.md` 是由 Canonical Model 统一渲染的人读全文；
- `chunks.json` 面向 RAG / 训练语料消费，必须保留原文锚点回链；
- `config_snapshot.json` 固化本次任务的输入哈希、Schema/模板版本、运行参数、模型/提示词版本与程序版本；
- `exports/` 为按需开启的输出适配层，不属于 MVP 强制项，但用于证明“一键导出到下游格式”；
- 包外另生成 ZIP 文件自身的 SHA-256，并保存于数据库和下载响应头中。

### 1.6 本项目负责什么

本项目负责：

1.  接收并保存 UIR；

2.  管理 Target Schema；

3.  管理 Mapping Template；

4.  从 UIR 中提取字段候选；

5.  将源字段映射到目标 Schema 字段；

6.  执行字段重命名、合并、拆分、类型转换、枚举映射、默认值填充；

7.  构建统一的 **Canonical Model**；

8.  从 Canonical Model 生成：

    - `content.json`
    - `content.md`
    - `chunks.json`

9.  生成：

    - `mapping_report.json`
    - `validation_report.json`
    - `consistency_report.json`
    - `trace.json`
    - `manifest.json`

10. 计算文件 sha256；

11. 打包 `standard_package.zip`；

12. 提供 RESTful API；

13. 提供人工复核入口；

14. 为外部智能体预留调用接口。

### 1.7 本项目不负责什么

本项目不负责：

1.  不解析 PDF / Word / Excel / PPT / 图片等原始文件；
2.  不做 OCR；
3.  不做复杂版面还原；
4.  不做清洗、脱敏、去噪；
5.  不做术语归一、实体链接、单位换算的完整实现；
6.  不做独立的数据质量总评分；
7.  不实现完整 RAG 系统；
8.  不实现知识库检索；
9.  不直接训练模型；
10. 不承诺复杂问答对生成。

核心边界：

    本项目接收 UIR，不接收复杂原始文档作为核心输入。
    本项目负责把 UIR 转换为标准成果包，不负责把原始文件解析成 UIR。

### 1.8 哪些能力只预留接口

只预留接口，不完整实现：

| 外部能力     | 对应课题    | 本项目处理方式                                    |
|--------------|-------------|---------------------------------------------------|
| 原始文档解析 | 课题 2      | 只接收其输出的 UIR                                |
| 数据清洗     | 课题 3      | 只接收清洗后 UIR                                  |
| 术语归一     | 课题 4      | 只接收归一后 UIR                                  |
| 智能分段     | 课题 11     | 提供 `chunker_adapter`，MVP 可用本地规则 fallback |
| 质量校验     | 课题 6 / 12 | 提供 `quality_adapter`，MVP 只做结构一致性校验    |
| 主控调度     | 课题 1      | 提供 orchestrator 调用接口                        |

### 1.9 哪些能力可以做 fallback

MVP 可提供 fallback：

| 能力        | 首选方式                            | fallback                |
|-------------|-------------------------------------|-------------------------|
| 字段映射    | 规则 + 模板 + 语义相似度 + LLM 兜底 | 规则映射 + 人工复核     |
| 分段        | 调用课题 11                         | 本地按 block / 字数切分 |
| 摘要        | 外部模型 / LLM                      | 使用标题 + 首段截断     |
| 关键词      | 模型 / 词频                         | 简单 TF 词频            |
| Schema 校验 | jsonschema                          | Pydantic + 手写规则     |
| 质检        | 课题 6                              | 本地 consistency_report |

### 1.10 哪些能力不应承诺实现

不应承诺：

1.  任意原始格式文档自动解析；
2.  扫描件 OCR；
3.  复杂表格识别；
4.  图表数据反解；
5.  全自动字段语义理解 100% 准确；
6.  无人工介入处理所有疑难映射；
7.  自动生成高质量训练问答集；
8.  完整企业级权限系统；
9.  分布式大规模任务调度；
10. 独立替代课题 6 的终检评分能力。

### 1.11 受约束的智能体决策闭环

本项目不是开放式自主规划智能体，而是“**确定性主流程 + 疑难映射受约束决策**”的治理智能体。其决策闭环固定为：

```text
观察：读取 UIR、Target Schema、Mapping Template 和上下文
  → 规则求解：exact / alias / regex / type / fuzzy
  → 疑难识别：未映射、冲突、低置信或高风险字段
  → 工具调用：语义模型或 LLM 仅生成候选映射、置信度和依据
  → 约束校验：Pydantic、字段白名单、类型兼容、阈值与冲突检查
  → 路由：自动确认 / 人工复核 / 拒绝继续
  → 执行：确定性 Transform Engine 写入 Canonical Model
  → 留痕：记录规则、模型版本、提示词版本、输入输出与人工修正
```

智能体不得自由增删主流程，不得让 LLM 直接写最终成果，不得绕过人工复核和 Schema 校验。

### 1.12 两类下游与转换模式

课题 5 同时面向业务系统和大模型数据消费，项目需明确两类投影：

- **document 模式（MVP 必须）**：处理文档元数据、正文块、资产引用、摘要、标签和 chunks；
- **recordset 模式（产品化拓展）**：把 UIR 中的简单二维表格行投影为 `records[]`，支持 JSONL / CSV 导出；复杂表格还原仍由课题 8 负责。

MVP 不要求处理嵌套表、跨页表或复杂关系映射，但 Canonical Model 和 Output Profile 应预留 `conversion_mode` 字段，避免后续扩展时推翻数据模型。

## 2. MVP 最小闭环定义

### 2.1 MVP 端到端闭环

MVP 必须跑通：

    输入 UIR JSON
    → 选择目标 Schema
    → 字段候选生成
    → 字段映射
    → 字段转换与重组
    → canonical model 构建
    → 输出 content.json
    → 输出 content.md
    → 输出 chunks.json
    → 生成 mapping_report
    → 生成 validation_report
    → 生成 consistency_report
    → 生成 trace.json
    → 生成 manifest.json
    → 打包 standard_package.zip

### 2.2 MVP 必须实现的功能

1. UIR JSON 上传、版本校验、大小限制与保存；
2. Target Schema 上传、保存、读取和版本绑定；
3. Mapping Template 上传、保存、读取和版本绑定；
4. 字段候选提取；
5. 规则映射：`exact_match`、`alias_match`、`regex_match`、`type_match`、`fuzzy_match`；
6. **真实 LLM/本地模型 fallback 一条可运行链路**，同时保留 mock 和完全离线关闭模式；
7. 低置信、冲突和必填缺失的人工复核；
8. 字段转换：`rename`、`merge`、`split`、`type_cast`、`date_format`、`number_format`、`enum_map`、`default_value`；
9. Canonical Model 构建；
10. `content.json` 渲染，其中 `data` 必须通过 Target Schema；
11. `content.md` 渲染；
12. `chunks.json` 渲染，包含 `source_blocks`、三级标签、摘要、关键词和上游实体标签；
13. 文档级摘要与关键词生成；
14. `mapping_report.json`、`validation_report.json`、`consistency_report.json`、`trace.json` 生成；
15. `config_snapshot.json` 生成；
16. `manifest.json` 生成、文件 SHA-256 计算和 ZIP 原子打包；
17. 包外完整性 verifier；
18. 下载 API、任务重放 API 与统一错误响应；
19. 最小前端页面：导入 UIR、选择 Schema/模板、查看映射、人工复核、执行转换、查看报告、下载成果包；
20. 规则版与“规则 + 模型”版的对比评测脚本。

> 开发阶段可以先使用 mock 联调，但最终验收版本不能只展示 mock；至少应准备 3～5 个规则无法直接判断、模型能够给出合理候选且可人工确认的疑难字段案例。

### 2.3 MVP 可以简化的功能

| 功能     | MVP 简化方式                    |
|----------|---------------------------------|
| 前端     | 不做复杂可视化，只做表单 + 表格 |
| 数据库   | SQLite                          |
| 任务执行 | 同步执行或简单后台任务          |
| LLM      | 先 mock，返回候选字段和置信度   |
| 分段     | 本地规则切分，不强依赖课题 11   |
| 摘要     | 取标题 + 前 200 字作为摘要      |
| 关键词   | 简单词频统计                    |
| 用户系统 | 暂不做登录                      |
| 权限系统 | 暂不做                          |
| 并发队列 | 暂不做复杂队列                  |

### 2.4 MVP 暂不实现但保留接口的功能

1.  调用课题 11 智能分段服务；
2.  调用课题 6 / 12 质量评估服务；
3.  调用课题 1 主控调度；
4.  外部对象存储；
5.  多租户权限；
6.  版本化 Schema 发布；
7.  人工复核操作的学习反馈；
8.  embedding 向量库；
9.  训练语料问答对生成。

### 2.5 MVP 不做的功能

1.  不解析原始 PDF / Word / Excel；
2.  不做 OCR；
3.  不做图片理解；
4.  不做复杂表格结构还原；
5.  不做实体链接；
6.  不做全链路工作流编排；
7.  不做完整 RAG 检索系统；
8.  不做生产级权限审计。

### 2.6 MVP 端到端验收标准

使用 `examples/demo/example_uir_general_doc.json`、`examples/demo/target_schema_general.json`、`examples/demo/mapping_template_general.json` 执行后，应满足：

1.  任务状态变为 `completed`；
2.  生成 `standard_package.zip`；
3.  zip 中包含全部必需文件；
4.  `content.json.data` 通过 Target Schema 校验；
5.  `content.md` 中的 block_id 与 `content.json` 对齐；
6.  `chunks.json` 中每个 chunk 都有 `source_blocks`；
7.  `manifest.json` 记录除自身外的全部 payload 文件及 sha256；
8.  `consistency_report.json` 中 critical error 数量为 0；
9.  `trace.json` 中至少包含字段映射、字段转换、渲染、打包动作；
10. pytest 端到端测试通过。

### 2.7 MVP 验收版与演示版的区别

- **开发联调版**：允许 LLM mock、同步任务和简化前端；
- **最终验收版**：必须完成真实模型 fallback、人工复核、配置快照、独立评测集、包完整性验证和离线运行演示；
- **产品化拓展版**：再增加 Schema/模板发布流程、recordset 模式、输出 profile、Webhook、权限和对象存储。

该分层可避免一开始过度开发，同时保证最终成果具有“智能体属性”和企业回购价值。

## 3. 推荐技术栈

### 3.1 后端框架

推荐：

    Python 3.11+
    FastAPI
    Pydantic v2
    SQLAlchemy 2.x / SQLModel

原因：

- Codex 快速生成和调试成本低；
- FastAPI 自动生成 Swagger；
- Pydantic 适合定义 UIR、Schema、Mapping、Report 等结构；
- Python 生态适合 JSON、Markdown、zip、hash、测试。

### 3.2 前端框架

推荐：

    React + Vite + TypeScript

原因：

- 工程轻量；
- 与 FastAPI 对接方便；
- 适合快速实现表单、表格、JSON 预览、文件下载。

也可选择 Vue 3，但建议统一使用 React + Vite，便于 Codex 生成常规代码。

### 3.3 数据库

推荐：

    SQLite

MVP 使用 SQLite 即可。

后续可切换：

    PostgreSQL

### 3.4 文件存储

推荐：

    project-root/storage/

目录：

    storage/
    ├── documents/
    ├── schemas/
    ├── templates/
    ├── tasks/
    ├── packages/
    └── tmp/

MVP 不需要对象存储。

### 3.5 Schema 校验方式

推荐：

    jsonschema
    Pydantic

分工：

- `jsonschema`：校验动态 Target Schema；
- `Pydantic`：校验系统内部数据结构；
- 自定义 validator：校验 block_id、chunk 回链、manifest、sha256。

### 3.6 大模型调用方式

推荐统一封装：

```text
backend/app/clients/llm_client.py
backend/app/prompts/field_mapping_v1.md
```

原则：

- 所有模型调用必须通过 `LLMClient`，业务代码不得直接访问模型 SDK；
- 支持三种运行模式：`disabled`、`mock`、`openai_compatible`，可扩展本地模型；
- 开发阶段默认 `mock`，最终验收至少启用一次真实模型调用；
- LLM 只输出候选 `target_field_id`、备选项、置信度、依据和风险标记；
- LLM 不直接生成字段最终值，不直接改写 Canonical Model，不直接渲染或打包；
- 输出必须经过 Pydantic 校验、目标字段白名单校验、类型兼容校验和阈值路由；
- 必须记录 provider、model、prompt_version、temperature、token 用量、耗时和原始响应摘要；
- 外部模型可一键关闭，私有化部署时可替换为本地 OpenAI-compatible 服务；
- 提示词必须版本化，变更提示词视为能力版本变更并重新跑回归评测。

验收需报告：规则调用比例、模型调用比例、人工复核比例、模型对字段映射准确率的增益、平均耗时与单任务成本。

### 3.7 是否需要 embedding / 语义相似度

MVP：

    不必须。

推荐实现：

- 第一版不接入向量库；
- 可用 `rapidfuzz` 做字符串相似度；
- 可选用本地 sentence-transformers 作为增强项；
- 不引入 Milvus / FAISS，避免工程过大。

MVP 字段映射优先级：

    exact_match → alias_match → regex_match → type_match → fuzzy_similarity → llm_fallback → manual_review

### 3.8 API 文档工具

使用：

    FastAPI Swagger UI
    OpenAPI JSON

路径：

    /docs
    /openapi.json

### 3.9 测试框架

推荐：

    pytest
    pytest-cov
    httpx

测试对象：

- service 单元测试；
- API 测试；
- 端到端测试；
- 文件输出测试。

### 3.10 代码格式化工具

推荐：

    ruff
    black
    isort
    mypy 可选

### 3.11 部署方式

推荐使用 Docker Compose，至少包含：

```text
backend
frontend
```

MVP 使用 SQLite；产品化阶段可切换 PostgreSQL。部署必须满足：

- `OFFLINE_MODE=true` 时禁止外部网络调用，规则映射、人工复核、渲染、校验和打包仍可完整运行；
- 模型服务地址、密钥、存储路径、上传限制和 CORS 均通过环境变量配置；
- 提供 `/health` 与 `/ready`；
- 容器以非 root 用户运行；
- `storage/` 与数据库目录使用挂载卷；
- `.env.example` 不包含真实密钥；
- Docker 镜像和 Python/Node 依赖版本锁定，保证可复现部署。

### 3.11.1 私有化与安全基线

MVP 即应实现以下底线：

- 限制 UIR、Schema、模板和资产的最大体积、JSON 最大深度与 block 数量；
- 所有路径由 `StorageService` 生成，拒绝 `..`、绝对路径和越界符号链接；
- ZIP 解压与打包防止路径穿越，禁止把存储根目录之外的文件加入成果包；
- 用户提供的正则规则设置超时或安全执行策略，防止 ReDoS；
- MVP 不支持任意表达式执行；产品化阶段若增加表达式规则，只允许白名单 AST；
- 下载接口校验任务与包状态，禁止通过路径参数直接读取任意文件；
- 日志不得记录密钥和完整敏感正文，默认只记录摘要、哈希和必要锚点；
- 外部模型调用前可按配置仅发送字段名、类型和脱敏后的有限上下文；
- 依赖使用锁文件并进行基础漏洞扫描。

### 3.11.2 可复现执行原则

同一 UIR 哈希、同一 Schema/模板版本、同一参数、同一程序/提示词/模型版本应得到相同的确定性路径和稳定结果。需固定排序、时间格式、序列化方式和本地分段规则；模型结果无法完全确定时，应保留原始建议、人工确认结果和最终映射，使任务可以按已确认结果重放。

### 3.12 本地开发方式

后端：

    cd backend
    python -m venv .venv
    source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    pytest

前端：

    cd frontend
    npm install
    npm run dev

Docker：

    docker compose up --build

## 4. 项目目录结构设计

### 4.1 总体目录

    schema-pack-agent/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   ├── api/
    │   │   │   ├── deps.py
    │   │   │   └── v1/
    │   │   │       ├── router.py
    │   │   │       ├── documents.py
    │   │   │       ├── tasks.py
    │   │   │       ├── schemas.py
    │   │   │       ├── templates.py
    │   │   │       ├── mappings.py
    │   │   │       ├── conversions.py
    │   │   │       ├── packages.py
    │   │   │       ├── reports.py
    │   │   │       ├── reviews.py
    │   │   │       └── adapters.py
    │   │   ├── db/
    │   │   │   ├── base.py
    │   │   │   ├── session.py
    │   │   │   └── models.py
    │   │   ├── schemas/
    │   │   │   ├── common.py
    │   │   │   ├── uir.py
    │   │   │   ├── target_schema.py
    │   │   │   ├── mapping_template.py
    │   │   │   ├── mapping.py
    │   │   │   ├── transform.py
    │   │   │   ├── canonical.py
    │   │   │   ├── reports.py
    │   │   │   ├── package.py
    │   │   │   ├── review.py
    │   │   │   └── api.py
    │   │   ├── services/
    │   │   │   ├── document_service.py
    │   │   │   ├── task_service.py
    │   │   │   ├── schema_service.py
    │   │   │   ├── template_service.py
    │   │   │   ├── candidate_service.py
    │   │   │   ├── mapping_service.py
    │   │   │   ├── transform_service.py
    │   │   │   ├── canonical_service.py
    │   │   │   ├── render_service.py
    │   │   │   ├── package_service.py
    │   │   │   ├── report_service.py
    │   │   │   ├── trace_service.py
    │   │   │   ├── review_service.py
    │   │   │   └── storage_service.py
    │   │   ├── engines/
    │   │   │   ├── field_candidate_engine.py
    │   │   │   ├── mapping_engine.py
    │   │   │   ├── transform_engine.py
    │   │   │   ├── canonical_builder.py
    │   │   │   ├── chunk_engine.py
    │   │   │   └── manifest_engine.py
    │   │   ├── renderers/
    │   │   │   ├── json_renderer.py
    │   │   │   ├── markdown_renderer.py
    │   │   │   └── chunks_renderer.py
    │   │   ├── validators/
    │   │   │   ├── schema_validator.py
    │   │   │   ├── required_validator.py
    │   │   │   ├── type_validator.py
    │   │   │   ├── value_range_validator.py
    │   │   │   ├── consistency_validator.py
    │   │   │   └── manifest_validator.py
    │   │   ├── adapters/
    │   │   │   ├── parser_adapter.py
    │   │   │   ├── cleaner_adapter.py
    │   │   │   ├── normalizer_adapter.py
    │   │   │   ├── external_chunker_adapter.py
    │   │   │   ├── quality_adapter.py
    │   │   │   └── orchestrator_adapter.py
    │   │   ├── clients/
    │   │   │   ├── llm_client.py
    │   │   │   └── http_client.py
    │   │   └── utils/
    │   │       ├── ids.py
    │   │       ├── hashing.py
    │   │       ├── time.py
    │   │       ├── json_utils.py
    │   │       ├── markdown_utils.py
    │   │       └── errors.py
    │   ├── tests/
    │   │   ├── conftest.py
    │   │   ├── test_schemas.py
    │   │   ├── test_document_service.py
    │   │   ├── test_schema_service.py
    │   │   ├── test_candidate_engine.py
    │   │   ├── test_mapping_engine.py
    │   │   ├── test_transform_engine.py
    │   │   ├── test_canonical_builder.py
    │   │   ├── test_renderers.py
    │   │   ├── test_validators.py
    │   │   ├── test_manifest_engine.py
    │   │   ├── test_package_service.py
    │   │   ├── test_api.py
    │   │   └── test_e2e_conversion.py
    │   ├── requirements.txt
    │   ├── pyproject.toml
    │   └── Dockerfile
    ├── frontend/
    │   ├── src/
    │   │   ├── api/
    │   │   ├── components/
    │   │   ├── pages/
    │   │   ├── routes/
    │   │   ├── types/
    │   │   └── main.tsx
    │   ├── package.json
    │   └── Dockerfile
    ├── docs/
    │   ├── api.md
    │   ├── data_models.md
    │   ├── package_protocol.md
    │   ├── mapping_engine.md
    │   └── deployment.md
    ├── examples/
    │   ├── example_uir_general_doc.json
    │   ├── example_uir_policy_doc.json
    │   ├── target_schema_general.json
    │   ├── target_schema_policy.json
    │   ├── mapping_template_general.json
    │   ├── mapping_template_policy.json
    │   ├── expected_content.json
    │   ├── expected_content.md
    │   ├── expected_chunks.json
    │   └── expected_manifest.json
    ├── storage/
    │   ├── documents/
    │   ├── schemas/
    │   ├── templates/
    │   ├── tasks/
    │   ├── packages/
    │   └── tmp/
    ├── docker-compose.yml
    ├── .env.example
    ├── .gitignore
    └── README.md

#### 4.1.1 修订版新增文件与目录

在原目录基础上增加：

```text
backend/app/
├── prompts/
│   └── field_mapping_v1.md
├── schemas/
│   ├── run_snapshot.py
│   └── output_profile.py
├── services/
│   ├── replay_service.py
│   └── content_organization_service.py
└── validators/
    └── package_verifier.py

docs/
├── evaluation.md
├── badcase_report.md
├── security_and_offline.md
└── acceptance_demo.md

examples/
├── demo/
├── eval/
├── badcases/
└── consumers/
```

若增加数据库结构变更，建议同时加入 Alembic；三周 MVP 也可使用明确版本号的初始化脚本，但不得依赖手工改表。

### 4.2 目录职责说明

| 目录                      | 职责                                         |
|---------------------------|----------------------------------------------|
| `backend/app/api/`        | API 路由层，只做请求响应，不写业务逻辑       |
| `backend/app/db/`         | 数据库模型、连接、会话                       |
| `backend/app/schemas/`    | Pydantic 请求、响应、内部数据模型            |
| `backend/app/services/`   | 业务编排层                                   |
| `backend/app/engines/`    | 核心算法层：候选、映射、转换、构建、manifest |
| `backend/app/renderers/`  | 多形态输出渲染                               |
| `backend/app/validators/` | 校验模块                                     |
| `backend/app/adapters/`   | 外部智能体适配器                             |
| `backend/app/clients/`    | LLM 和 HTTP 客户端封装                       |
| `backend/app/utils/`      | ID、hash、时间、异常工具                     |
| `backend/tests/`          | 后端测试                                     |
| `frontend/`               | 前端页面                                     |
| `docs/`                   | 项目文档                                     |
| `examples/`               | 示例输入与期望输出                           |
| `storage/`                | 本地文件存储                                 |
| `docker-compose.yml`      | 本地部署编排                                 |

### 4.3 后端文件级职责

#### 入口与基础配置

| 文件          | 职责                                       |
|---------------|--------------------------------------------|
| `main.py`     | 创建 FastAPI app，挂载 v1 router，健康检查 |
| `config.py`   | 读取环境变量，如 storage 路径、LLM 开关    |
| `database.py` | 初始化数据库                               |
| `api/deps.py` | 注入 DB session、service 依赖              |

#### API 路由

| 文件             | 职责                                            |
|------------------|-------------------------------------------------|
| `documents.py`   | UIR 导入、文档列表、文档详情                    |
| `tasks.py`       | 创建转换任务、任务状态                          |
| `schemas.py`     | Target Schema CRUD                              |
| `templates.py`   | Mapping Template CRUD                           |
| `mappings.py`    | 生成候选、执行映射、人工确认                    |
| `conversions.py` | 执行转换、获取 canonical model                  |
| `packages.py`    | 生成、查询、下载成果包                          |
| `reports.py`     | 获取 mapping / validation / consistency / trace |
| `reviews.py`     | 人工复核记录                                    |
| `adapters.py`    | 外部 chunker / quality checker 预留接口         |

#### Service 层

| 文件                   | 职责                                                   |
|------------------------|--------------------------------------------------------|
| `document_service.py`  | 保存 UIR、创建 document 记录、读取文档                 |
| `task_service.py`      | 创建任务、更新任务状态、任务生命周期                   |
| `schema_service.py`    | Target Schema 保存、校验、版本管理                     |
| `template_service.py`  | 映射模板管理、按 Schema 查模板                         |
| `candidate_service.py` | 调用字段候选生成引擎并保存候选                         |
| `mapping_service.py`   | 调用 mapping_engine，保存映射结果，生成 mapping_report |
| `transform_service.py` | 调用 transform_engine，生成字段转换结果                |
| `canonical_service.py` | 构建并保存 canonical model                             |
| `render_service.py`    | 统一调用 JSON / Markdown / chunks renderer             |
| `package_service.py`   | 组织成果文件、manifest、zip                            |
| `report_service.py`    | 读取和聚合报告                                         |
| `trace_service.py`     | 记录每个转换动作                                       |
| `review_service.py`    | 保存人工复核记录并回写映射                             |
| `storage_service.py`   | 文件读写、路径生成、sha256                             |

#### Engine 层

| 文件                        | 职责                                                            |
|-----------------------------|-----------------------------------------------------------------|
| `field_candidate_engine.py` | 从 UIR blocks、metadata、tables 中提取字段候选                  |
| `mapping_engine.py`         | exact / alias / regex / type / semantic / llm / manual 映射流程 |
| `transform_engine.py`       | rename / merge / split / type_cast / enum_map / default         |
| `canonical_builder.py`      | 把转换结果和 UIR 组织成 canonical model                         |
| `chunk_engine.py`           | 本地 fallback 分段                                              |
| `manifest_engine.py`        | 生成 manifest、文件列表、sha256                                 |

#### Renderer 层

| 文件                   | 职责                                   |
|------------------------|----------------------------------------|
| `json_renderer.py`     | 从 canonical model 生成 `content.json` |
| `markdown_renderer.py` | 从 canonical model 生成 `content.md`   |
| `chunks_renderer.py`   | 从 canonical model 生成 `chunks.json`  |

#### Validator 层

| 文件                       | 职责                                          |
|----------------------------|-----------------------------------------------|
| `schema_validator.py`      | JSON Schema 合规校验                          |
| `required_validator.py`    | 必填字段校验                                  |
| `type_validator.py`        | 类型校验                                      |
| `value_range_validator.py` | 值域、枚举、长度校验                          |
| `consistency_validator.py` | JSON / MD / chunks / assets / manifest 一致性 |
| `manifest_validator.py`    | manifest 文件完整性与 sha256 校验             |

#### Adapter 层

| 文件                          | 职责                                             |
|-------------------------------|--------------------------------------------------|
| `parser_adapter.py`           | 定义接收课题 2 UIR 输出的接口，不实现解析        |
| `cleaner_adapter.py`          | 定义接收课题 3 清洗后 UIR 的接口                 |
| `normalizer_adapter.py`       | 定义接收课题 4 归一后 UIR 的接口                 |
| `external_chunker_adapter.py` | 调用课题 11，失败时 fallback 到本地 chunk_engine |
| `quality_adapter.py`          | 把成果包交给课题 6 / 12，MVP 只 mock             |
| `orchestrator_adapter.py`     | 提供给课题 1 调用的统一任务入口                  |

## 5. 后端模块设计

### 5.1 模块总览

| 模块                      | 核心程度 | 建议文件                                   |
|---------------------------|----------|--------------------------------------------|
| UIR 输入适配模块          | 核心入口 | `document_service.py`, `schemas/uir.py`    |
| Schema 管理模块           | 核心     | `schema_service.py`                        |
| Mapping Template 管理模块 | 核心     | `template_service.py`                      |
| 字段候选生成模块          | 核心     | `field_candidate_engine.py`                |
| 字段映射引擎              | 核心核心 | `mapping_engine.py`                        |
| 字段转换与重组引擎        | 核心核心 | `transform_engine.py`                      |
| Canonical Model 构建模块  | 核心核心 | `canonical_builder.py`                     |
| Content JSON 渲染模块     | 核心     | `json_renderer.py`                         |
| Markdown 渲染模块         | 核心     | `markdown_renderer.py`                     |
| Chunks 渲染模块           | 核心     | `chunks_renderer.py`                       |
| 成果包生成模块            | 核心     | `package_service.py`, `manifest_engine.py` |
| Schema 校验模块           | 核心     | `schema_validator.py`                      |
| 一致性校验模块            | 核心     | `consistency_validator.py`                 |
| Manifest 生成模块         | 核心     | `manifest_engine.py`                       |
| Trace 记录模块            | 核心     | `trace_service.py`                         |
| 人工复核模块              | 重要     | `review_service.py`                        |
| 外部智能体接口适配模块    | 边界接口 | `adapters/`                                |
| 任务状态管理模块          | 工程基础 | `task_service.py`                          |

### 5.2 UIR 输入适配模块

- 模块目标：接收上游 UIR JSON，做基本格式校验并落库。
- 输入数据：`UIRDocument`
- 输出数据：`DocumentRecord`
- 是否属于课题 5 核心：是，作为入口。
- 是否需要调用大模型：否。
- 是否可以先做规则版：是。
- 建议文件：
  - `schemas/uir.py`
  - `services/document_service.py`
- 最小实现方式：
  - 校验 `doc_id`、`blocks`、`metadata`；
  - 保存原始 JSON 到 `storage/documents/{doc_id}/uir.json`；
  - 写入 `documents` 表。
- 后续扩展：
  - 支持 UIR version migration；
  - 支持从 parser_adapter 接收远程 UIR。

### 5.3 Schema 管理模块

- 模块目标：管理目标 Schema，支持上传、保存、版本读取。
- 输入数据：`TargetSchema`
- 输出数据：schema 记录、schema 校验结果。
- 核心：是。
- LLM：否。
- 规则版：是。
- 文件：`schema_service.py`, `schemas/target_schema.py`
- 最小实现：
  - 保存 JSON Schema；
  - 校验字段包含 `field_id`、`name`、`type`、`required`；
  - 支持 list / get / create。
- 扩展：
  - Schema 版本 diff；
  - Schema 发布状态。

### 5.4 Mapping Template 管理模块

- 目标：保存字段别名、转换规则、默认值、枚举映射。
- 输入：`MappingTemplate`
- 输出：模板记录。
- 核心：是。
- LLM：否。
- 文件：`template_service.py`, `schemas/mapping_template.py`
- 最小实现：
  - 与 `schema_id` 绑定；
  - 保存 aliases、rules、defaults。
- 扩展：
  - 模板复用；
  - 人工修正反哺模板。

### 5.5 字段候选生成模块

- 目标：从 UIR 中抽取可映射字段。
- 输入：UIR blocks、metadata、tables。
- 输出：`FieldCandidate[]`
- 核心：是。
- LLM：否。
- 文件：`field_candidate_engine.py`
- 最小实现：
  - 从 `metadata` 提取字段；
  - 从 `blocks[].attributes` 提取字段；
  - 从 `table` 类型 block 提取列名；
  - 从标题结构推断 `title`、`section_title`。
- 扩展：
  - 根据上下文识别隐式字段；
  - 引入语义相似度。

### 5.6 字段映射引擎

- 目标：把 FieldCandidate 映射到 Target Schema Field。
- 输入：
  - `FieldCandidate[]`
  - `TargetSchema`
  - `MappingTemplate`
- 输出：
  - `FieldMapping[]`
  - `mapping_report`
- 核心：核心核心。
- LLM：可选兜底。
- 文件：`mapping_engine.py`
- 最小实现：
  - exact_match；
  - alias_match；
  - regex_match；
  - type_match；
  - fuzzy_match；
  - 人工复核标记。
- 扩展：
  - LLM fallback；
  - 历史映射学习；
  - schema-aware mapping。

### 5.7 字段转换与重组引擎

- 目标：执行字段级转换。
- 输入：
  - `FieldMapping[]`
  - UIR values
  - transform rules
- 输出：
  - 标准字段值；
  - trace。
- 核心：核心核心。
- LLM：否。
- 文件：`transform_engine.py`
- 最小实现：
  - rename；
  - merge；
  - split；
  - type_cast；
  - date_format；
  - enum_map；
  - default。
- 扩展：
  - 表达式规则；
  - 条件规则；
  - 可视化规则编辑器。

### 5.8 Canonical Model 构建模块

- 目标：生成统一内部模型，作为所有输出的唯一来源。
- 输入：字段转换结果、UIR blocks、metadata、assets。
- 输出：`CanonicalModel`
- 核心：核心核心。
- LLM：否。
- 文件：`canonical_builder.py`
- 最小实现：
  - 构建 `doc_meta`；
  - 构建 `fields`；
  - 构建 `blocks`；
  - 保留 `source_blocks`；
  - 保留 `assets`。
- 扩展：
  - 支持多 schema projection；
  - 支持版本差异记录。

### 5.9 Content JSON 渲染模块

- 目标：从 canonical model 生成 `content.json`。
- 输入：`CanonicalModel`
- 输出：`content.json`
- 核心：是。
- LLM：否。
- 文件：`json_renderer.py`
- 最小实现：结构化序列化。
- 扩展：支持下游格式 profile。

### 5.10 Markdown 渲染模块

- 目标：从 canonical model 生成人读 Markdown。
- 输入：`CanonicalModel`
- 输出：`content.md`
- 核心：是。
- LLM：否。
- 文件：`markdown_renderer.py`
- 最小实现：
  - 标题；
  - 元数据表；
  - 正文 blocks；
  - block_id 注释；
  - asset 占位符。
- 扩展：
  - 自定义模板；
  - 表格内联渲染。

### 5.11 Chunks 渲染模块

- 目标：生成 `chunks.json`。
- 输入：canonical blocks、分段参数。
- 输出：`chunks.json`
- 核心：是。
- LLM：可选。
- 文件：`chunks_renderer.py`, `chunk_engine.py`
- 最小实现：按 block 和最大长度切分。
- 扩展：调用课题 11。

### 5.12 成果包生成模块

- 目标：生成标准成果包。
- 输入：
  - content.json
  - content.md
  - chunks.json
  - reports
  - trace
  - assets
- 输出：`standard_package.zip`
- 核心：是。
- LLM：否。
- 文件：`package_service.py`
- 最小实现：
  - 写入任务目录；
  - 生成 manifest；
  - zip 打包。
- 扩展：
  - 上传对象存储；
  - 包版本签名。

### 5.13 Schema 校验模块

- 目标：检查 content.json 是否符合 Target Schema。
- 输入：`content.json`, `target_schema`
- 输出：`validation_report`
- 核心：是。
- LLM：否。
- 文件：`schema_validator.py`
- 最小实现：
  - required；
  - type；
  - enum；
  - pattern；
  - min/max。
- 扩展：自定义业务规则。

### 5.14 一致性校验模块

- 目标：检查多形态输出一致性。
- 输入：
  - content.json
  - content.md
  - chunks.json
  - manifest
  - assets
- 输出：`consistency_report`
- 核心：是。
- LLM：否。
- 文件：`consistency_validator.py`
- 最小实现：
  - block_id 对齐；
  - source_blocks 回链；
  - sha256；
  - manifest 完整性。
- 扩展：
  - 文本 hash 对齐；
  - Markdown 反解析对齐。

### 5.15 Manifest 生成模块

- 目标：记录成果包文件清单和校验和。
- 输入：文件列表。
- 输出：`manifest.json`
- 核心：是。
- LLM：否。
- 文件：`manifest_engine.py`
- 最小实现：遍历 package 目录并计算 sha256。
- 扩展：签名、版本策略。

### 5.16 Trace 记录模块

- 目标：记录每次映射、转换、渲染、打包动作。
- 输入：操作事件。
- 输出：`trace.json`, `transform_traces` 表。
- 核心：是。
- LLM：否。
- 文件：`trace_service.py`
- 最小实现：
  - `record_event(task_id, action, before, after, reason)`。
- 扩展：
  - 回放；
  - 回滚；
  - 审计查询。

### 5.17 人工复核模块

- 目标：低置信映射由人工确认或修改。
- 输入：mapping_id、target_field_id、reviewer、decision。
- 输出：review record，更新后的 mapping。
- 核心：重要。
- LLM：否。
- 文件：`review_service.py`
- 最小实现：
  - 保存人工修改；
  - 更新 `field_mappings.status=confirmed`。
- 扩展：
  - 反哺 Mapping Template；
  - 构建 badcase。

### 5.18 外部智能体接口适配模块

- 目标：与其他课题连接但不越权。
- 输入输出：按 adapter 定义。
- 核心：边界。
- LLM：否。
- 文件：`adapters/`
- 最小实现：
  - mock；
  - HTTP client skeleton；
  - fallback。
- 扩展：
  - 接入真实服务注册中心。

### 5.19 任务状态管理模块

- 目标：管理课题 5 内部转换任务生命周期，不承担全流水线编排。
- 输入：任务创建请求、执行事件、人工复核结果。
- 输出：任务状态与阻塞原因。
- 核心：工程基础。
- LLM：否。
- 文件：`task_service.py`

推荐状态机：

```text
created
→ candidates_ready
→ mapping_running
→ mapping_completed
→ review_required ──人工确认──→ mapping_completed
→ transforming
→ rendered
→ validating
→ ready_to_package
→ packaging
→ completed
```

异常状态：

```text
任一执行态 → failed
任一可恢复态 → cancelled
failed / cancelled → replaying → 对应断点状态
```

约束：

- 存在未解决的必填字段、映射冲突或必须复核项时，不得进入 `transforming`；
- `validation_report` 或 `consistency_report` 存在 critical error 时，不得进入 `ready_to_package`；
- ZIP 尚未写完、哈希未完成或包外 verifier 未通过时，不得标记 `completed`；
- 状态更新、文件写入和数据库记录尽量使用事务或补偿逻辑，避免“文件失败但状态成功”。

### 5.20 配置快照、重放与幂等模块

- 文件：`services/replay_service.py`、`schemas/run_snapshot.py`；
- 每次任务保存 `input_hash`、`schema_version`、`template_version`、`options`、`engine_version`、`prompt_version`、`model_config`、`random_seed` 和人工确认映射；
- 相同 `Idempotency-Key` 的创建请求返回同一任务，不重复生成数据；
- `replay` 默认使用原任务已确认映射，不重新请求模型；也可显式选择 `rerun_mapping=true` 做能力回归；
- 任务重放必须生成新 task_id，并通过 `parent_task_id` 建立血缘。

### 5.21 内容组织元数据模块

- 文件：`services/content_organization_service.py`；
- 文档级摘要、chunk 摘要、关键词和标签均从 Canonical Model 生成；
- 摘要默认采用抽取式或“标题 + 首段”降级策略，启用模型时必须限制为基于给定内容总结；
- 内容标签可由规则/模型生成并带置信度；
- 管理标签由 Schema、模板、来源、版本和任务配置确定；
- 质量标签只能反映本项目可验证的状态，如 `mapping:confirmed`、`schema:passed`、`consistency:passed`，不得冒充课题 6/12 的语义质量总评；
- 标准实体标签只读取 UIR 上游归一结果，不在本模块自行做实体链接。

## 6. 前端页面结构设计

### 6.1 页面总览

    /
    ├── /tasks
    ├── /import
    ├── /schemas
    ├── /templates
    ├── /tasks/:taskId
    ├── /tasks/:taskId/mapping
    ├── /tasks/:taskId/preview
    ├── /tasks/:taskId/reports
    └── /tasks/:taskId/package

### 6.2 首页 / 任务列表页

- 页面目标：展示转换任务列表和状态。
- 主要组件：
  - `TaskTable`
  - `StatusBadge`
  - `CreateTaskButton`
- API：
  - `GET /api/v1/tasks`
- 展示数据：
  - task_id
  - doc_id
  - schema_id
  - status
  - created_at
  - updated_at
- MVP 必须：是。
- 简化版：
  - 表格 + 状态 + 详情按钮。

### 6.3 UIR 导入页

- 页面目标：上传或粘贴 UIR JSON。
- 主要组件：
  - `JsonUploader`
  - `JsonPreview`
  - `ImportButton`
- API：
  - `POST /api/v1/documents/import`
- 展示数据：
  - doc_id
  - blocks 数量
  - metadata 摘要
- MVP 必须：是。
- 简化版：
  - 文件上传 + JSON 校验结果。

### 6.4 Schema 管理页

- 页面目标：上传和管理 Target Schema。
- 主要组件：
  - `SchemaList`
  - `SchemaEditor`
  - `SchemaUploadDialog`
- API：
  - `GET /api/v1/schemas`
  - `POST /api/v1/schemas`
  - `GET /api/v1/schemas/{schema_id}`
- 展示数据：
  - schema_id
  - name
  - version
  - fields count
- MVP 必须：是。
- 简化版：
  - 只支持上传 JSON 和查看。

### 6.5 映射模板管理页

- 页面目标：管理 Mapping Template。
- 主要组件：
  - `TemplateList`
  - `TemplateEditor`
- API：
  - `GET /api/v1/templates`
  - `POST /api/v1/templates`
  - `PUT /api/v1/templates/{template_id}`
- 展示数据：
  - template_id
  - schema_id
  - aliases count
  - rules count
- MVP 必须：是。
- 简化版：
  - 只支持上传 JSON。

### 6.6 转换任务详情页

- 页面目标：展示任务执行状态和阶段。
- 组件：
  - `TaskSummary`
  - `PipelineSteps`
  - `RunActionPanel`
- API：
  - `GET /api/v1/tasks/{task_id}`
  - `POST /api/v1/tasks/{task_id}/generate-candidates`
  - `POST /api/v1/tasks/{task_id}/map`
  - `POST /api/v1/tasks/{task_id}/convert`
  - `POST /api/v1/tasks/{task_id}/package`
- MVP 必须：是。
- 简化版：
  - 阶段按钮手动点击执行。

### 6.7 字段映射确认页

- 页面目标：查看候选字段和映射结果，人工修正低置信项。
- 组件：
  - `MappingTable`
  - `ConfidenceBadge`
  - `TargetFieldSelect`
  - `ReviewSubmitButton`
- API：
  - `GET /api/v1/tasks/{task_id}/candidates`
  - `GET /api/v1/tasks/{task_id}/mappings`
  - `POST /api/v1/tasks/{task_id}/mappings/review`
- 展示数据：
  - source field
  - target field
  - method
  - confidence
  - evidence
  - status
- MVP 必须：是。
- 简化版：
  - 表格中可选择目标字段并保存。

### 6.8 转换结果预览页

- 页面目标：预览 content.json、content.md、chunks.json。
- 组件：
  - `JsonViewer`
  - `MarkdownPreview`
  - `ChunksTable`
- API：
  - `GET /api/v1/tasks/{task_id}/canonical`
  - `GET /api/v1/tasks/{task_id}/package/files/content.json`
  - `GET /api/v1/tasks/{task_id}/package/files/content.md`
  - `GET /api/v1/tasks/{task_id}/package/files/chunks.json`
- MVP 必须：是。
- 简化版：
  - 只显示 JSON 文本和 Markdown 文本。

### 6.9 报告查看页

- 页面目标：查看 mapping、validation、consistency、trace。
- 组件：
  - `ReportTabs`
  - `IssueTable`
  - `TraceTimeline`
- API：
  - `GET /api/v1/tasks/{task_id}/reports/mapping`
  - `GET /api/v1/tasks/{task_id}/reports/validation`
  - `GET /api/v1/tasks/{task_id}/reports/consistency`
  - `GET /api/v1/tasks/{task_id}/trace`
- MVP 必须：是。
- 简化版：
  - tabs + JSON viewer。

### 6.10 成果包下载页

- 页面目标：下载 standard_package.zip。
- 组件：
  - `PackageSummary`
  - `ManifestTable`
  - `DownloadButton`
- API：
  - `GET /api/v1/tasks/{task_id}/package`
  - `GET /api/v1/tasks/{task_id}/package/download`
- MVP 必须：是。
- 简化版：
  - 显示包状态和下载按钮。

## 7. 核心数据模型设计

### 7.1 关联 ID 规则

| ID             | 用途                       |
|----------------|----------------------------|
| `doc_id`       | 文档唯一标识               |
| `task_id`      | 一次转换任务唯一标识       |
| `schema_id`    | 目标 Schema 标识           |
| `template_id`  | 映射模板标识               |
| `field_id`     | 目标字段标识               |
| `candidate_id` | 源字段候选标识             |
| `mapping_id`   | 字段映射记录标识           |
| `block_id`     | UIR / canonical block 标识 |
| `chunk_id`     | 分段标识                   |
| `trace_id`     | 追踪记录标识               |
| `package_id`   | 成果包标识                 |

### 7.2 UIR 输入格式

文件：`schemas/uir.py`

    {
      "uir_version": "1.0",
      "doc_id": "doc_001",
      "source": {
        "source_type": "normalized_uir",
        "source_name": "policy_doc_001",
        "upstream_agents": ["parser", "cleaner", "normalizer"]
      },
      "metadata": {
        "title": "数据治理管理办法",
        "author": "信息中心",
        "publish_date": "2026-06-01",
        "doc_type": "policy"
      },
      "blocks": [
        {
          "block_id": "blk_001",
          "type": "heading",
          "level": 1,
          "text": "第一章 总则",
          "source_anchor": {
            "page": 1,
            "bbox": [0, 0, 100, 20]
          },
          "attributes": {
            "section_no": "1"
          }
        },
        {
          "block_id": "blk_002",
          "type": "paragraph",
          "text": "为规范数据治理工作，制定本办法。",
          "source_anchor": {
            "page": 1,
            "bbox": [0, 25, 400, 80]
          },
          "attributes": {}
        }
      ],
      "assets": [
        {
          "asset_id": "asset_001",
          "type": "image",
          "path": "assets/image_001.png",
          "source_block_id": "blk_010",
          "sha256": "..."
        }
      ],
      "normalization_records": []
    }

用途：

- 输入模型；
- 需要入库；
- 原始文件保存到 storage。

### 7.3 Target Schema

    {
      "schema_id": "schema_policy_v1",
      "name": "政策文档标准结构",
      "version": "1.0.0",
      "description": "用于政策类文档标准化输出",
      "fields": [
        {
          "field_id": "title",
          "name": "title",
          "display_name": "标题",
          "type": "string",
          "required": true,
          "aliases": ["文档标题", "题名", "名称"],
          "constraints": {
            "min_length": 1,
            "max_length": 200
          }
        },
        {
          "field_id": "publish_date",
          "name": "publish_date",
          "display_name": "发布日期",
          "type": "date",
          "required": false,
          "aliases": ["发布时间", "印发日期", "发布日期"],
          "constraints": {
            "format": "YYYY-MM-DD"
          }
        }
      ],
      "json_schema": {
        "type": "object",
        "required": ["title"],
        "properties": {
          "title": { "type": "string" },
          "publish_date": { "type": "string", "format": "date" }
        }
      }
    }

用途：

- 需要入库；
- 转换与校验核心配置；
- 最终成果包中可记录 schema 摘要。

### 7.4 Mapping Template

    {
      "template_id": "tpl_policy_v1",
      "schema_id": "schema_policy_v1",
      "name": "政策文档映射模板",
      "version": "1.0.0",
      "aliases": {
        "title": ["标题", "文档标题", "题名", "政策名称"],
        "publish_date": ["发布日期", "发布时间", "印发日期"]
      },
      "regex_rules": [
        {
          "target_field_id": "publish_date",
          "pattern": "(发布日期|印发日期)[:：]\\s*(\\d{4}[-年]\\d{1,2}[-月]\\d{1,2})",
          "group": 2
        }
      ],
      "transform_rules": [
        {
          "rule_id": "rule_date_001",
          "target_field_id": "publish_date",
          "operation": "date_format",
          "params": {
            "input_formats": ["YYYY年M月D日", "YYYY-MM-DD"],
            "output_format": "YYYY-MM-DD"
          }
        }
      ],
      "defaults": {
        "language": "zh-CN"
      },
      "enum_maps": {
        "doc_type": {
          "制度": "policy",
          "办法": "policy",
          "通知": "notice"
        }
      }
    }

用途：

- 需要入库；
- 可复用；
- 支撑规则优先映射。

### 7.5 Field Candidate

    {
      "candidate_id": "cand_001",
      "task_id": "task_001",
      "doc_id": "doc_001",
      "source_path": "metadata.title",
      "source_name": "title",
      "display_name": "标题",
      "value_sample": "数据治理管理办法",
      "inferred_type": "string",
      "source_blocks": ["blk_001"],
      "confidence": 0.95,
      "evidence": ["metadata key matched", "heading level 1 found"]
    }

用途：

- 中间数据；
- MVP 建议入库，方便人工复核。

### 7.6 Field Mapping

    {
      "mapping_id": "map_001",
      "task_id": "task_001",
      "candidate_id": "cand_001",
      "source_field": {
        "source_path": "metadata.title",
        "source_name": "title"
      },
      "target_field_id": "title",
      "target_field_name": "title",
      "method": "exact_match",
      "confidence": 1.0,
      "status": "confirmed",
      "need_review": false,
      "evidence": [
        "source_name equals target field name"
      ]
    }

用途：

- 需要入库；
- 生成 mapping_report；
- 支撑 trace。

### 7.7 Field Transform Rule

    {
      "rule_id": "rule_merge_001",
      "operation": "merge",
      "target_field_id": "full_title",
      "source_fields": ["main_title", "sub_title"],
      "params": {
        "separator": "：",
        "skip_empty": true
      },
      "on_error": "record_and_continue"
    }

用途：

- 可存于 Mapping Template；
- 执行转换；
- 生成 trace。

### 7.8 Conversion Trace

    {
      "trace_id": "trace_001",
      "task_id": "task_001",
      "doc_id": "doc_001",
      "stage": "field_transform",
      "action": "date_format",
      "target_field_id": "publish_date",
      "source": {
        "path": "metadata.publish_date",
        "value": "2026年6月1日"
      },
      "result": {
        "value": "2026-06-01"
      },
      "rule_id": "rule_date_001",
      "reason": "matched date_format rule",
      "status": "success",
      "created_at": "2026-06-22T10:00:00+08:00"
    }

用途：

- 需要入库；
- 最终导出到 `trace.json`。

### 7.9 Canonical Model

系统内部最核心模型。

    {
      "canonical_version": "1.0",
      "task_id": "task_001",
      "doc_id": "doc_001",
      "schema_id": "schema_policy_v1",
      "doc_meta": {
        "title": "数据治理管理办法",
        "publish_date": "2026-06-01",
        "doc_type": "policy"
      },
      "fields": {
        "title": {
          "value": "数据治理管理办法",
          "type": "string",
          "source_candidates": ["cand_001"],
          "source_blocks": ["blk_001"]
        },
        "publish_date": {
          "value": "2026-06-01",
          "type": "date",
          "source_candidates": ["cand_002"],
          "source_blocks": []
        }
      },
      "blocks": [
        {
          "block_id": "blk_001",
          "type": "heading",
          "level": 1,
          "text": "第一章 总则",
          "source_blocks": ["blk_001"],
          "text_hash": "sha256:..."
        },
        {
          "block_id": "blk_002",
          "type": "paragraph",
          "text": "为规范数据治理工作，制定本办法。",
          "source_blocks": ["blk_002"],
          "text_hash": "sha256:..."
        }
      ],
      "assets": [
        {
          "asset_id": "asset_001",
          "type": "image",
          "path": "assets/image_001.png",
          "source_block_id": "blk_010"
        }
      ]
    }

用途：

- 核心内部模型；
- 需要入库；
- 所有输出文件必须从它生成；
- 禁止分别独立生成 JSON / Markdown / chunks。

### 7.10 Content JSON

`content.json` 采用“稳定外层协议 + Target Schema 数据投影”的结构，Target Schema 只校验 `$.data`：

```json
{
  "content_version": "1.1",
  "doc_id": "doc_001",
  "task_id": "task_001",
  "schema_ref": {
    "schema_id": "schema_policy_v1",
    "version": "1.0.0"
  },
  "metadata": {
    "source_name": "policy_doc_001",
    "document_summary": "介绍数据治理管理办法的适用范围和基本要求。",
    "keywords": ["数据治理", "管理办法"]
  },
  "data": {
    "title": "数据治理管理办法",
    "publish_date": "2026-06-01",
    "doc_type": "policy"
  },
  "blocks": [
    {
      "block_id": "blk_001",
      "type": "heading",
      "level": 1,
      "text": "第一章 总则",
      "source_blocks": ["blk_001"]
    }
  ],
  "assets": []
}
```

规则：

- `data` 是下游业务字段投影，也是 Target Schema 的唯一校验对象；
- 外层协议由 SchemaPack Agent 固定维护，不受业务 Schema 任意改写；
- 需要“完全裸对象”时，由 Output Profile 把 `data` 导出到 `exports/<profile>.json`；
- `blocks`、`assets`、溯源字段和摘要用于 RAG、人读渲染与审计，不与业务字段混在一起。

### 7.11 Content Markdown 结构说明

`content.md` 不是单独生成的文本，而是 canonical model 的人读渲染。

建议格式：

    ---
    doc_id: doc_001
    task_id: task_001
    schema_id: schema_policy_v1
    title: 数据治理管理办法
    publish_date: 2026-06-01
    ---
    
    # 数据治理管理办法
    
    <!-- block_id: blk_001 | source_blocks: blk_001 -->
    ## 第一章 总则
    
    <!-- block_id: blk_002 | source_blocks: blk_002 -->
    为规范数据治理工作，制定本办法。

要求：

- 每个 block 保留 `block_id`；
- 每个 block 保留 `source_blocks`；
- Markdown 只用于人读，不作为主数据源；
- 与 content.json 内容必须一致。

### 7.12 Chunks JSON

    {
      "chunks_version": "1.0",
      "doc_id": "doc_001",
      "task_id": "task_001",
      "chunks": [
        {
          "chunk_id": "chk_001",
          "order": 1,
          "text": "第一章 总则\n为规范数据治理工作，制定本办法。",
          "source_blocks": ["blk_001", "blk_002"],
          "title_path": ["数据治理管理办法", "第一章 总则"],
          "labels": {
            "content_tags": ["数据治理", "制度"],
            "management_tags": ["doc_type:policy", "schema:policy_v1"],
            "quality_tags": ["mapping:confirmed", "validation:passed"]
          },
          "summary": "介绍数据治理管理办法的制定目的。",
          "keywords": ["数据治理", "管理办法"],
          "text_hash": "sha256:..."
        }
      ]
    }

用途：

- 最终导出；
- RAG / 训练语料读取。

### 7.13 Mapping Report

    {
      "task_id": "task_001",
      "schema_id": "schema_policy_v1",
      "summary": {
        "target_fields": 5,
        "mapped_fields": 4,
        "unmapped_required_fields": 0,
        "review_required": 1,
        "average_confidence": 0.91
      },
      "mappings": [
        {
          "source_name": "标题",
          "target_field_id": "title",
          "method": "alias_match",
          "confidence": 0.95,
          "need_review": false,
          "evidence": ["标题 in aliases of title"]
        }
      ],
      "unmapped": [],
      "review_required_items": []
    }

用途：

- 最终导出；
- 需要入库。

### 7.14 Validation Report

    {
      "task_id": "task_001",
      "schema_id": "schema_policy_v1",
      "passed": true,
      "summary": {
        "error_count": 0,
        "warning_count": 1
      },
      "issues": [
        {
          "level": "warning",
          "field_id": "publish_date",
          "message": "optional field missing",
          "path": "$.fields.publish_date"
        }
      ]
    }

用途：

- 最终导出；
- 需要入库。

### 7.15 Consistency Report

    {
      "task_id": "task_001",
      "passed": true,
      "checks": [
        {
          "check_name": "json_markdown_block_alignment",
          "passed": true,
          "details": {
            "json_blocks": 2,
            "markdown_blocks": 2
          }
        },
        {
          "check_name": "chunks_source_blocks_backlink",
          "passed": true,
          "details": {
            "chunks": 1,
            "missing_source_blocks": []
          }
        }
      ],
      "errors": [],
      "warnings": []
    }

用途：

- 最终导出；
- 需要入库。

### 7.16 Manifest

```json
{
  "manifest_version": "1.1",
  "package_id": "pkg_001",
  "package_version": "1.0.0",
  "task_id": "task_001",
  "doc_id": "doc_001",
  "created_at": "2026-06-22T10:00:00+08:00",
  "files": [
    {
      "path": "content.json",
      "required": true,
      "media_type": "application/json",
      "sha256": "abc123",
      "bytes": 1234
    }
  ],
  "generator": {
    "name": "SchemaPack Agent",
    "version": "0.2.0",
    "build_commit": "<git_commit>"
  }
}
```

规则：

- `manifest.json` 记录所有 payload 文件，但**不记录自身哈希**，避免自引用循环；
- ZIP 文件自身哈希保存在 `output_packages.sha256` 和下载响应头，不写回 ZIP 内部；
- Manifest 的文件路径必须是标准化相对路径，排序固定；
- 每个条目记录 `required`、`media_type`、`bytes` 和 `sha256`。

### 7.17 Output Package Metadata

    {
      "package_id": "pkg_001",
      "task_id": "task_001",
      "doc_id": "doc_001",
      "schema_id": "schema_policy_v1",
      "template_id": "tpl_policy_v1",
      "package_version": "1.0.0",
      "zip_path": "storage/packages/pkg_001/standard_package.zip",
      "status": "completed",
      "sha256": "zip_sha256",
      "created_at": "2026-06-22T10:00:00+08:00"
    }

用途：

- 需要入库；
- 不一定完整导出，可写入 `metadata.json`。

### 7.18 Review Record

    {
      "review_id": "rev_001",
      "task_id": "task_001",
      "mapping_id": "map_003",
      "candidate_id": "cand_003",
      "old_target_field_id": "summary",
      "new_target_field_id": "abstract",
      "reviewer": "human",
      "decision": "modified",
      "comment": "源字段“摘要”应映射到 abstract",
      "created_at": "2026-06-22T10:05:00+08:00"
    }

用途：

- 需要入库；
- 后续可反哺模板。

### 7.19 模型保存策略

| 模型                    | 是否入库   | 是否导出          | 说明         |
|-------------------------|------------|-------------------|--------------|
| UIR                     | 是         | 可选              | 原始输入保存 |
| Target Schema           | 是         | manifest 记录引用 | 配置         |
| Mapping Template        | 是         | 可选              | 配置         |
| Field Candidate         | 是         | 否                | 中间数据     |
| Field Mapping           | 是         | mapping_report    | 核心结果     |
| Transform Rule          | 是，随模板 | trace             | 规则配置     |
| Conversion Trace        | 是         | trace.json        | 必须导出     |
| Canonical Model         | 是         | 可选              | 核心内部模型 |
| Content JSON            | 文件       | 是                | 必须         |
| Content Markdown        | 文件       | 是                | 必须         |
| Chunks JSON             | 文件       | 是                | 必须         |
| Reports                 | 是         | 是                | 必须         |
| Manifest                | 文件       | 是                | 必须         |
| Output Package Metadata | 是         | metadata.json     | 必须         |
| Review Record           | 是         | 可选              | 人工复核记录 |

### 7.20 Execution Snapshot

```json
{
  "snapshot_version": "1.0",
  "task_id": "task_001",
  "parent_task_id": null,
  "input_hash": "sha256:...",
  "schema_ref": {"schema_id": "schema_policy_v1", "version": "1.0.0"},
  "template_ref": {"template_id": "tpl_policy_v1", "version": "1.0.0"},
  "options": {"chunk_size": 800, "review_threshold": 0.8},
  "engine_version": "0.2.0",
  "build_commit": "<git_commit>",
  "prompt_version": "field_mapping_v1",
  "model": {"mode": "openai_compatible", "name": "configured-model", "temperature": 0},
  "confirmed_mapping_ids": ["map_001"],
  "created_at": "2026-06-22T10:00:00+08:00"
}
```

用途：写入 `config_snapshot.json`，支撑结果复现、能力回归和任务重放。

### 7.21 Output Profile

Output Profile 定义 `content.json.data` 如何导出到具体下游格式，但不改变 Canonical Model：

```json
{
  "profile_id": "policy_jsonl_v1",
  "format": "jsonl",
  "source_path": "$.data",
  "file_name": "exports/policy.jsonl",
  "field_order": ["title", "publish_org", "publish_date", "doc_no", "doc_type"]
}
```

MVP 可只实现一个 JSON profile；JSONL / CSV 作为优先拓展，用于证明成果包可被业务系统直接消费。

## 8. 数据库表结构设计

MVP 使用 SQLite。JSON 字段可使用 `TEXT` 存储 JSON 字符串，后续迁移 PostgreSQL 时改为 `JSONB`。

### 8.1 documents

| 项   | 内容                |
|------|---------------------|
| 用途 | 保存导入的 UIR 文档 |
| 主键 | `doc_id`            |
| MVP  | 必须                |

字段：

| 字段            | 类型     | 说明         |
|-----------------|----------|--------------|
| `doc_id`        | TEXT PK  | 文档 ID      |
| `title`         | TEXT     | 文档标题     |
| `uir_version`   | TEXT     | UIR 版本     |
| `source_name`   | TEXT     | 来源名称     |
| `storage_path`  | TEXT     | UIR 文件路径 |
| `block_count`   | INTEGER  | block 数量   |
| `metadata_json` | TEXT     | 元数据       |
| `created_at`    | DATETIME | 创建时间     |

索引：

    idx_documents_created_at
    idx_documents_title

简化：

- MVP 可不拆 metadata，只存 JSON。

### 8.2 conversion_tasks

| 项 | 内容 |
|---|---|
| 用途 | 转换任务状态、运行快照与血缘 |
| 主键 | task_id |
| 外键 | doc_id, schema_id, template_id |
| MVP | 必须 |

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| task_id | TEXT PK | 任务 ID |
| parent_task_id | TEXT NULL | 重放来源任务 |
| doc_id | TEXT FK | 文档 ID |
| schema_id | TEXT FK | Schema ID |
| schema_version | TEXT | Schema 版本 |
| template_id | TEXT FK | 模板 ID |
| template_version | TEXT | 模板版本 |
| status | TEXT | 状态 |
| input_hash | TEXT | UIR SHA-256 |
| options_json | TEXT | 运行参数 |
| config_snapshot_path | TEXT | 配置快照路径 |
| idempotency_key | TEXT NULL | 幂等键 |
| error_code | TEXT NULL | 结构化错误码 |
| error_message | TEXT NULL | 错误摘要 |
| created_at | DATETIME | 创建 |
| started_at | DATETIME NULL | 开始 |
| finished_at | DATETIME NULL | 完成 |
| updated_at | DATETIME | 更新 |

索引：

```text
idx_tasks_doc_id
idx_tasks_status
idx_tasks_created_at
idx_tasks_parent_task_id
uq_tasks_idempotency_key
```

### 8.3 target_schemas

| 项   | 内容            |
|------|-----------------|
| 用途 | 保存目标 Schema |
| 主键 | `schema_id`     |
| MVP  | 必须            |

字段：

| 字段          | 类型     | 说明        |
|---------------|----------|-------------|
| `schema_id`   | TEXT PK  | Schema ID   |
| `name`        | TEXT     | 名称        |
| `version`     | TEXT     | 版本        |
| `schema_json` | TEXT     | 完整 Schema |
| `json_schema` | TEXT     | JSON Schema |
| `created_at`  | DATETIME | 创建        |

索引：

    idx_target_schemas_name_version

### 8.4 mapping_templates

| 项   | 内容          |
|------|---------------|
| 用途 | 保存映射模板  |
| 主键 | `template_id` |
| 外键 | `schema_id`   |
| MVP  | 必须          |

字段：

| 字段            | 类型     | 说明      |
|-----------------|----------|-----------|
| `template_id`   | TEXT PK  | 模板 ID   |
| `schema_id`     | TEXT FK  | Schema ID |
| `name`          | TEXT     | 名称      |
| `version`       | TEXT     | 版本      |
| `template_json` | TEXT     | 完整模板  |
| `created_at`    | DATETIME | 创建      |

索引：

    idx_templates_schema_id

### 8.5 field_candidates

| 项   | 内容                |
|------|---------------------|
| 用途 | 保存字段候选        |
| 主键 | `candidate_id`      |
| 外键 | `task_id`, `doc_id` |
| MVP  | 必须                |

字段：

| 字段                 | 类型     | 说明       |
|----------------------|----------|------------|
| `candidate_id`       | TEXT PK  | 候选 ID    |
| `task_id`            | TEXT FK  | 任务       |
| `doc_id`             | TEXT FK  | 文档       |
| `source_path`        | TEXT     | 来源路径   |
| `source_name`        | TEXT     | 源字段名   |
| `display_name`       | TEXT     | 展示名     |
| `value_sample`       | TEXT     | 样例值     |
| `inferred_type`      | TEXT     | 推断类型   |
| `source_blocks_json` | TEXT     | 关联 block |
| `confidence`         | REAL     | 候选置信度 |
| `created_at`         | DATETIME | 创建       |

索引：

    idx_candidates_task_id
    idx_candidates_source_name

### 8.6 field_mappings

| 项   | 内容                      |
|------|---------------------------|
| 用途 | 保存源字段到目标字段映射  |
| 主键 | `mapping_id`              |
| 外键 | `task_id`, `candidate_id` |
| MVP  | 必须                      |

字段：

| 字段              | 类型     |
|-------------------|----------|
| `mapping_id`      | TEXT PK  |
| `task_id`         | TEXT FK  |
| `candidate_id`    | TEXT FK  |
| `target_field_id` | TEXT     |
| `method`          | TEXT     |
| `confidence`      | REAL     |
| `status`          | TEXT     |
| `need_review`     | BOOLEAN  |
| `evidence_json`   | TEXT     |
| `created_at`      | DATETIME |
| `updated_at`      | DATETIME |

索引：

    idx_mappings_task_id
    idx_mappings_need_review
    idx_mappings_target_field_id

### 8.7 transform_traces

| 项   | 内容         |
|------|--------------|
| 用途 | 保存转换留痕 |
| 主键 | `trace_id`   |
| 外键 | `task_id`    |
| MVP  | 必须         |

字段：

| 字段              | 类型     |
|-------------------|----------|
| `trace_id`        | TEXT PK  |
| `task_id`         | TEXT FK  |
| `stage`           | TEXT     |
| `action`          | TEXT     |
| `target_field_id` | TEXT     |
| `before_json`     | TEXT     |
| `after_json`      | TEXT     |
| `rule_id`         | TEXT     |
| `reason`          | TEXT     |
| `status`          | TEXT     |
| `created_at`      | DATETIME |

索引：

    idx_traces_task_id
    idx_traces_stage

### 8.8 canonical_models

| 项   | 内容                 |
|------|----------------------|
| 用途 | 保存 canonical model |
| 主键 | `task_id`            |
| MVP  | 必须                 |

字段：

| 字段           | 类型     |
|----------------|----------|
| `task_id`      | TEXT PK  |
| `doc_id`       | TEXT     |
| `schema_id`    | TEXT     |
| `model_json`   | TEXT     |
| `storage_path` | TEXT     |
| `created_at`   | DATETIME |

索引：

    idx_canonical_doc_id

### 8.9 validation_reports

| 项   | 内容                 |
|------|----------------------|
| 用途 | 保存 Schema 校验报告 |
| 主键 | `report_id`          |
| 外键 | `task_id`            |
| MVP  | 必须                 |

字段：

| 字段            | 类型     |
|-----------------|----------|
| `report_id`     | TEXT PK  |
| `task_id`       | TEXT FK  |
| `passed`        | BOOLEAN  |
| `error_count`   | INTEGER  |
| `warning_count` | INTEGER  |
| `report_json`   | TEXT     |
| `created_at`    | DATETIME |

索引：

    idx_validation_task_id

### 8.10 consistency_reports

| 项   | 内容               |
|------|--------------------|
| 用途 | 保存一致性校验报告 |
| 主键 | `report_id`        |
| 外键 | `task_id`          |
| MVP  | 必须               |

字段同 validation_reports。

### 8.11 output_packages

| 项   | 内容             |
|------|------------------|
| 用途 | 保存成果包元数据 |
| 主键 | `package_id`     |
| 外键 | `task_id`        |
| MVP  | 必须             |

字段：

| 字段         | 类型     |
|--------------|----------|
| `package_id` | TEXT PK  |
| `task_id`    | TEXT FK  |
| `doc_id`     | TEXT     |
| `zip_path`   | TEXT     |
| `sha256`     | TEXT     |
| `status`     | TEXT     |
| `created_at` | DATETIME |

索引：

    idx_packages_task_id
    idx_packages_status

### 8.12 package_files

| 项   | 内容                   |
|------|------------------------|
| 用途 | 保存成果包内部文件清单 |
| 主键 | `file_id`              |
| 外键 | `package_id`           |
| MVP  | 必须                   |

字段：

| 字段            | 类型    |
|-----------------|---------|
| `file_id`       | TEXT PK |
| `package_id`    | TEXT FK |
| `relative_path` | TEXT    |
| `media_type`    | TEXT    |
| `bytes`         | INTEGER |
| `sha256`        | TEXT    |

索引：

    idx_package_files_package_id

### 8.13 review_records

| 项   | 内容                    |
|------|-------------------------|
| 用途 | 保存人工复核            |
| 主键 | `review_id`             |
| 外键 | `task_id`, `mapping_id` |
| MVP  | 必须，简化也可          |

字段：

| 字段                  | 类型     |
|-----------------------|----------|
| `review_id`           | TEXT PK  |
| `task_id`             | TEXT FK  |
| `mapping_id`          | TEXT FK  |
| `old_target_field_id` | TEXT     |
| `new_target_field_id` | TEXT     |
| `decision`            | TEXT     |
| `comment`             | TEXT     |
| `reviewer`            | TEXT     |
| `created_at`          | DATETIME |

索引：

    idx_reviews_task_id
    idx_reviews_mapping_id

## 9. API 接口设计

### 9.1 通用错误响应

所有接口统一错误格式：

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request body",
        "details": [
          {
            "path": "$.schema_id",
            "message": "field required"
          }
        ]
      }
    }

常见错误码：

    VALIDATION_ERROR
    NOT_FOUND
    TASK_STATE_ERROR
    SCHEMA_INVALID
    MAPPING_REVIEW_REQUIRED
    PACKAGE_NOT_READY
    INTERNAL_ERROR

### 9.2 API 列表

#### 1. 导入 UIR

- 路径：`POST /api/v1/documents/import`
- Service：`document_service.py`
- MVP：必须

请求：

    {
      "uir": {
        "uir_version": "1.0",
        "doc_id": "doc_001",
        "metadata": { "title": "数据治理管理办法" },
        "blocks": []
      }
    }

响应：

    {
      "doc_id": "doc_001",
      "status": "imported",
      "block_count": 0
    }

#### 2. 获取文档列表

- 路径：`GET /api/v1/documents`
- 参数：`page`, `page_size`
- Service：`document_service.py`
- MVP：必须

响应：

    {
      "items": [
        {
          "doc_id": "doc_001",
          "title": "数据治理管理办法",
          "block_count": 12
        }
      ],
      "total": 1
    }

#### 3. 获取文档详情

- 路径：`GET /api/v1/documents/{doc_id}`
- Service：`document_service.py`
- MVP：必须

响应：

    {
      "doc_id": "doc_001",
      "metadata": { "title": "数据治理管理办法" },
      "blocks_preview": []
    }

#### 4. 创建转换任务

- 路径：`POST /api/v1/tasks`
- Service：`task_service.py`
- MVP：必须

请求：

    {
      "doc_id": "doc_001",
      "schema_id": "schema_policy_v1",
      "template_id": "tpl_policy_v1",
      "options": {
        "chunk_size": 800,
        "enable_llm_fallback": false
      }
    }

响应：

    {
      "task_id": "task_001",
      "status": "created"
    }

#### 5. 查询任务状态

- 路径：`GET /api/v1/tasks/{task_id}`
- Service：`task_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "status": "mapped",
      "doc_id": "doc_001",
      "schema_id": "schema_policy_v1"
    }

#### 6. 上传 / 创建目标 Schema

- 路径：`POST /api/v1/schemas`
- Service：`schema_service.py`
- MVP：必须

请求：

    {
      "schema": {
        "schema_id": "schema_policy_v1",
        "name": "政策文档标准结构",
        "version": "1.0.0",
        "fields": []
      }
    }

响应：

    {
      "schema_id": "schema_policy_v1",
      "status": "created"
    }

#### 7. 获取 Schema 列表

- 路径：`GET /api/v1/schemas`
- Service：`schema_service.py`
- MVP：必须

响应：

    {
      "items": [
        {
          "schema_id": "schema_policy_v1",
          "name": "政策文档标准结构",
          "version": "1.0.0"
        }
      ]
    }

#### 8. 创建 / 修改映射模板

- 创建：`POST /api/v1/templates`
- 修改：`PUT /api/v1/templates/{template_id}`
- Service：`template_service.py`
- MVP：必须

请求：

    {
      "template": {
        "template_id": "tpl_policy_v1",
        "schema_id": "schema_policy_v1",
        "aliases": {},
        "transform_rules": []
      }
    }

响应：

    {
      "template_id": "tpl_policy_v1",
      "status": "saved"
    }

#### 9. 生成字段候选

- 路径：`POST /api/v1/tasks/{task_id}/generate-candidates`
- Service：`candidate_service.py`
- MVP：必须

请求：

    {
      "include_metadata": true,
      "include_blocks": true,
      "include_tables": true
    }

响应：

    {
      "task_id": "task_001",
      "candidate_count": 8,
      "status": "candidate_generated"
    }

#### 10. 获取字段候选

- 路径：`GET /api/v1/tasks/{task_id}/candidates`
- Service：`candidate_service.py`
- MVP：必须

响应：

    {
      "items": [
        {
          "candidate_id": "cand_001",
          "source_name": "标题",
          "source_path": "metadata.title",
          "inferred_type": "string"
        }
      ]
    }

#### 11. 执行字段映射

- 路径：`POST /api/v1/tasks/{task_id}/map`
- Service：`mapping_service.py`
- MVP：必须

请求：

    {
      "enable_llm_fallback": false,
      "review_threshold": 0.8
    }

响应：

    {
      "task_id": "task_001",
      "mapped_count": 5,
      "review_required_count": 1,
      "status": "mapped"
    }

#### 12. 获取字段映射结果

- 路径：`GET /api/v1/tasks/{task_id}/mappings`
- Service：`mapping_service.py`
- MVP：必须

响应：

    {
      "items": [
        {
          "mapping_id": "map_001",
          "source_name": "标题",
          "target_field_id": "title",
          "method": "alias_match",
          "confidence": 0.95
        }
      ]
    }

#### 13. 人工确认 / 修改字段映射

- 路径：`POST /api/v1/tasks/{task_id}/mappings/review`
- Service：`review_service.py`
- MVP：必须

请求：

    {
      "reviews": [
        {
          "mapping_id": "map_003",
          "new_target_field_id": "abstract",
          "decision": "modified",
          "comment": "人工修正"
        }
      ]
    }

响应：

    {
      "task_id": "task_001",
      "updated": 1,
      "status": "review_saved"
    }

#### 14. 执行转换

- 路径：`POST /api/v1/tasks/{task_id}/convert`
- Service：`transform_service.py`, `canonical_service.py`, `render_service.py`
- MVP：必须

请求：

    {
      "render_outputs": true
    }

响应：

    {
      "task_id": "task_001",
      "status": "rendered",
      "outputs": ["content.json", "content.md", "chunks.json"]
    }

#### 15. 获取 canonical model

- 路径：`GET /api/v1/tasks/{task_id}/canonical`
- Service：`canonical_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "doc_id": "doc_001",
      "fields": {},
      "blocks": []
    }

#### 16. 生成成果包

- 路径：`POST /api/v1/tasks/{task_id}/package`
- Service：`package_service.py`
- MVP：必须

请求：

    {
      "package_version": "1.0.0"
    }

响应：

    {
      "package_id": "pkg_001",
      "status": "completed",
      "zip_path": "storage/packages/pkg_001/standard_package.zip"
    }

#### 17. 下载成果包

- 路径：`GET /api/v1/tasks/{task_id}/package/download`
- Service：`package_service.py`
- MVP：必须

响应：

    {
      "file": "standard_package.zip"
    }

实际返回：

    application/zip

#### 18. 获取 mapping_report

- 路径：`GET /api/v1/tasks/{task_id}/reports/mapping`
- Service：`report_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "summary": {
        "mapped_fields": 5,
        "review_required": 1
      }
    }

#### 19. 获取 validation_report

- 路径：`GET /api/v1/tasks/{task_id}/reports/validation`
- Service：`report_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "passed": true,
      "issues": []
    }

#### 20. 获取 consistency_report

- 路径：`GET /api/v1/tasks/{task_id}/reports/consistency`
- Service：`report_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "passed": true,
      "checks": []
    }

#### 21. 获取 trace

- 路径：`GET /api/v1/tasks/{task_id}/trace`
- Service：`trace_service.py`
- MVP：必须

响应：

    {
      "task_id": "task_001",
      "events": [
        {
          "trace_id": "trace_001",
          "stage": "field_mapping",
          "action": "alias_match"
        }
      ]
    }

#### 22. 外部 chunker 适配接口

- 路径：`POST /api/v1/adapters/chunker/preview`
- Service：`external_chunker_adapter.py`
- MVP：可选，先 mock

请求：

    {
      "task_id": "task_001",
      "blocks": [],
      "options": {
        "chunk_size": 800
      }
    }

响应：

    {
      "provider": "local_fallback",
      "chunks": []
    }

#### 23. 外部 quality checker 预留接口

- 路径：`POST /api/v1/adapters/quality/check`
- Service：`quality_adapter.py`
- MVP：预留，先 mock

请求：

    {
      "package_id": "pkg_001",
      "package_path": "storage/packages/pkg_001/standard_package.zip"
    }

响应：

    {
      "provider": "mock_quality_checker",
      "status": "accepted",
      "quality_task_id": "quality_mock_001"
    }

#### 24. 重放任务

- 路径：`POST /api/v1/tasks/{task_id}/replay`
- 作用：使用原配置快照和已确认映射创建新任务；默认不重复调用模型。

请求：

```json
{
  "rerun_mapping": false,
  "override_options": {}
}
```

#### 25. 获取配置快照

- 路径：`GET /api/v1/tasks/{task_id}/snapshot`
- 返回：输入哈希、Schema/模板版本、程序/提示词/模型版本及运行参数。

#### 26. 验证成果包

- 路径：`POST /api/v1/tasks/{task_id}/package/verify`
- 作用：在 ZIP 完成后重新读取 Manifest、校验文件存在性、大小和哈希，结果保存在数据库，不写入 ZIP，避免循环依赖。

#### 27. 下游导出

- 路径：`POST /api/v1/tasks/{task_id}/exports`
- MVP：可选；至少保留 Output Profile 契约。
- 输出：按 profile 生成 JSON、JSONL 或 CSV 文件并加入 Manifest。

### 9.3 API 工程约束

- 写接口支持 `Idempotency-Key`；
- 所有响应包含 `request_id`，任务相关响应包含 `task_id`；
- 状态冲突返回 `409 TASK_STATE_ERROR`，而不是通用 `500`；
- 上传接口设置体积限制并校验 JSON 深度；
- 下载接口返回 `Content-Disposition`、ZIP SHA-256 和 package version；
- OpenAPI 文档作为交付物冻结并纳入契约测试；
- orchestrator 对接可通过回调 URL 或轮询状态实现，但回调必须签名或使用共享令牌。

## 10. 字段映射引擎设计

### 10.1 字段映射引擎职责

`mapping_engine.py` 负责：

1.  读取字段候选；
2.  读取 Target Schema 字段；
3.  读取 Mapping Template；
4.  计算源字段到目标字段的候选映射；
5.  选择最佳映射；
6.  计算置信度；
7.  标记是否需要人工复核；
8.  记录映射依据；
9.  生成 mapping_report；
10. 不直接修改最终 content.json。

### 10.2 输入

    {
      "task_id": "task_001",
      "candidates": [],
      "target_schema": {},
      "mapping_template": {},
      "options": {
        "review_threshold": 0.8,
        "enable_llm_fallback": false
      }
    }

### 10.3 输出

    {
      "mappings": [],
      "mapping_report": {},
      "review_required": []
    }

### 10.4 如何从 UIR 中提取候选字段

候选来源：

1.  `uir.metadata`：

    - `metadata.title`
    - `metadata.author`
    - `metadata.publish_date`

2.  `blocks[].attributes`：

    - `section_no`
    - `doc_type`
    - `table_columns`

3.  `table` block：

    - 表头列名；
    - 单元格样例值；

4.  标题 block：

    - 一级标题可推断 `title`；
    - 章节标题可推断 `section_title`；

5.  正则抽取：

    - `发布日期：2026年6月1日`
    - `作者：信息中心`

候选结构：

    class FieldCandidate(BaseModel):
        candidate_id: str
        source_path: str
        source_name: str
        display_name: str | None
        value_sample: Any | None
        inferred_type: str
        source_blocks: list[str]
        confidence: float
        evidence: list[str]

### 10.5 如何从目标 Schema 中提取目标字段

从 `TargetSchema.fields` 提取：

    class TargetField(BaseModel):
        field_id: str
        name: str
        display_name: str
        type: str
        required: bool
        aliases: list[str] = []
        constraints: dict = {}

建立索引：

    field_id_index
    name_index
    display_name_index
    alias_index
    type_index
    regex_index

### 10.6 字段别名表设计

别名来源优先级：

1.  Mapping Template 中的 aliases；
2.  Target Schema fields 中的 aliases；
3.  系统内置通用别名；
4.  人工复核沉淀的别名。

示例：

    {
      "title": ["标题", "题名", "文档标题", "政策名称"],
      "publish_date": ["发布日期", "发布时间", "印发日期"],
      "author": ["作者", "发布单位", "制发单位", "责任部门"]
    }

### 10.7 映射优先级

固定流程：

    exact_match
    → alias_match
    → regex_match
    → type_match
    → semantic_match
    → llm_fallback
    → manual_review

任何后续步骤不能覆盖更高优先级的高置信映射，除非人工确认。

### 10.8 置信度规则

| 方法                   | 置信度建议  |
|------------------------|-------------|
| exact_match            | 1.00        |
| alias_match            | 0.90 - 0.98 |
| regex_match            | 0.85 - 0.95 |
| type_match + 唯一候选  | 0.70 - 0.85 |
| fuzzy / semantic_match | 0.60 - 0.85 |
| llm_fallback           | 0.50 - 0.85 |
| manual_review          | 1.00        |

推荐阈值：

    confidence >= 0.90：自动确认
    0.75 <= confidence < 0.90：可用但建议复核
    confidence < 0.75：必须人工复核

### 10.9 是否需要人工复核

满足任一条件则 `need_review=true`：

1.  置信度低于 `review_threshold`；
2.  目标字段为 required 但无映射；
3.  一个源字段匹配多个目标字段且分差小于 0.1；
4.  多个源字段映射到同一目标字段但不是 merge 规则；
5.  LLM fallback 给出的依据不足；
6.  类型冲突；
7.  目标字段涉及高风险业务字段。

### 10.10 规则优先设计

规则优先含义：

1.  exact / alias / regex / type 优先；
2.  LLM 只处理剩余疑难项；
3.  LLM 不直接生成最终字段值；
4.  LLM 输出只作为候选映射；
5.  LLM 输出必须经过 schema 校验和置信度判断。

### 10.11 大模型兜底设计

`llm_client.py` 提供：

    class LLMClient:
        def suggest_field_mapping(
            self,
            source_candidate: FieldCandidate,
            target_fields: list[TargetField],
            context: MappingContext,
        ) -> LLMSuggestion:
            ...

LLM 输出必须是：

    {
      "target_field_id": "publish_date",
      "confidence": 0.78,
      "reason": "源字段包含发布日期语义",
      "alternatives": [
        {
          "target_field_id": "created_at",
          "confidence": 0.52
        }
      ]
    }

禁止：

    禁止 LLM 直接输出 content.json
    禁止 LLM 直接改写 canonical model
    禁止 LLM 直接打包成果

### 10.12 mapping_report 生成

mapping_report 包含：

1.  总字段数；
2.  已映射字段数；
3.  必填缺失字段；
4.  低置信字段；
5.  每个字段映射方法；
6.  每个字段证据；
7.  人工复核项。

### 10.13 字段映射准确率评估

在独立评测集中维护 gold mapping：

```json
{
  "sample_id": "eval_001",
  "gold_mappings": [
    {
      "source_path": "metadata.title",
      "target_field_id": "title"
    }
  ]
}
```

至少统计：

```text
mapping_precision = 正确自动映射数 / 自动映射总数
mapping_recall    = 正确自动映射数 / 金标映射总数
mapping_f1        = 2PR / (P + R)
required_recall   = 正确映射的必填字段数 / 金标必填字段数
auto_coverage     = 无需人工即可确认的目标字段数 / 目标字段总数
review_rate       = 进入人工复核的字段数 / 候选映射字段总数
```

验收目标：

- 整体字段映射 F1 ≥ 0.85；
- 规则类确定性字段准确率 ≥ 0.95；
- 必填字段未映射定位率 = 100%；
- 疑难字段必须给出 top-k 候选、置信度和依据；
- 评测集与演示 examples 分离，避免在同一数据上调规则又报告指标。

### 10.14 完整映射示例

源 UIR：

    {
      "metadata": {
        "文档标题": "数据治理管理办法",
        "印发日期": "2026年6月1日"
      }
    }

Target Schema：

    {
      "fields": [
        {
          "field_id": "title",
          "name": "title",
          "aliases": ["文档标题", "题名"]
        },
        {
          "field_id": "publish_date",
          "name": "publish_date",
          "aliases": ["发布日期", "印发日期"]
        }
      ]
    }

映射过程：

    source_name = 文档标题
    exact_match：失败
    alias_match：命中 title.aliases
    target_field_id = title
    confidence = 0.95
    need_review = false
    evidence = ["文档标题 in aliases of title"]

输出：

    {
      "mapping_id": "map_001",
      "source_field": {
        "source_path": "metadata.文档标题",
        "source_name": "文档标题"
      },
      "target_field_id": "title",
      "method": "alias_match",
      "confidence": 0.95,
      "need_review": false,
      "evidence": ["文档标题 in aliases of title"]
    }

### 10.15 置信度校准与规则/模型对比

固定置信度常量只能作为初版启发式，最终应在评测集上检查“高置信是否真的更准确”。至少输出按置信度区间统计的实际准确率，例如 `[0.9,1.0]`、`[0.75,0.9)`、`<0.75`。若时间允许，可计算 Brier Score 或 ECE。

对比实验至少包含：

1. 仅规则映射；
2. 规则 + fuzzy/embedding；
3. 规则 + LLM fallback；
4. 规则 + LLM + 人工复核后的最终结果。

报告准确率/F1、自动覆盖率、人工复核率、模型调用率、耗时与成本，证明大模型确实用于核心疑难映射，而不是装饰性调用。

## 11. 字段转换与重组引擎设计

### 11.1 引擎职责

`transform_engine.py` 负责把已确认的字段映射转换成符合 Target Schema 的字段值。

输入：

    {
      "uir": {},
      "field_mappings": [],
      "transform_rules": []
    }

输出：

    {
      "fields": {},
      "trace_events": [],
      "errors": []
    }

### 11.2 支持的操作

| 操作                       | MVP  | 说明                         |
|----------------------------|------|------------------------------|
| 字段重命名 rename          | 必须 | 源字段值写入目标字段         |
| 字段合并 merge             | 必须 | 多个源字段合并为一个目标字段 |
| 字段拆分 split             | 必须 | 一个源字段拆成多个目标字段   |
| 类型转换 type_cast         | 必须 | string/int/float/date/bool   |
| 日期格式转换 date_format   | 必须 | 中文日期转 ISO               |
| 数值格式转换 number_format | 必须 | 去逗号、中文数字可扩展       |
| 枚举值映射 enum_map        | 必须 | 中文枚举转标准枚举           |
| 默认值填充 default         | 必须 | 缺失时填默认值               |
| 缺失字段处理 missing       | 必须 | required 缺失报错            |
| 必填字段校验 required      | 必须 | validation_report            |
| 值域校验 range             | 必须 | validation_report            |
| 条件规则 conditional       | 加分 | 根据条件执行                 |
| 表达式规则 expression      | 加分 | 简单表达式计算               |

### 11.3 规则配置示例

    {
      "transform_rules": [
        {
          "rule_id": "rename_title",
          "operation": "rename",
          "source_field": "metadata.文档标题",
          "target_field_id": "title"
        },
        {
          "rule_id": "merge_full_title",
          "operation": "merge",
          "source_fields": ["metadata.main_title", "metadata.sub_title"],
          "target_field_id": "full_title",
          "params": {
            "separator": "：",
            "skip_empty": true
          }
        },
        {
          "rule_id": "split_org_code",
          "operation": "split",
          "source_field": "metadata.org_full",
          "target_fields": ["org_name", "org_code"],
          "params": {
            "separator": "|"
          }
        },
        {
          "rule_id": "date_publish",
          "operation": "date_format",
          "source_field": "metadata.印发日期",
          "target_field_id": "publish_date",
          "params": {
            "output_format": "YYYY-MM-DD"
          }
        },
        {
          "rule_id": "doc_type_enum",
          "operation": "enum_map",
          "source_field": "metadata.doc_type",
          "target_field_id": "doc_type",
          "params": {
            "map": {
              "办法": "policy",
              "通知": "notice"
            }
          }
        }
      ]
    }

### 11.4 每类操作输入输出

#### rename

输入：

    {
      "operation": "rename",
      "source_field": "metadata.文档标题",
      "target_field_id": "title"
    }

输出：

    {
      "title": "数据治理管理办法"
    }

#### merge

输入：

    {
      "main_title": "数据治理",
      "sub_title": "管理办法"
    }

输出：

    {
      "full_title": "数据治理：管理办法"
    }

#### split

输入：

    {
      "org_full": "信息中心|ORG001"
    }

输出：

    {
      "org_name": "信息中心",
      "org_code": "ORG001"
    }

#### type_cast

输入：

    {
      "page_count": "12"
    }

输出：

    {
      "page_count": 12
    }

#### date_format

输入：

    {
      "publish_date": "2026年6月1日"
    }

输出：

    {
      "publish_date": "2026-06-01"
    }

#### enum_map

输入：

    {
      "doc_type": "办法"
    }

输出：

    {
      "doc_type": "policy"
    }

#### default

输入：

    {}

输出：

    {
      "language": "zh-CN"
    }

### 11.5 trace 记录

每次转换必须写 trace：

    {
      "stage": "field_transform",
      "action": "enum_map",
      "target_field_id": "doc_type",
      "before": {
        "value": "办法"
      },
      "after": {
        "value": "policy"
      },
      "rule_id": "doc_type_enum",
      "reason": "matched enum map",
      "status": "success"
    }

### 11.6 失败处理

| 失败类型       | 处理                            |
|----------------|---------------------------------|
| required 缺失  | validation_report error         |
| type_cast 失败 | 保留原值，写 error trace        |
| enum 未命中    | warning，可保留原值或填 unknown |
| merge 部分缺失 | 根据 `skip_empty` 决定          |
| split 段数不足 | error 或 warning                |
| date 解析失败  | warning，need_review            |

统一策略：

    转换失败不应导致程序崩溃。
    必须写 trace。
    必须写 validation_report。
    严重错误阻止成果包完成。

## 12. Canonical Model 与多形态渲染设计

### 12.1 为什么不能分别独立生成 JSON 和 Markdown

不能分别独立生成的原因：

1.  两份输出容易内容不一致；
2.  字段转换结果可能不同步；
3.  block_id 和 chunk 回链容易丢失；
4.  trace 无法准确追溯；
5.  后续一致性校验成本高；
6.  不符合治理场景可复现、可审计要求。

正确方式：

    UIR + Mapping + Transform
    → Canonical Model
    → content.json
    → content.md
    → chunks.json

### 12.2 Canonical Model 作为唯一事实源

所有导出文件只允许从 canonical model 生成：

    canonical_model.json
      ├── json_renderer → content.json
      ├── markdown_renderer → content.md
      └── chunks_renderer → chunks.json

### 12.3 content.json 生成

生成规则：

1. 外层 `metadata` 来自 `canonical.doc_meta` 与内容组织结果；
2. `data` 来自 `canonical.fields` 的 Target Schema 投影；
3. 只对 `data` 执行动态 Target Schema 校验；
4. `blocks` 来自 `canonical.blocks`；
5. `assets` 来自 `canonical.assets`；
6. 保留 `block_id`、`source_blocks`、文本哈希与实体引用；
7. 业务方需要裸对象时，通过 Output Profile 导出 `data`，不得改变主协议。

### 12.4 content.md 生成

生成规则：

1.  front matter 写入 doc_id、task_id、schema_id；
2.  文档标题来自 canonical fields；
3.  每个 block 前写 HTML 注释：

<!-- -->

    <!-- block_id: blk_001 | source_blocks: blk_001 -->

4.  heading block 渲染为 `#`；
5.  paragraph 渲染为普通段落；
6.  table 可渲染为 Markdown 表格；
7.  image asset 渲染为占位符：

<!-- -->

    ![asset_001](assets/image_001.png)

### 12.5 chunks.json 生成

MVP 本地规则：

1.  按 block 顺序累积；
2.  超过 `chunk_size` 切分；
3.  heading 作为上下文；
4.  chunk_id 使用稳定规则生成：

<!-- -->

    chunk_id = "chk_" + task_id + "_" + order

5.  每个 chunk 保存 `source_blocks`；
6.  每个 chunk 记录 `text_hash`。

### 12.6 block_id 保留

规则：

- UIR block_id 默认原样保留；
- 如果转换中新增 block，使用：

<!-- -->

    blk_gen_{task_id}_{index}

- 新增 block 必须记录 `source_blocks`。

### 12.7 source_blocks 回链

任何输出 block / chunk 都必须能回链原 UIR block：

    {
      "block_id": "blk_002",
      "source_blocks": ["blk_002"]
    }

合并 block：

    {
      "block_id": "blk_gen_001",
      "source_blocks": ["blk_002", "blk_003"]
    }

### 12.8 assets 引用

assets 不在本项目中深度处理，只保留引用：

    {
      "asset_id": "asset_001",
      "path": "assets/image_001.png",
      "source_block_id": "blk_010"
    }

打包时：

- 如果 asset 文件存在：复制到 package/assets；
- 如果不存在：写 warning；
- 不阻塞文本类成果包，除非 schema 要求 asset 必须存在。

### 12.9 避免内容不一致

一致性策略：

1.  所有输出来自 canonical；
2.  输出后反向校验 block_id；
3.  计算 block text hash；
4.  chunks 的 source_blocks 必须存在于 content.json；
5.  manifest 记录全部文件 sha256；
6.  consistency_report 汇总校验结果。

### 12.10 三级标签、摘要与关键词规范

每个 chunk 的标签分为：

- `content_tags`：主题、关键词或业务分类，可由规则或模型生成，需带生成方式和置信度；
- `management_tags`：文档类型、Schema、来源、版本、部门等，由配置和确定性规则生成；
- `quality_tags`：仅记录本项目可验证状态，如映射是否人工确认、Schema 是否通过、一致性是否通过。

摘要要求：

- 文档级摘要写入 `content.json.metadata.document_summary`；
- chunk 级摘要写入 `chunks.json`；
- 不得引入原文没有的事实；
- fallback 可使用标题、关键句和首段抽取；
- 使用模型时记录 prompt/model 版本，并通过抽样人工核对或基于原文的事实一致性检查。

关键词可由词频/TF-IDF 或模型生成。MVP 不要求复杂语义标签体系，但必须可配置，不能硬编码为单一行业。

### 12.11 实体标签写入边界

若 UIR 含 `normalization_records` 或标准实体列表，本项目负责把 `entity_id`、标准名称和来源 block 写入对应 chunk；若上游没有实体链接结果，则保持空数组或 warning，不自行实现课题 10 的实体消歧。

## 13. 成果包协议设计

### 13.1 标准成果包目录

```text
standard_package/
├── manifest.json
├── metadata.json
├── config_snapshot.json
├── content.json
├── content.md
├── chunks.json
├── mapping_report.json
├── validation_report.json
├── consistency_report.json
├── trace.json
├── assets/
└── exports/                  # 可选
```

`manifest.json` 不列出自身；ZIP 哈希不写入包内，保存在数据库和下载响应头中。

### 13.2 每个文件作用

| 文件/目录 | 作用 | 生成模块 |
|---|---|---|
| `manifest.json` | payload 文件清单、SHA-256、包版本 | `manifest_engine.py` |
| `metadata.json` | 包级元数据与 ZIP 外部标识 | `package_service.py` |
| `config_snapshot.json` | 输入哈希、配置、程序/提示词/模型版本 | `replay_service.py` |
| `content.json` | 稳定外层协议 + `data` 业务投影 + blocks/assets | `json_renderer.py` |
| `content.md` | 人读全文 | `markdown_renderer.py` |
| `chunks.json` | RAG/训练语料分段、标签、摘要和回链 | `chunks_renderer.py` |
| `mapping_report.json` | 字段映射结果、置信度、依据和复核项 | `mapping_service.py` |
| `validation_report.json` | `content.json.data` 的 Schema 校验报告 | `schema_validator.py` |
| `consistency_report.json` | 多形态内容一致性报告，不校验 Manifest | `consistency_validator.py` |
| `trace.json` | 映射、转换、渲染和打包留痕 | `trace_service.py` |
| `assets/` | 外置资产 | `package_service.py` |
| `exports/` | 可选下游 JSON/JSONL/CSV | output profile exporter |

### 13.3 package_version 设计

建议：

    package_version = "1.0.0"

语义：

- major：成果包协议不兼容变化；
- minor：新增兼容字段；
- patch：修复生成逻辑。

### 13.4 package_id 生成

推荐：

    package_id = "pkg_" + doc_id + "_" + task_id + "_" + timestamp

或 UUID：

    pkg_01JZ...

### 13.5 manifest 文件列表

Manifest 必须记录：

1. 规范化相对路径；
2. `media_type`；
3. `bytes`；
4. `sha256`；
5. `required`；
6. 逻辑角色，如 `content`、`report`、`asset`、`export`；
7. 固定排序规则。

```json
{
  "files": [
    {
      "path": "content.json",
      "role": "content",
      "required": true,
      "sha256": "abc",
      "bytes": 1000,
      "media_type": "application/json"
    }
  ]
}
```

不得把 `manifest.json` 自身放入 `files`，否则会形成自哈希循环。

### 13.6 sha256 生成

`utils/hashing.py`：

    def sha256_file(path: Path) -> str:
        ...

规则：

- 文件写入完成后计算；
- zip 生成后也计算；
- manifest 中不包含 zip 自身；
- `output_packages.sha256` 记录 zip sha256。

### 13.7 下游系统如何读取成果包

下游读取流程：

    1. 解压 standard_package.zip
    2. 读取 manifest.json
    3. 校验 required files 是否存在
    4. 校验 sha256
    5. 读取 content.json 入库
    6. 读取 chunks.json 入 RAG
    7. 读取 content.md 给人工查看
    8. 读取 trace/report 做审计

### 13.8 成果包生成失败处理

| 场景 | 处理 |
|---|---|
| `content.json` 未生成 | package failed |
| `data` 未通过 Target Schema | 阻止打包；MVP 不开放 `allow_invalid` 绕过 |
| consistency critical error | 阻止打包 |
| 必需 asset 缺失 | 阻止打包 |
| 可选 asset 缺失 | warning |
| Manifest 生成或哈希失败 | package failed |
| ZIP 写入失败 | package failed |
| 包外 verifier 失败 | 不得标记 completed |

失败时：

1. 更新 task status 为 `failed`；
2. 写入结构化 error trace；
3. 返回明确错误码；
4. 不生成可下载的半成品 ZIP；
5. 临时目录按配置保留，默认仅保留有限时间；
6. 采用临时目录生成、校验后原子移动到正式目录。

### 13.9 无循环依赖的构建顺序

```text
1. 生成 content.json / content.md / chunks.json / 各类报告 / trace / config_snapshot
2. 运行包内内容一致性校验，生成 consistency_report.json
3. 生成 manifest.json（覆盖所有 payload 文件，但排除 manifest 自身）
4. 打包 ZIP，并计算 ZIP SHA-256
5. 包外 verifier 解压或流式读取 ZIP，复核 Manifest、文件大小和 SHA-256
6. verifier 通过后，任务状态才进入 completed
```

包外 verifier 结果保存在数据库或 API 响应中，不再写回 ZIP，以避免修改文件导致 Manifest 失效。

## 14. 一致性校验设计

### 14.1 校验项

一致性校验分为两层。

**A. 包内 `consistency_report.json`：**

| 校验项 | MVP | 说明 |
|---|---|---|
| Target Schema 合规 | 必须 | `content.json.data` 对 Target Schema |
| 必填、类型、值域 | 必须 | required/type/enum/range/pattern |
| JSON / Markdown block 对齐 | 必须 | block_id、顺序与文本 hash |
| chunks 回链完整性 | 必须 | source_blocks 必须存在 |
| assets 引用完整性 | 必须 | 引用与文件对应 |
| 摘要/标签结构完整 | 必须 | 字段存在、类型正确、来源可追踪 |
| 报告结构完整 | 必须 | mapping/validation/trace 等可解析 |

**B. 包外 verifier：**

| 校验项 | MVP | 说明 |
|---|---|---|
| Manifest 文件清单 | 必须 | required 文件存在，路径安全 |
| 文件 bytes 与 SHA-256 | 必须 | 与 ZIP 中真实内容一致 |
| ZIP SHA-256 | 必须 | 保存至数据库和下载响应 |
| 禁止额外危险路径 | 必须 | 无绝对路径、`..` 或越界项 |

这样可避免让 `consistency_report.json` 在 Manifest 生成前后反复改写。

### 14.2 consistency_report.json 示例

```json
{
  "task_id": "task_001",
  "package_id": "pkg_001",
  "passed": true,
  "summary": {
    "critical_errors": 0,
    "errors": 0,
    "warnings": 1,
    "checks_total": 4,
    "checks_passed": 3
  },
  "checks": [
    {
      "check_name": "schema_compliance",
      "severity": "critical",
      "passed": true,
      "message": "content.json.data conforms to target schema"
    },
    {
      "check_name": "json_markdown_block_id_alignment",
      "severity": "critical",
      "passed": true,
      "details": {
        "json_block_count": 12,
        "markdown_block_count": 12,
        "mismatch": []
      }
    },
    {
      "check_name": "chunks_source_blocks_backlink",
      "severity": "critical",
      "passed": true,
      "details": {
        "chunk_count": 3,
        "missing_block_ids": []
      }
    },
    {
      "check_name": "assets_reference_integrity",
      "severity": "warning",
      "passed": false,
      "details": {
        "missing_assets": ["assets/image_001.png"]
      }
    }
  ],
  "errors": [],
  "warnings": [
    {
      "code": "ASSET_MISSING",
      "message": "optional asset file not found but referenced",
      "path": "assets/image_001.png"
    }
  ]
}
```

Manifest 文件清单、文件大小、SHA-256 和 ZIP 安全由包外 verifier 单独输出，不写入该报告。

### 14.3 critical 与 warning

critical：

- required 文件缺失；
- schema 校验失败；
- 必填字段缺失；
- block_id 不一致；
- chunk 回链断裂；
- sha256 不匹配。

warning：

- 可选 asset 缺失；
- 可选字段为空；
- 摘要为空；
- 关键词为空。

### 14.4 下游可用性 smoke test

“文件存在”不等于“下游可用”。验收至少增加两个轻量消费测试：

1. **业务入库消费测试**：读取 `content.json.data` 或 `exports/`，完成反序列化、字段类型检查和一条模拟入库；
2. **RAG 消费测试**：读取 `chunks.json`，验证每个 chunk 的文本、标签、摘要、实体和 `source_blocks` 可被一个最小 loader 正常加载。

不要求实现完整业务系统或完整 RAG，只需用独立 consumer 脚本证明成果包契约可被下游直接读取。

## 15. 外部智能体接口边界

### 15.1 总原则

本项目只做转换组织，不越权实现其他课题。

    能接收，不实现。
    能调用，不内化。
    能 fallback，不替代。

### 15.2 parser_adapter

文件：`adapters/parser_adapter.py`

- 对接：课题 2
- 输入：原始文件引用或 parser 输出 UIR
- 输出：UIR
- 当前实际实现：
  - 只定义 `accept_uir(payload)`；
  - 不解析文件。
- mock：
  - 返回传入 UIR。
- fallback：
  - 用户手动上传 UIR。
- 避免越权：
  - 不引入 PDF / OCR / Office 解析库作为核心能力。

### 15.3 cleaner_adapter

文件：`adapters/cleaner_adapter.py`

- 对接：课题 3
- 输入：清洗后 UIR
- 输出：清洗后 UIR 引用
- 实际实现：
  - 接收并标记 upstream_agents 包含 cleaner。
- mock：
  - 直接 pass through。
- 避免越权：
  - 不做去噪、脱敏、修复。

### 15.4 normalizer_adapter

文件：`adapters/normalizer_adapter.py`

- 对接：课题 4
- 输入：归一后 UIR
- 输出：归一后 UIR 引用
- 实际实现：
  - 校验 normalization_records 可存在；
  - 不执行归一。
- fallback：
  - 如果没有 normalization_records，只给 warning。
- 避免越权：
  - 不做实体链接、地名归一、单位换算。

### 15.5 chunker_adapter

文件：`adapters/external_chunker_adapter.py`

- 对接：课题 11
- 输入：

<!-- -->

    {
      "blocks": [],
      "options": {
        "chunk_size": 800,
        "strategy": "structure_aware"
      }
    }

- 输出：

<!-- -->

    {
      "chunks": []
    }

- 当前实现：
  - HTTP client skeleton；
  - 默认关闭；
  - 本地 `chunk_engine.py` fallback。
- mock：
  - 返回本地分段结果。
- 避免越权：
  - 不做复杂语义分段评估；
  - 不以检索指标闭环优化。

### 15.6 quality_adapter

文件：`adapters/quality_adapter.py`

- 对接：课题 6 / 12
- 输入：成果包路径
- 输出：外部质量任务 ID 或质量报告
- 当前实现：
  - mock accepted。
- fallback：
  - 本项目只生成 validation_report 和 consistency_report。
- 避免越权：
  - 不做语义保真度综合评分；
  - 不做路由决策。

### 15.7 orchestrator_adapter

文件：`adapters/orchestrator_adapter.py`

- 对接：课题 1
- 输入：

<!-- -->

    {
      "doc_id": "doc_001",
      "schema_id": "schema_policy_v1",
      "template_id": "tpl_policy_v1",
      "callback_url": "http://orchestrator/callback"
    }

- 输出：

<!-- -->

    {
      "task_id": "task_001",
      "status": "created"
    }

- 当前实现：
  - 提供统一任务创建接口；
  - 可回调状态。
- 避免越权：
  - 不做全链路调度；
  - 不调解析、清洗、归一全流程。

## 16. 开发任务拆解

## Phase 0：项目初始化

### 任务 0.1 创建目录结构

- 创建：
  - `backend/`
  - `frontend/`
  - `docs/`
  - `examples/`
  - `storage/`
- 完成标准：
  - 目录与本蓝本一致。
- 测试：
  - `tree` 检查。

### 任务 0.2 初始化 FastAPI

- 创建：
  - `backend/app/main.py`
  - `backend/app/api/v1/router.py`
- 完成标准：
  - `GET /health` 返回 ok。
- 测试：
  - `pytest tests/test_api.py`

### 任务 0.3 初始化配置

- 创建：
  - `config.py`
  - `.env.example`
- 完成标准：
  - 可配置 STORAGE_ROOT、DATABASE_URL、ENABLE_LLM。
- 测试：
  - 单元测试配置加载。

### 任务 0.4 初始化数据库

- 创建：
  - `db/models.py`
  - `db/session.py`
  - `database.py`
- 完成标准：
  - SQLite 表可创建。
- 测试：
  - 启动后创建 test.db。

### 任务 0.5 配置 pytest 和格式化

- 创建：
  - `pyproject.toml`
  - `tests/conftest.py`
- 完成标准：
  - `pytest` 可运行；
  - `ruff check` 可运行。

### 任务 0.6 创建 README

- 创建：
  - `README.md`
- 完成标准：
  - 包含启动、测试、目录说明。

## Phase 1：核心数据模型与样例数据

### 任务 1.1 定义 UIR Pydantic 模型

- 创建：
  - `schemas/uir.py`
- 完成标准：
  - 支持 metadata、blocks、assets。
- 测试：
  - `test_schemas.py`

### 任务 1.2 定义 Target Schema 模型

- 创建：
  - `schemas/target_schema.py`
- 完成标准：
  - 支持 fields、json_schema。
- 测试：
  - 合法 / 非法 schema 测试。

### 任务 1.3 定义 Mapping Template 模型

- 创建：
  - `schemas/mapping_template.py`
- 完成标准：
  - 支持 aliases、regex_rules、transform_rules、defaults。
- 测试：
  - 模板解析测试。

### 任务 1.4 定义 Mapping / Transform / Canonical / Reports 模型

- 创建：
  - `schemas/mapping.py`
  - `schemas/transform.py`
  - `schemas/canonical.py`
  - `schemas/reports.py`
  - `schemas/package.py`
- 完成标准：
  - 所有模型可被 Pydantic 校验。
- 测试：
  - schema round-trip。

### 任务 1.5 创建 examples

- 创建：
  - `example_uir_general_doc.json`
  - `example_uir_policy_doc.json`
  - `target_schema_general.json`
  - `target_schema_policy.json`
  - `mapping_template_general.json`
  - `mapping_template_policy.json`
- 完成标准：
  - examples 可被模型加载。
- 测试：
  - `test_examples_load.py`

## Phase 2：任务与文档管理

### 任务 2.1 实现 StorageService

- 修改：
  - `storage_service.py`
- 完成标准：
  - 支持 save_json、read_json、write_text、copy_file、sha256。
- 测试：
  - 文件写读测试。

### 任务 2.2 实现 UIR 导入

- 修改：
  - `document_service.py`
  - `documents.py`
- 完成标准：
  - POST 导入后写 DB 和 storage。
- 测试：
  - API 导入测试。

### 任务 2.3 实现文档列表与详情

- 修改：
  - `documents.py`
- 完成标准：
  - GET list/detail 正常。
- 测试：
  - API 测试。

### 任务 2.4 实现转换任务创建

- 修改：
  - `task_service.py`
  - `tasks.py`
- 完成标准：
  - 创建 task，状态 `created`。
- 测试：
  - task 创建测试。

### 任务 2.5 实现任务状态更新

- 修改：
  - `task_service.py`
- 完成标准：
  - 状态合法流转。
- 测试：
  - 非法状态跳转报错。

## Phase 3：Schema 与模板管理

### 任务 3.1 实现 Target Schema CRUD

- 修改：
  - `schema_service.py`
  - `schemas.py`
- 完成标准：
  - create/list/get。
- 测试：
  - API 测试。

### 任务 3.2 实现 Schema validation

- 修改：
  - `schema_validator.py`
- 完成标准：
  - 校验 schema 结构和 fields。
- 测试：
  - required field 缺失测试。

### 任务 3.3 实现 Mapping Template CRUD

- 修改：
  - `template_service.py`
  - `templates.py`
- 完成标准：
  - create/list/get/update。
- 测试：
  - API 测试。

### 任务 3.4 模板与 Schema 绑定校验

- 修改：
  - `template_service.py`
- 完成标准：
  - template.schema_id 必须存在。
- 测试：
  - 不存在 schema_id 报错。

## Phase 4：字段候选与映射

### 任务 4.1 实现候选字段提取

- 修改：
  - `field_candidate_engine.py`
  - `candidate_service.py`
- 完成标准：
  - 从 metadata / blocks / table 提取候选。
- 测试：
  - 候选数量和 source_path 断言。

### 任务 4.2 实现生成候选 API

- 修改：
  - `mappings.py`
- 完成标准：
  - `/generate-candidates` 可用。
- 测试：
  - API 测试。

### 任务 4.3 实现 exact_match

- 修改：
  - `mapping_engine.py`
- 完成标准：
  - 源字段名等于目标 name 时 confidence=1。
- 测试：
  - exact_match 单测。

### 任务 4.4 实现 alias_match

- 修改：
  - `mapping_engine.py`
- 完成标准：
  - 命中 aliases。
- 测试：
  - 中文别名映射测试。

### 任务 4.5 实现 regex_match

- 修改：
  - `mapping_engine.py`
- 完成标准：
  - 正则从 block text 抽取字段。
- 测试：
  - 发布日期抽取测试。

### 任务 4.6 实现 type_match

- 修改：
  - `mapping_engine.py`
- 完成标准：
  - 类型兼容加权。
- 测试：
  - date/string 类型匹配测试。

### 任务 4.7 实现 fuzzy / semantic mock

- 修改：
  - `mapping_engine.py`
- 完成标准：
  - 使用 rapidfuzz 或简单相似度。
- 测试：
  - 相似名称匹配。

### 任务 4.8 实现 llm_fallback 接口

- 创建：
  - `clients/llm_client.py`
- 完成标准：
  - 默认 mock；
  - 不直接生成最终内容。
- 测试：
  - mock 输出校验。

### 任务 4.9 生成 mapping_report

- 修改：
  - `mapping_service.py`
- 完成标准：
  - 生成报告并保存。
- 测试：
  - report summary 断言。

### 任务 4.10 人工复核 API

- 修改：
  - `review_service.py`
  - `reviews.py`
- 完成标准：
  - 可修改 mapping。
- 测试：
  - review 后 mapping status=confirmed。

## Phase 5：字段转换与 canonical model

### 任务 5.1 实现 rename

- 修改：
  - `transform_engine.py`
- 完成标准：
  - 源值写入目标字段。
- 测试：
  - rename 单测。

### 任务 5.2 实现 type_cast

- 修改：
  - `transform_engine.py`
- 完成标准：
  - string/int/float/bool/date。
- 测试：
  - 类型转换测试。

### 任务 5.3 实现 date_format

- 修改：
  - `transform_engine.py`
- 完成标准：
  - 中文日期转 ISO。
- 测试：
  - `2026年6月1日` → `2026-06-01`。

### 任务 5.4 实现 enum_map/default

- 修改：
  - `transform_engine.py`
- 完成标准：
  - 枚举映射和默认值填充。
- 测试：
  - enum 未命中 warning。

### 任务 5.5 实现 merge/split

- 修改：
  - `transform_engine.py`
- 完成标准：
  - 字段合并、拆分。
- 测试：
  - 合并标题、拆分机构字段。

### 任务 5.6 实现 trace_service

- 修改：
  - `trace_service.py`
- 完成标准：
  - 每个转换动作写 trace。
- 测试：
  - trace 数量和字段断言。

### 任务 5.7 实现 canonical_builder

- 修改：
  - `canonical_builder.py`
  - `canonical_service.py`
- 完成标准：
  - 生成 canonical model。
- 测试：
  - fields、blocks、source_blocks 完整。

## Phase 6：多形态渲染

### 任务 6.1 生成 content.json

- 修改：
  - `json_renderer.py`
- 完成标准：
  - 从 canonical 生成 JSON。
- 测试：
  - 与 expected_content.json 对比。

### 任务 6.2 生成 content.md

- 修改：
  - `markdown_renderer.py`
- 完成标准：
  - 包含 front matter、block_id 注释。
- 测试：
  - block_id 存在。

### 任务 6.3 生成 chunks.json

- 修改：
  - `chunk_engine.py`
  - `chunks_renderer.py`
- 完成标准：
  - 每个 chunk 有 source_blocks。
- 测试：
  - chunk 回链测试。

### 任务 6.4 统一 render_service

- 修改：
  - `render_service.py`
- 完成标准：
  - 一次调用生成三种输出。
- 测试：
  - 三文件都生成。

## Phase 7：成果包与一致性校验

### 任务 7.1 生成 validation_report

- 修改：
  - `schema_validator.py`
- 完成标准：
  - required/type/enum 校验。
- 测试：
  - 缺失必填字段定位。

### 任务 7.2 生成 consistency_report

- 修改：
  - `consistency_validator.py`
- 完成标准：
  - block_id、chunks、assets、manifest 检查。
- 测试：
  - 故意断链应报错。

### 任务 7.3 生成 manifest

- 修改：
  - `manifest_engine.py`
- 完成标准：
  - 所有文件有 sha256。
- 测试：
  - sha256 与实际一致。

### 任务 7.4 实现 package_service

- 修改：
  - `package_service.py`
- 完成标准：
  - 生成 standard_package.zip。
- 测试：
  - zip 内容检查。

### 任务 7.5 下载 API

- 修改：
  - `packages.py`
- 完成标准：
  - 可下载 zip。
- 测试：
  - API 返回 application/zip。

## Phase 8：前端最小页面

### 任务 8.1 初始化 React

- 创建：
  - `frontend/`
- 完成标准：
  - 页面可启动。
- 测试：
  - `npm run build`

### 任务 8.2 API client

- 创建：
  - `frontend/src/api/client.ts`
- 完成标准：
  - 封装 fetch。
- 测试：
  - 手工联调。

### 任务 8.3 任务列表页

- 创建：
  - `pages/TaskListPage.tsx`
- 完成标准：
  - 展示任务列表。

### 任务 8.4 UIR 导入页

- 创建：
  - `pages/ImportPage.tsx`
- 完成标准：
  - 上传 JSON。

### 任务 8.5 Schema 管理页

- 创建：
  - `pages/SchemaPage.tsx`
- 完成标准：
  - 上传 Schema。

### 任务 8.6 映射结果页

- 创建：
  - `pages/MappingPage.tsx`
- 完成标准：
  - 展示和修改 mapping。

### 任务 8.7 成果包下载页

- 创建：
  - `pages/PackagePage.tsx`
- 完成标准：
  - 下载 zip。

## Phase 9：测试与稳定化

### 任务 9.1 单元测试补齐

- 覆盖：
  - schema
  - candidate
  - mapping
  - transform
  - canonical
  - render
  - validators
  - package

### 任务 9.2 API 测试

- 覆盖所有 MVP API。
- 使用 `httpx.AsyncClient` 或 FastAPI TestClient。

### 任务 9.3 端到端测试

流程：

    导入 UIR
    → 创建 Schema
    → 创建 Template
    → 创建 Task
    → 生成 candidates
    → 执行 mapping
    → review
    → convert
    → package
    → 校验 zip

### 任务 9.4 badcase 样例

创建：

    examples/badcase_missing_required.json
    examples/badcase_type_error.json
    examples/badcase_mapping_ambiguous.json
    examples/badcase_broken_block_link.json

### 任务 9.5 异常路径修复

要求：

- 不崩溃；
- 返回统一错误；
- 写 trace；
- task 状态正确。

## Phase 10：验收强化与产品化基线

### 任务 10.1 真实模型 fallback

- 接入一个 OpenAI-compatible 或本地模型；
- 准备 3～5 个疑难字段案例；
- 记录模型、提示词、置信度、依据、耗时与人工确认结果；
- 保留 `disabled` 和 `mock` 模式。

### 任务 10.2 配置快照与任务重放

- 生成 `config_snapshot.json`；
- 实现 `parent_task_id` 与 replay API；
- 测试默认重放不重复请求模型。

### 任务 10.3 独立评测集

- 建立至少 30 份 UIR 样本或不少于 150 对金标字段映射；
- 覆盖通用文档、政策文档和至少一类简单表格记录；
- 划分开发集和评测集；
- 输出规则版与混合版对比报告。

### 任务 10.4 内容组织验收

- 文档级摘要、chunk 摘要、关键词、三级标签和上游实体标签写入；
- 增加摘要忠实度与标签准确率抽样评估。

### 任务 10.5 包外 verifier 与安全测试

- 修复 Manifest 自引用问题；
- 校验 ZIP 内路径、文件大小、哈希和额外文件；
- 增加路径穿越、恶意文件名、超大 JSON、危险正则等测试。

### 任务 10.6 企业交付文档

- 完成 API 与数据规范、成果包协议、部署手册、评测报告、badcase 报告和技术报告；
- 固化 OpenAPI JSON；
- 准备验收演示脚本和一键启动命令。

## 17. Codex 执行规范

Codex 开发时必须遵守：

1.  不要一次性生成过多文件；
2.  每次只完成一个小任务；
3.  每完成一个 service 后运行对应测试；
4.  每个 service 必须有测试；
5.  所有接口必须有 Pydantic 请求 / 响应模型；
6.  不要把业务逻辑写在 router 里；
7.  router 只负责参数接收、调用 service、返回响应；
8.  核心逻辑放在 services / engines / validators；
9.  不要让 LLM 直接生成最终成果；
10. 所有大模型调用封装在 `llm_client.py`；
11. LLM 输出必须结构化校验；
12. 外部智能体调用都放在 `adapters/`；
13. 成果包只能从 canonical model 渲染；
14. 不允许分别独立生成 content.json 和 content.md；
15. 所有转换动作必须写 trace；
16. 所有导出文件必须写入 manifest；
17. 所有文件路径必须走 `storage_service.py`；
18. 不要硬编码绝对路径；
19. 不要把密钥写入代码；
20. `.env.example` 只写示例值；
21. 每个模块要写最小单元测试；
22. 所有 JSON 文件读写使用 UTF-8；
23. 所有时间使用 ISO 8601；
24. 所有 ID 使用统一工具 `utils/ids.py`；
25. 每次修改后至少运行相关 pytest；
26. 不要引入大型依赖，除非当前阶段明确需要；
27. 不要实现 PDF / OCR / 清洗 / 归一等越界能力；
28. adapter 可以 mock，但接口要稳定；
29. 打包失败不能留下伪 completed 状态；
30. consistency critical error 必须阻止 package completed。

## 18. 测试方案

### 18.1 Pydantic schema 测试

输入：

- example UIR；
- example Target Schema；
- example Mapping Template。

断言：

- 能成功 parse；
- 缺少 required 字段时报错；
- 类型错误时报错。

### 18.2 UIR 导入测试

输入：

    examples/demo/example_uir_general_doc.json

断言：

- documents 表有记录；
- storage 中有 `uir.json`；
- block_count 正确。

### 18.3 Schema 校验测试

输入：

- 合法 schema；
- 缺少 fields 的非法 schema。

断言：

- 合法通过；
- 非法返回 `SCHEMA_INVALID`。

### 18.4 字段候选提取测试

输入：

    {
      "metadata": {
        "标题": "测试文档",
        "发布日期": "2026年6月1日"
      }
    }

断言：

- 生成候选 `标题`；
- 生成候选 `发布日期`；
- inferred_type 正确。

### 18.5 字段映射测试

断言：

- exact_match confidence=1；
- alias_match 能把 `文档标题` 映射到 `title`；
- regex_match 能提取日期；
- 低置信映射 need_review=true。

### 18.6 字段转换测试

断言：

- rename 正确；
- merge 正确；
- split 正确；
- date_format 正确；
- enum_map 正确；
- default 正确；
- 每个操作产生 trace。

### 18.7 canonical model 测试

断言：

- fields 完整；
- blocks 保留 block_id；
- source_blocks 不为空；
- assets 保留引用。

### 18.8 JSON 渲染测试

断言：

- `content.json` 存在；
- fields 值正确；
- blocks 数量正确；
- 通过 Target Schema。

### 18.9 Markdown 渲染测试

断言：

- 包含 front matter；
- 包含标题；
- 每个 block 包含 block_id 注释；
- Markdown 文本包含 canonical block 文本。

### 18.10 chunks 渲染测试

断言：

- chunks 非空；
- 每个 chunk 有 chunk_id；
- 每个 chunk 有 source_blocks；
- source_blocks 都存在于 canonical blocks。

### 18.11 trace 完整性测试

断言：

- mapping 有 trace；
- transform 有 trace；
- render 有 trace；
- package 有 trace；
- trace 中包含 before/after/reason/status。

### 18.12 consistency_report 测试

断言：

- 正常样例 passed=true；
- 删除一个 block_id 后 passed=false；
- 删除 asset 后出现 warning；
- 删除 required 文件后 critical error。

### 18.13 manifest sha256 测试

断言：

- manifest 中所有文件真实存在；
- sha256 与实际文件一致；
- bytes 与实际大小一致。

### 18.14 成果包 zip 测试

断言：

- zip 存在；
- 包含全部 required 文件；
- 可解压；
- 解压后 manifest 校验通过。

### 18.15 API 测试

覆盖：

- POST documents/import；
- POST schemas；
- POST templates；
- POST tasks；
- POST generate-candidates；
- POST map；
- POST convert；
- POST package；
- GET download。

断言：

- HTTP status 正确；
- response schema 正确；
- 错误响应统一。

### 18.16 端到端测试

测试函数：

    test_e2e_general_doc_conversion
    test_e2e_policy_doc_conversion

断言：

- 最终 completed；
- zip 生成；
- validation passed；
- consistency passed；
- manifest sha256 passed。

### 18.17 Target Schema 投影测试

断言：

- Target Schema 校验 `content.json.data`；
- 外层 `blocks`、`assets` 不影响业务 Schema 校验；
- Output Profile 导出的裸对象与 `data` 一致。

### 18.18 模型 fallback 集成测试

断言：

- 规则无法决定时才调用模型；
- 模型输出经过结构化校验；
- 非法 target field 被拒绝；
- 低置信结果进入人工复核；
- 模型关闭时主流程仍可运行。

### 18.19 可复现与重放测试

断言：

- 同一输入与配置的确定性阶段结果一致；
- `config_snapshot.json` 信息完整；
- replay 创建新 task 并保留 parent_task_id；
- 默认 replay 使用已确认映射，不重复调用模型。

### 18.20 安全测试

覆盖：

- 路径穿越文件名；
- ZIP 中 `../` 条目；
- 超大或过深 JSON；
- 越界 asset 路径；
- 危险正则超时；
- 非法下载路径。

### 18.21 下游 consumer 测试

- `business_consumer.py` 可读取 `content.json.data` 或 `exports/`；
- `rag_consumer.py` 可读取 `chunks.json` 并检查回链；
- 不依赖 SchemaPack Agent 内部数据库。

### 18.22 摘要与标签测试

- 文档级和 chunk 级摘要均存在；
- 管理标签按规则稳定生成；
- 质量标签与 validation/consistency 结果一致；
- 实体标签仅来自上游记录；
- 抽样检查摘要不引入原文外事实。

## 19. 示例数据设计

### 19.1 examples 目录

```text
examples/
├── demo/
│   ├── example_uir_general_doc.json
│   ├── example_uir_policy_doc.json
│   ├── target_schema_general.json
│   ├── target_schema_policy.json
│   ├── mapping_template_general.json
│   ├── mapping_template_policy.json
│   ├── expected_content.json
│   ├── expected_content.md
│   ├── expected_chunks.json
│   └── expected_manifest.json
├── eval/
│   ├── dataset.jsonl
│   ├── gold_mappings.jsonl
│   ├── split.json
│   └── README.md
├── badcases/
│   ├── missing_required.json
│   ├── type_error.json
│   ├── mapping_ambiguous.json
│   ├── broken_block_link.json
│   ├── unsafe_asset_path.json
│   └── malformed_model_output.json
└── consumers/
    ├── business_consumer.py
    └── rag_consumer.py
```

`demo/` 用于演示；`eval/` 用于独立量化评测；二者不得混用。

### 19.2 example_uir_general_doc.json

内容应包含：

- 普通文档标题；
- 作者；
- 创建日期；
- 2 个 heading；
- 3 个 paragraph；
- 1 个 list；
- block_id 连续；
- metadata 字段较规范。

用途：

- 测试普通字段映射；
- 测试 Markdown 渲染；
- 测试 chunks。

### 19.3 example_uir_policy_doc.json

内容应包含：

- 政策标题；
- 发布单位；
- 印发日期；
- 文号；
- 章节结构；
- 正文字段中包含 `发布日期：2026年6月1日`；
- 至少 1 个字段需要 regex_match；
- 至少 1 个字段需要 alias_match。

用途：

- 测试政策 Schema；
- 测试字段别名；
- 测试日期转换；
- 测试 mapping_report。

### 19.4 target_schema_general.json

字段：

    title
    author
    created_date
    language
    summary

约束：

- title required；
- created_date date；
- language default `zh-CN`。

### 19.5 target_schema_policy.json

字段：

    title
    publish_org
    publish_date
    doc_no
    doc_type
    main_content

约束：

- title required；
- publish_date date；
- doc_type enum: policy / notice / report。

### 19.6 mapping_template_general.json

包含：

- title aliases；
- author aliases；
- created_date aliases；
- default language；
- date_format。

### 19.7 mapping_template_policy.json

包含：

- 政策标题 aliases；
- 发布单位 aliases；
- 印发日期 regex；
- 文号 regex；
- doc_type enum_map；
- publish_date date_format。

### 19.8 expected_content.json

应包含：

- 标准 fields；
- blocks；
- source_blocks；
- assets 空数组或示例引用。

### 19.9 expected_content.md

应包含：

- front matter；
- block_id 注释；
- 标题层级；
- 正文。

### 19.10 expected_chunks.json

应包含：

- 至少 2 个 chunk；
- source_blocks；
- labels；
- summary；
- keywords。

### 19.11 expected_manifest.json

应包含：

- required files；
- path；
- media_type；
- sha256 可在测试中动态更新或只比对结构。

### 19.12 独立评测集设计

建议最低规模：

- UIR 文档不少于 30 份；
- 金标字段映射不少于 150 对；
- 至少包含 20 个疑难或冲突映射；
- 至少包含 10 个转换 badcase；
- 至少覆盖通用文档、政策/制度文档和简单二维表格三类形态。

评测集应记录样本来源、许可或自建方式、金标制作人、复核方式和版本。开发规则时只查看开发集，最终指标在冻结的评测集上运行。

## 20. 验收指标

### 20.1 字段映射准确率

核心指标采用 Precision、Recall 和 F1，而不是只用一个易受分母影响的“准确率”：

```text
Precision = 正确自动映射数 / 自动映射总数
Recall    = 正确自动映射数 / 金标映射总数
F1        = 2PR / (P + R)
```

验证方式：使用冻结的 `examples/eval/gold_mappings.jsonl` 自动计算，并分别报告规则版、规则 + 模型版和人工确认后的最终结果。

目标：

- 自动字段映射 F1 ≥ 0.85；
- 规则类映射准确率 ≥ 0.95；
- 必填字段未映射定位率 = 100%；
- 人工确认后的最终映射正确率目标 ≥ 0.98。

### 20.2 字段转换正确率

计算：

    字段转换正确率 = 转换结果与 expected fields 一致的字段数 / 需要转换字段数

目标：

    规则类转换 >= 95%

### 20.3 Schema 校验覆盖率

计算：

    Schema 校验覆盖率 = 已实现校验项 / Schema 中声明的约束项

至少覆盖：

- required；
- type；
- enum；
- pattern；
- min/max。

目标：

    >= 90%

### 20.4 必填字段缺失定位率

计算：

    定位率 = 能给出 field_id/path 的缺失错误数 / 必填缺失错误总数

目标：

    100%

### 20.5 content.json / content.md 一致性

计算：

    一致性 = Markdown 中可识别 block_id 数 / content.json blocks 数

并检查文本 hash。

目标：

    100%

### 20.6 chunks 回链完整率

计算：

    回链完整率 = source_blocks 全部存在的 chunk 数 / chunk 总数

目标：

    100%

### 20.7 trace 完整率

计算：

    trace 完整率 = 有 trace 的转换动作数 / 转换动作总数

目标：

    100%

### 20.8 manifest 完整率

计算：

    manifest 完整率 = manifest 记录文件数 / package 实际 required 文件数

目标：

    100%

### 20.9 sha256 校验通过率

计算：

    sha256 通过率 = sha256 匹配文件数 / manifest 文件数

目标：

    100%

### 20.10 成果包生成成功率

计算：

    成果包生成成功率 = 成功生成 zip 的任务数 / 总任务数

在示例数据上目标：

    100%

### 20.11 API 可用性

计算：

    API 可用性 = 测试通过接口数 / MVP 接口数

目标：

    100%

### 20.12 端到端处理成功率

计算：

    端到端成功率 = completed 任务数 / 测试任务总数

目标：

    examples 数据 100%
    badcase 数据能正确失败并报告

### 20.13 打标与摘要质量

- 内容标签准确率 ≥ 85%；
- 管理标签规则正确率 = 100%；
- 摘要忠实度抽样评估 ≥ 90%，不得出现明确臆造；
- 标准实体标签写入准确率以“是否忠实搬运上游实体 ID 和来源 block”为准，目标 100%。

### 20.14 智能体与大模型有效性

至少报告：

- 模型调用率；
- 模型 fallback 对映射 F1/自动覆盖率的提升；
- 人工复核率变化；
- 模型建议被人工接受、修改、拒绝的比例；
- 平均模型耗时和单任务成本。

验收要求：真实模型能处理至少一类规则难以覆盖的疑难映射，且所有输出受约束、可解释、可人工复核。

### 20.15 可复现与重放

- 配置快照完整率 = 100%；
- 同输入、同配置的规则和转换阶段结果一致率 = 100%；
- 任务重放成功率 = 100%；
- 重放过程不得丢失人工确认映射和来源血缘。

### 20.16 私有化与离线运行

- `OFFLINE_MODE=true` 时无外部网络依赖；
- 除模型 fallback 外，核心闭环功能可完整运行；
- 外部模型调用可关闭或替换为本地兼容服务；
- 运行日志不泄露密钥。

### 20.17 性能与资源基线

建议以真实开发环境测量并在报告中给出结果。最低建议目标：

- 10 MB 或 5,000 blocks 以内的 UIR 能稳定处理；
- 不调用外部模型时，1,000 blocks 的转换与封装在 30 秒内完成；
- 大文件处理不得一次性复制多份完整正文到内存；
- 同时执行 3 个普通任务时服务不崩溃，状态与文件互不串扰。

如硬件环境不同，可调整具体阈值，但必须给出可复现的 benchmark 脚本和机器配置。

### 20.18 下游可用性

- `business_consumer.py` 读取成功率 = 100%；
- `rag_consumer.py` 读取成功率 = 100%；
- 所有 required 文件与字段契约均通过独立 consumer 验证；
- 至少演示一次 JSON/JSONL/CSV 中的一种下游导出格式。

## 21. 风险与兜底方案

### 21.1 项目范围失控

风险：

- 想把解析、清洗、归一、质检、RAG 都做进来。

兜底：

- 严格以 UIR 为输入；
- adapters 只 mock；
- README 写清边界；
- 不引入 PDF/OCR 依赖。

### 21.2 误实现其他课题

风险：

- 实现复杂智能分段、实体链接、质量评分。

兜底：

- 分段只做 fallback；
- 质检只做结构一致性；
- 实体标签只接收上游结果，不生成标准实体。

### 21.3 数据结构设计反复变更

风险：

- UIR / Canonical / Package 模型频繁变化。

兜底：

- 先冻结 MVP schema；
- 所有模型加 version；
- examples 和 tests 作为契约。

### 21.4 字段映射准确率不高

风险：

- 异构字段名太多，规则覆盖不足。

兜底：

- 强化 Mapping Template；
- 加 aliases；
- 低置信进入人工复核；
- 人工修正可反哺模板。

### 21.5 LLM 输出不稳定

风险：

- LLM 幻觉、输出格式不稳定。

兜底：

- 默认关闭 LLM；
- mock 优先；
- LLM 只做 suggestion；
- Pydantic 校验；
- 低置信人工复核。

### 21.6 Schema 太复杂

风险：

- Target Schema 支持过深嵌套导致实现困难。

兜底：

- MVP 支持一层 fields；
- 嵌套字段作为后续扩展；
- 复杂 schema 转为 flat projection。

### 21.7 多形态输出不一致

风险：

- JSON、Markdown、chunks 不一致。

兜底：

- 统一从 canonical model 渲染；
- consistency_validator 强制校验；
- 不一致则不允许 package completed。

### 21.8 成果包生成失败

风险：

- 文件缺失、hash 错误、zip 失败。

兜底：

- 临时目录生成；
- 完成后原子移动；
- manifest 校验通过后再 zip；
- 失败保留错误 trace。

### 21.9 前后端联调困难

风险：

- API 响应不稳定。

兜底：

- 所有 API 使用 Pydantic response model；
- Swagger 自动文档；
- 前端先用 mock data；
- 后端 API 测试先行。

### 21.10 测试不足

风险：

- 只跑通 happy path。

兜底：

- examples + badcase；
- 每个 service 对应测试；
- e2e 必须检查 zip 和 manifest；
- CI 可后续补充。

### 21.11 时间不够

风险：前端、外部适配器、模型接入和文档工作拖慢进度。

兜底优先级：

```text
后端核心闭环
→ examples 与独立评测集
→ tests 与包 verifier
→ Swagger API
→ 真实模型 fallback
→ 最小前端
→ 外部 adapter / 高级导出
```

如果时间不足：

- 前端压缩为导入、映射复核、任务详情、成果下载 4 个核心页面；
- 外部 adapter 仅保留稳定接口和 mock；
- recordset、复杂 Output Profile、对象存储和权限系统延期；
- **不得取消真实模型 fallback、人工复核、配置快照、独立评测和成果包完整性验证**；
- 重点保证 `UIR → Mapping → Transform → Canonical → Render → Validate → Package → Verify` 全链路正确。

### 21.12 Manifest/报告循环依赖

风险：一致性报告检查 Manifest，而 Manifest 又要记录一致性报告的哈希，导致生成后相互失效。

兜底：严格按“两层校验 + 包外 verifier”流程实现，Manifest 排除自身，包内报告不再检查 Manifest 哈希。

### 21.13 安全输入与路径风险

风险：恶意路径、ZIP 条目、超大 JSON、危险正则或任意表达式造成文件越界、资源耗尽或代码执行。

兜底：StorageService 统一路径、上传限制、JSON 深度限制、正则超时、禁止任意表达式、非 root 容器和安全测试。

### 21.14 只有流程 Demo、缺少智能效果证据

风险：项目能生成 ZIP，但评委认为只是普通 ETL/格式转换工具，没有智能体价值。

兜底：展示规则未解决的疑难字段、模型候选与依据、人工复核、规则版与混合版指标对比，并解释为何模型只能提出建议而不能直接写最终成果。

### 21.15 评测集过小或数据泄漏

风险：只在两个 examples 上测出 100%，指标不可信。

兜底：演示集与评测集分离；建立至少 30 份 UIR、150 对金标映射的冻结评测集；记录数据版本和金标复核过程。

## 22. 最终输出要求

本项目最终应交付一个可运行、可测试、可部署的工程，而不是一次性脚本。

### 22.1 必须交付

**可运行软件：**

- FastAPI 后端服务；
- 最小前端；
- SQLite 数据库及初始化/迁移脚本；
- Docker Compose 与离线运行配置；
- 标准成果包生成、下载和 verifier；
- 真实模型 fallback、mock 和 disabled 三种模式；
- 示例数据、独立评测集、badcase 与 consumer 脚本；
- pytest 测试与覆盖率报告。

**工程与接口文档：**

- `README.md`；
- API 文档与冻结的 `openapi.json`；
- UIR、Target Schema、Mapping Template、Canonical Model 和成果包协议；
- 部署与使用说明；
- Schema/模板版本和兼容策略；
- 外部智能体适配接口说明。

**评测与验收材料：**

- 字段映射、字段转换、标签、摘要、一致性和下游可用性评测报告；
- 规则版与规则 + 模型版对比；
- badcase 分类和改进说明；
- 典型任务的 trace、配置快照和人工复核记录；
- 一份简要技术报告，说明方法选型、与通用 ETL/格式转换工具的差异、难点、指标、不足和后续计划。

### 22.2 最终运行命令

后端：

    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload

前端：

    cd frontend
    npm install
    npm run dev

测试：

    cd backend
    pytest

Docker：

    docker compose up --build

### 22.3 最终验收路径

1.  打开 Swagger；
2.  上传 `example_uir_policy_doc.json`；
3.  上传 `target_schema_policy.json`；
4.  上传 `mapping_template_policy.json`；
5.  创建转换任务；
6.  生成字段候选；
7.  执行字段映射；
8.  如有低置信字段，人工确认；
9.  执行转换；
10. 生成成果包；
11. 下载 `standard_package.zip`；
12. 解压检查：
    - `content.json`
    - `content.md`
    - `chunks.json`
    - `mapping_report.json`
    - `validation_report.json`
    - `consistency_report.json`
    - `trace.json`
    - `manifest.json`
13. 运行 pytest 端到端测试；
14. 确认 validation passed；
15. 确认 consistency passed；
16. 调用包外 verifier，确认 Manifest 文件大小与 SHA-256 全部通过，并记录 ZIP SHA-256。

### 22.3.1 验收演示建议

演示不只展示“成功样例”，建议按以下顺序：

1. 上传 UIR、Schema 和模板；
2. 展示规则自动映射；
3. 展示一个规则无法解决的疑难字段，触发真实模型 fallback；
4. 展示模型候选、置信度、依据和人工修改；
5. 执行确定性转换，展示 before/after trace；
6. 展示 `content.json.data` 通过 Target Schema；
7. 展示 Markdown、chunks、标签、摘要和原文回链；
8. 生成 ZIP，运行包外 verifier；
9. 使用独立 business/RAG consumer 读取成果；
10. 展示评测报告和 badcase，而不是只展示单次运行结果。

### 22.3.2 最终验收判定条件

以下条件全部满足才视为项目完成：

- 基础闭环和 badcase 路径均可复现；
- 真实模型 fallback 可演示，且失败时能安全降级到规则/人工；
- 字段映射 F1、规则转换正确率、标签/摘要和一致性指标达到约定值；
- `content.json.data` 通过 Target Schema；
- Manifest 无自引用，包外 verifier 通过；
- 任务 trace、配置快照和人工复核记录完整；
- 离线模式可运行；
- 独立 consumer 能读取业务数据和 chunks；
- 代码、文档、测试、评测报告、badcase 和部署材料齐全。

### 22.4 给 Codex 的实施总原则

优先实现这条主线：

    UIR → Schema → Mapping → Transform → Canonical → Render → Validate → Manifest → Zip

不要偏离为：

    原始文档解析
    清洗
    归一
    完整 RAG
    完整质检

本项目的创新点应集中在：

    Schema 驱动转换
    字段映射
    字段重组
    双形态输出
    成果包封装
    一致性校验
    转换留痕
    模板复用
    人工复核闭环


## 23. 产品化拓展路线图

### 23.1 P0：三周实训验收版

必须完成：

- document 模式；
- 规则映射 + 真实模型疑难 fallback + 人工复核；
- 基础字段转换；
- Canonical Model 单一事实源；
- JSON / Markdown / chunks；
- 三级标签、摘要、关键词和上游实体写入；
- Schema 校验、内容一致性校验、Manifest 与包外 verifier；
- trace、配置快照和任务重放；
- FastAPI、最小前端、Docker、测试和独立评测集。

### 23.2 P1：可交付产品增强

- Schema 和 Mapping Template 的草稿、发布、废弃与版本 diff；
- mapping dry-run、影响分析和批量人工复核；
- JSONL / CSV Output Profile；
- 简单 recordset 模式；
- PostgreSQL、Alembic、后台任务队列；
- Webhook、API Token、操作审计；
- 本地 embedding 或私有模型；
- 更完善的置信度校准和历史复核反哺模板。

### 23.3 P2：企业系统接入

- 对象存储和大文件流式处理；
- 多租户、角色权限和数据隔离；
- Schema Registry、模板审批和环境发布；
- Java/Python SDK；
- 与主控调度、课题 11 分段、课题 6/12 质检服务真实集成；
- 指标监控、告警、调用成本和 SLA；
- 数据保留、删除、备份与灾难恢复策略。

### 23.4 建议突出展示的创新点

1. **Schema 驱动且受约束的智能字段映射**：规则优先，模型只处理疑难并给出证据；
2. **Canonical Model 单一事实源**：解决多形态成果容易不一致的问题；
3. **双形态 + RAG 组织 + 下游 Profile**：同一成果同时服务业务系统、人读和大模型；
4. **可追溯与可重放**：字段级 before/after、配置快照、人工复核和任务血缘；
5. **无循环依赖的可验证成果包协议**：内容一致性、Manifest 和包外 verifier 分层；
6. **评测闭环**：规则版与混合版对比、独立金标、badcase 和下游 consumer 验证；
7. **私有化可替换模型**：外部模型可关闭，本地规则和人工流程仍可完整工作。

## 24. 最终开发优先级

```text
P0-1 数据契约：UIR / Target Schema / Mapping Template / Canonical / content.data
P0-2 核心算法：候选提取 / 规则映射 / 转换 / trace
P0-3 智能能力：真实模型 fallback / 置信度 / 人工复核
P0-4 成果组织：JSON / Markdown / chunks / 摘要 / 标签 / 实体回链
P0-5 可信交付：validation / consistency / manifest / verifier / snapshot / replay
P0-6 工程交付：API / 最小前端 / Docker / 文档
P0-7 证据链：独立评测 / 对比实验 / badcase / consumer smoke test
```

在 P0 全部完成之前，不进入复杂表格、完整 RAG、完整质检、分布式调度或多租户权限建设。
