# 课题 5 能力实现矩阵

本矩阵说明每项能力采用何种实现、适用输入、性能与成本特征，以及确定性规则或 LLM 的使用边界。运行时主边界是标准 UIR 或 External UIR JSON 到经校验的 SchemaPack 成果包；原始 PDF、Word、Excel、图片、扫描件与 OCR 不属于默认生产运行时。

| 能力 | 实现类型 | 适用输入/数据形态 | 性能与成本特征 | 规则或 LLM 选择 | 私有化部署行为 |
| --- | --- | --- | --- | --- | --- |
| UIR 与 External UIR 接入 | 确定性 Pydantic 校验与 block-list/section-tree adapter | 标准 UIR JSON、两类 External UIR JSON | 线性遍历；无模型调用成本 | 结构转换与字段校验可精确定义，不需要 LLM | 完全本地运行，无外部服务依赖 |
| SchemaPack 配置加载 | 确定性 manifest、路径约束、Schema/模板快照 | 注册或 inline SchemaPack | 文件读取与哈希校验；成本稳定 | 契约、版本和路径安全必须确定性执行 | 本地文件或私有仓库即可部署 |
| 字段候选抽取 | 确定性 metadata、key-value、table、block 抽取 | UIR metadata 与结构化 blocks | 与字段/块数量近似线性 | 来源位置和证据可追溯，规则足够 | 完全本地运行 |
| 字段映射 | exact、alias、regex、evidence-ranked、type、fuzzy 规则及受控全局分配 | 候选字段、目标 Schema、映射模板 | 主要为字符串比较和受限候选排序；无需推理费用 | 高置信自动映射必须由可复现规则支持 | 完全本地运行；结果包含 confidence、evidence、risk flags |
| 歧义映射建议 | 可选 LLM fallback，默认关闭且仅生成复核建议 | 无确定性映射的低置信歧义候选 | 有启用时才产生模型延迟/调用成本；受超时、重试和单任务建议数限制 | LLM 仅用于语义歧义建议；置信度上限 0.65，始终 `review_required`，不自动接受 | 可使用离线 stub 验证；私有 OpenAI-compatible 服务需显式配置，密钥不写入报告 |
| 字段变换 | 确定性 rename、merge、split 与类型/枚举变换 | 已确认映射与 transform rules | 与字段数量近似线性 | 操作语义可精确定义，禁止 LLM 改写 | 完全本地运行 |
| Canonical 与 Schema 校验 | JSON Schema/Pydantic 确定性校验 | canonical JSON、目标 Schema | 结构校验成本稳定 | 合规判定必须可复现，不使用 LLM-as-Judge | 完全本地运行 |
| 内容组织与分段 | heading-aware 等确定性策略，保护 table/list/code，建立父子关系与 source links | UIR blocks、内容组织配置 | 与块数和文本长度近似线性 | 边界、来源和保护规则需要稳定复现 | 完全本地运行 |
| 内容/管理/质量标签 | 配置化 tag rules；内容语义以多标签 Jaccard accuracy 独立评估 | chunks、SchemaPack tag 配置 | 规则匹配成本低且可审计 | 当前公开标签集可由规则覆盖；LLM 不参与自动标签门禁 | 完全本地运行，可由新增 SchemaPack 扩展 |
| 摘要与关键词 | 来源约束的确定性提取/组织 | UIR 文本块与 source blocks | 本地文本处理，无推理费用 | 当前要求强调来源覆盖与不新增事实，规则更易验证 | 完全本地运行 |
| 成果渲染与封装 | 确定性 JSON/JSONL/Markdown 渲染、manifest、checksum、ZIP 原子写入 | canonical、chunks、报告与快照 | 与成果大小近似线性；压缩与哈希为主要成本 | 格式与完整性属于机器契约，不需要 LLM | 完全本地运行；失败时不保留部分包 |
| 成果验证与下游契约 | checksum 重算、包验证、RAG/training/CSV consumer contracts | Package 1.1 成果包 | 读取全包并哈希，成本与包大小线性相关 | 接受/拒绝必须确定性判定 | 完全本地运行 |
| Review/Knowledge 治理 | 审批记录、badcase、draft/active/archived knowledge pack、影响预览与回滚 | 人工复核决策与知识候选 | 数据库/文件操作；不产生模型费用 | 人工审批是生产规则变更的唯一入口；LLM/Codex 输出不得自动激活 | 可在私有环境保存审计与版本历史 |
| Lineage 与审计 | field/block/chunk/artifact 边、审计日志、secret redaction | 转换任务与成果包 | 随证据边数量线性增长 | 可追溯性必须确定性记录 | 完全本地保存；敏感配置只输出脱敏快照 |
| 评测与回归门禁 | 冻结数据哈希、dev/test、replay、runtime equivalence、性能/并发/故障评测 | 公开冻结样本与精确提交 | 全量测试与性能评测成本最高；无网络是默认路径 | 定量结论来自评估器，不由 LLM 主观评分 | 可在离线 CI 复现；外部 blind 未运行，不宣称生产盲测 0.85 |

## 选择原则

1. 能由结构契约、配置、规则或可重复算法确定的能力，一律采用确定性实现。
2. LLM 只补充规则无法可靠决定的语义歧义，并且只能输出人工复核建议。
3. 新 Schema/模板/标签优先通过 SchemaPack 配置扩展，不通过 LLM 自动写入或激活生产规则。
4. 性能证据仅代表记录主机，不外推为生产环境绝对 SLO。
