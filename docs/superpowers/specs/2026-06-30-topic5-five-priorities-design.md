# SchemaPack Agent 五优先级深化设计

> **Historical specification:** Preserved for design rationale. Current status: [`../../project_status.md`](../../project_status.md).

## 目标

在保持现有
`UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`
生产链路和 UIR 输入边界不变的前提下，连续落实
《课题 5 下一步推进实施指导文档：五个优先级工程化落地方案》的全部内容：

1. 提高非采购类文档的严格验证通过率和真实字段映射召回率。
2. 将真实 UIR 数据集从 16 份扩展到至少 30 份，并补齐可追溯的 gold 数据。
3. 为 chunk 策略、摘要忠实度和标签质量建立可量化评测。
4. 用 before/after 报告证明人审知识包对后续任务的能力增益。
5. 用结构化 CSV、RAG JSONL 和消费方合同校验证明成果包可被下游读取。

全部工作在一个连续执行周期内完成，不设置人工阶段门禁。实现仍按依赖顺序推进，
每项能力完成后运行局部质量检查，最后执行统一验收。

## 当前基线与缺口

2026-06-30 的干净基线为：

- 后端测试 203 个通过。
- Ruff 无问题。
- 前端 production build 成功。
- OpenAPI 导出和一致性检查通过，共 32 条路径。
- 真实 UIR 共 16 份，全部可 import、execute 和 package verify。
- `procurement_doc` 严格验证 5/5。
- `general_doc`、`meeting_doc`、`policy_doc` 严格验证分别为 0/3、0/3、0/5。
- 真实映射召回率为 0.42592592592592593。
- badcase violation 为 0，LLM fallback 自动接受数为 0。

仓库已经具备真实映射、采购对比、内容检索和真实知识闭环的第一代评测，但指导文档
要求的以下深化交付尚不存在：

- 非采购差距分析和专项评测。
- 30 份以上真实 UIR 及其 inventory。
- 内容策略对比、摘要忠实度和标签质量专项评测。
- 知识能力成长曲线 fixture 与报告。
- CSV、RAG corpus 和下游消费合同工具。

## 方案选择

采用“依赖顺序连续推进 + 共享评测基础设施 + 单职责 CLI”的方案。

实施顺序仍为 Phase A 到 Phase G，但这些阶段只用于依赖管理和验证，不作为暂停点：

1. 冻结基线并生成非采购失败差距报告。
2. 强化非采购 Schema、Template、Mapping 和 badcase。
3. 扩展真实 UIR 数据集与 gold 数据。
4. 增加内容组织质量评测。
5. 增加知识能力成长曲线评测。
6. 增加下游消费适配器与合同验证。
7. 更新前端证据展示、文档和统一验收材料。

未采用按五个优先级各自复制一套评测基础设施的方案，因为会重复 HTTP、JSONL、
报告和指标逻辑。也不采用先集中写完生产代码再补测试的方式，因为无法证明新增测试
能够捕获缺失行为。

## 架构与组件边界

### 共享评测能力

优先复用 `scripts/eval_support.py`、现有服务层和现有 package contract。只有两个以上
新增 CLI 共同需要的纯函数、文件读取、指标或报告能力才进入共享模块。共享能力负责：

- UTF-8 JSON/JSONL 的严格读取与写入。
- 安全除法、按文档类型聚合、字段覆盖和失败分类。
- 可复现的 JSON/Markdown 双格式报告。
- package 目录与 ZIP 的只读访问。
- 单文档失败结构化和基础设施失败快速退出。

各 CLI 只负责参数解析、流程编排和固定输出路径，不复制生产服务逻辑。

### 非采购差距分析与增强

`scripts/analyze_real_world_validation_gaps.py` 读取已有真实运行、映射和验证产物，
按 `doc_type` 聚合缺失必填字段、复核字段、低置信来源和风险建议，不重新执行全流程。

`general_doc`、`meeting_doc`、`policy_doc` 继续使用稳定主 Schema 与 Template，
通过真实语义驱动的字段、alias、regex、enum、transform 和 candidate extraction
增强映射。只在字段天然不适用于全部 subtype 时使用 conditional 或 optional；
不会整体放宽 required，也不会自动接受高风险 fuzzy 结果。

`scripts/eval_non_procurement_doc.py` 对三类非采购样本输出总体、按类型和逐文档指标，
包括 strict pass、required coverage、mapping recall、review-required、badcase 和
package verification。

### 真实 UIR 数据集

数据集从 16 份扩展到至少 30 份。新来源只选择公开官方 HTML 或文本层 PDF，优先补充
字段较稳定的 `policy_doc` 和 `procurement_doc`，再补充 `meeting_doc` 和
`general_doc`。生产 runtime 仍只接收 UIR，不增加 OCR 或原始文档解析服务。

`source_manifest.json` 为每个来源保留 URL、发布机构、文档类型、采集时间、许可说明、
内容哈希、构建状态和失败原因。每份 UIR 保留稳定的 source block、层级、表格和来源
引用。同步补充 mapping gold、badcase 和 retrieval query。

`scripts/build_real_world_dataset_inventory.py` 只读扫描 manifest、UIR 与 gold，
输出覆盖度、来源完整性、文档类型分布、字段密度、gold 覆盖和数据质量问题。

### 内容组织质量评测

新增 `content_organization_gold.jsonl`，以人工标注的 source block、标题路径、摘要事实
和期望标签作为评测依据。

- `eval_content_strategy_comparison.py` 比较现有五种 chunk 策略的覆盖、完整性、
  冗余、表格保护、source-link coverage 和检索指标。
- `eval_summary_faithfulness.py` 使用确定性规则检查摘要中的实体、数字、日期和关键事实
  是否可由来源支持；无法可靠判断的项目明确标记为需人审，不调用模型伪造结论。
- `eval_content_tag_quality.py` 分别计算 content、management、quality 标签的
  precision、recall、F1 和逐标签失败案例。

前端只读取固定报告并展示关键指标、对比和失败样本，不重构现有工作台。

### 人审知识能力成长曲线

新增 review fixture，明确每个 review 决策的 approve/reject、候选规则、目标字段、
风险和预期状态。

`eval_review_knowledge_growth.py` 在隔离数据库和存储中执行：

1. 运行 before 任务并保存完整快照。
2. 应用人审决定并生成 knowledge candidate。
3. 验证 rejected/blocked candidate 不可进入 active pack。
4. 创建 draft pack，验证未激活前不影响 effective template。
5. 激活合规 pack，对同类新任务执行 after。
6. 比较 mapping recall、strict pass、review-required 和字段级变化。
7. 重新读取 before 任务，逐字段证明旧快照不变。
8. 运行 badcase，证明高风险错误映射未被自动接受。

报告同时包含能力提升和安全不变量，不将被拒绝候选或 LLM 建议自动激活。

### 下游消费证明

`export_structured_csv.py` 从 package 目录或 ZIP 读取 canonical/content、metadata 和
mapping evidence，默认导出适合异构 Schema 入库的 long CSV；可选 wide 模式只在字段
能够稳定展开时使用。

`export_rag_corpus.py` 将 `chunks.jsonl` 转换为带 package、task、document、Schema、
Template、标题路径、来源、标签、粒度和 parent ID 的 JSONL。它只生成 corpus，
不实现向量数据库或在线 RAG。

`verify_downstream_contract.py` 从消费方视角校验 required artifacts、manifest hash、
metadata 标识、非空 Markdown、可序列化 chunks、CSV 导出和 RAG 导出。它补充而不替代
现有 package verifier。

## 数据流与失败处理

新增评测统一遵循：

```text
fixture/gold/report/package
  -> strict reader
  -> pure metric or production-service orchestration
  -> per-item structured result
  -> aggregate JSON
  -> Markdown rendering
```

合法输入中的单文档映射、验证或 package 失败写入结果并继续，以便保留完整分布。
以下情况直接返回非零退出码：

- 输入文件缺失、JSON/JSONL 无法解析或结构不合法。
- gold 引用了不存在的文档、Schema、Template、字段或 source block。
- API 无法连接、鉴权失败或隔离评测环境无法初始化。
- package 无法打开、required artifact 缺失或 manifest hash 不一致。
- 报告或导出目标不可写。

所有阈值未达成情况都如实写入报告和最终交付说明，不删除失败样本、不修改 gold 来
迎合实现，也不隐藏 warning。

## 测试策略

所有新增生产行为严格按 red-green-refactor 实施：

1. 先写一个描述目标行为的最小失败测试。
2. 运行测试并确认其因功能缺失而失败。
3. 写最小实现使测试通过。
4. 运行相关测试，确认新增和既有行为均为绿色。
5. 只在绿色状态下整理重复代码。

测试至少覆盖：

- 差距分析聚合、建议分类和双格式报告。
- 三类非采购 Schema/Template 合法性、真实 alias/regex/transform 和 badcase。
- 非采购专项评测的 strict、mapping、review 和 package 指标。
- manifest、UIR、gold、badcase、retrieval query 和 inventory 的交叉引用。
- 五种 chunk 策略、summary 事实检查和三类标签指标。
- approve/reject、draft/active、before/after、旧快照和 badcase 不变量。
- ZIP/目录的 CSV 和 RAG 导出、粒度过滤、缺失来源、空 chunks、缺失 artifact 和
  hash mismatch。
- 前端报告解析和展示组件的纯函数行为。

涉及 HTTP 的评测使用唯一临时 SQLite 数据库和 storage root，避免历史状态污染。

## 验收与不可回退项

最终必须同时满足：

- `verify_all.py --check-openapi` 通过，完整 pytest、Ruff 和前端 build 通过。
- 采购严格验证保持 5/5。
- 第一阶段至少达到：general 2/3、meeting 2/3、policy 3/5、mapping recall 0.65。
- 继续推进第二阶段目标：general 3/3、meeting 3/3、policy 4/5、mapping recall 0.75；
  若真实语义不支持，报告必须说明阻碍，不得放宽安全门槛。
- package verification 对扩展后的全部数据通过，badcase violation 为 0。
- LLM fallback 保持 review-only，`auto_accepted_count = 0`。
- 数据集至少 30 份且 manifest、UIR 与 gold 交叉引用完整。
- 内容策略、摘要忠实度和标签质量均有 JSON/Markdown 报告。
- knowledge growth 报告证明 after 优于 before、旧快照不变、reject 不生效。
- CSV、RAG corpus 和 downstream contract verification 可运行。
- OpenAPI 仅在 API 确有变化时重新导出并解释差异。
- README 和交付文档准确声明边界，不声称支持 runtime OCR、任意原始文档解析、
  完整 RAG、模型训练或 LLM 自动学习生产规则。

## 文档与前端收尾

更新 README、数据集、知识闭环、demo、API 示例、需求映射、最终交接和必要的 package
说明。前端按现有组件结构增加报告入口和证据展示，不把逻辑堆回 `App.tsx`。

所有报告路径和运行命令写入文档。最终汇报只陈述由测试和报告证明的能力，对未达到的
第二阶段目标保留明确限制和后续建议。
