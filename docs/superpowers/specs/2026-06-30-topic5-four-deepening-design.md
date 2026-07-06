# SchemaPack Agent 四项深化设计

> **Historical specification:** Preserved for design rationale. Current status: [`../../project_status.md`](../../交接/project_status.md).

## 目标

在保持现有
`UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`
主链路和 UIR 生产输入边界不变的前提下，把真实 UIR 数据集扩展为可复现、可比较、
可审计的能力评测集。交付覆盖四个方向：

1. 真实 UIR 字段映射金标与专项评测。
2. `procurement_doc` 专用 Schema、Template 及相对 `general_doc` 的收益评测。
3. 五种内容组织策略的轻量检索评测。
4. 真实 UIR 人审与知识包闭环评测。

每个方向必须具备可运行脚本、JSON/Markdown 报告和自动化测试。

## 仓库现状与实施判断

仓库已有 16 份真实 UIR：5 份政策、5 份采购、3 份会议和 3 份通用文档。使用全新
SQLite 数据库和独立存储目录运行现有 HTTP 评测时，16 份文档均能导入、执行和通过
package verifier，并产生 69 个复核项。

现有基础能力包括：

- Target Schema、Mapping Template 文件加载和 catalog 治理。
- `fixed_window`、`heading_aware`、`source_block_aware`、`table_protect`、
  `parent_child` 五种内容组织策略。
- review、knowledge candidate、draft/active knowledge pack 和 effective template。
- 任务执行快照、mapping/validation/chunks/verifier 报告和 package 下载 API。

指导文档要求的两份 gold 数据、采购 Schema/Template、四个专项脚本、四组报告和对应
测试目前均不存在。采购 UIR 在现有评测中仍明确映射到
`general_doc/general_doc_base_v1`。因此本次工作以补充数据、配置、专项评测和回归
证据为主，不重构已有服务。

## 方案选择

采用“专项脚本 + 共享评测工具”方案：

- 保留 `scripts/eval_real_world_uir.py` 的已有行为。
- 新增四个职责单一的专项 CLI。
- 将 HTTP 调用、JSONL 校验、指标计算和双格式报告的通用逻辑放入共享评测模块。
- 指标计算保持为纯函数，脚本编排与度量逻辑分离，以便单元测试。

未采用把全部能力合并进现有真实 UIR 评测脚本的方案，因为会形成难维护的巨型脚本。
也不引入通用评测框架、向量数据库或完整 RAG，以免超出课程项目范围。

## 目录与组件

### 评测数据

`examples/real_world/gold/mapping_gold.jsonl` 覆盖全部 16 份真实 UIR。每份文档至少
标注三个映射字段，并记录应进入复核的歧义项和禁止自动接受的 badcase。四类文档
均至少包含一个 badcase；采购文档覆盖金额、日期、采购人、代理机构和供应商字段。

`examples/real_world/gold/retrieval_queries.jsonl` 至少包含 32 条查询，每份真实 UIR
至少两条、每类文档至少六条。采购查询覆盖项目名称、预算金额、采购人、中标供应商
和截止日期。相关 source block、标题路径和关键词只用于命中判定，不参与结果排序。

### 共享评测模块

共享模块负责：

- 读取并严格校验 JSON/JSONL。
- 根据 doc_type 定位真实 UIR 和 catalog 配置。
- 封装 documents、tasks、reports、package、reviews 和 knowledge HTTP API。
- 计算安全除法、Recall@k、MRR、nDCG@5、字段覆盖和 badcase 违规数。
- 原子写入 UTF-8 JSON 和 Markdown 报告。
- 将单文档失败转换为结构化结果，同时让格式或配置错误快速失败。

共享模块不保存 API key，不解析原始 PDF/DOCX/HTML，也不实现在线向量检索。

### 真实映射评测

`scripts/eval_real_world_mapping.py` 对每个 gold 文档执行：

1. 导入 UIR。
2. 使用 gold 指定的 Schema/Template 创建并执行任务。
3. 拉取 mapping、validation 和 verifier 报告并读取 package。
4. 将 accepted、review_required、unmapped 与 gold 对齐。
5. 统计 precision、recall、required coverage、review rate、badcase 和 package 指标。

报告包含总体、按文档类型、按文档、按目标字段的结果，以及缺失字段、歧义证据、
badcase 违规、package 验证和后续建议。单个文档失败不会中断其他文档，但会降低相应
通过率并出现在失败明细中。

### 采购领域扩展

新增：

- `examples/production_like/schemas/procurement_doc_v1.json`
- `examples/production_like/mapping_templates/procurement_doc_base_v1.json`

Schema 遵循现有 `TargetSchema` JSON 结构，必填字段仅设为 `title`、
`project_name` 和 `purchaser`。其他采购编号、采购方式、代理机构、预算金额、
中标供应商、中标金额、公告日期、截止日期、开标日期、联系人、来源和摘要字段保持
可选，以免真实公告格式差异导致普遍验证失败。

Template 使用现有 alias、regex、enum map、default 和 transform 能力支持的子集。
日期、金额和相似机构角色的歧义保持复核，不通过高置信规则强行接受。现有
`SchemaService`、`TemplateService` 和 `CatalogGovernanceService.seed_from_files`
会自动发现并激活新文件，不新增平行 catalog。

`scripts/eval_procurement_doc.py` 对同一批五份采购 UIR 分别以 `general_doc` 和
`procurement_doc` 执行，比较必填覆盖、gold recall、正确自动接受、复核项、缺失
必填、badcase 和 package 通过率。现有 `eval_real_world_uir.py` 的采购映射在采购
catalog 验证通过后改为专用 Schema/Template。

### 内容组织检索评测

`scripts/eval_content_organization_retrieval.py` 对每份文档按五种已有策略创建任务并
读取 chunks。检索使用零外部依赖的确定性关键词评分：

- 查询与 chunk 正文的 token/子串重合。
- 查询与 `title_path` 的重合加分。
- 查询与 chunk `keywords` 的重合加分。

gold source block ID、标题路径和答案关键词只用于判断返回结果是否相关，绝不进入
排序分数。parent-child 策略分别记录 child、parent 和 all 粒度结果。

报告输出 Recall@1/3/5、MRR、nDCG@5、answerable rate、平均 chunk 数、平均 token
估算、表格拆分违规和 source-link coverage，并保留逐查询失败案例。若结构化策略
没有优于 fixed window，报告如实记录结果并给出金标、检索器或分段策略的改进建议。

### 人审与知识包闭环

`scripts/eval_knowledge_loop_real_world.py` 在独立评测数据库中执行：

1. 运行带有 review_required 或缺失映射的真实 UIR。
2. 从 gold 中选择至少三个可批准的 alias 候选。
3. 通过 review API 批准并创建 knowledge candidates。
4. 接受候选并创建 draft pack。
5. 在激活前验证 effective template 和新任务不受 draft pack 影响。
6. 激活 pack，对同类新任务重新执行并比较映射指标。
7. 再次读取旧任务快照并逐字段比较，确认其保持不变。
8. 执行 known badcase 检查，确认知识包未使禁止映射自动 accepted。

只有 active pack 可以影响新任务。blocked candidate 不能被接受，draft/pending pack
不能进入 effective template。

## 报告与退出行为

固定生成：

- `reports/real_world_mapping_eval_report.{json,md}`
- `reports/procurement_doc_eval_report.{json,md}`
- `reports/content_organization_retrieval_eval.{json,md}`
- `reports/knowledge_loop_eval_report.{json,md}`

合法数据中的个别 HTTP、任务或 package 失败写入报告并继续评测。以下情况直接返回
非零退出码：

- gold 文件缺失、JSONL 无法解析或引用不存在的文档。
- gold 引用不存在的 Schema/Template 或目标字段。
- API 无法连接或鉴权失败。
- 报告目标路径不可写。

报告不伪造指标。推荐阈值未达成时，JSON 保留实际值，Markdown 同时列出失败原因和
下一步建议。

## 测试策略

实施严格遵循测试优先：

- 先写一个描述所需行为的失败测试并确认失败原因。
- 写最小实现使该测试通过。
- 保持相关测试为绿色后再进入下一行为。

测试分为四组：

1. Gold 数据测试：文件存在、每行可解析、16 份文档、每份至少三个映射、四类覆盖、
   badcase 覆盖、至少 32 条查询和采购关键查询覆盖。
2. 采购 catalog 测试：Schema/Template 可加载，字段和 alias 合法，所有 template
   target 均存在，catalog seed/activation/archival 与现有治理兼容。
3. 检索评测测试：空 chunks、相关性判定、Recall@k、MRR、nDCG、报告生成及 gold
   source block 不参与排序。
4. 知识闭环测试：draft 不生效、active 影响新任务、旧快照不变、badcase candidate
   被阻断。

真实 HTTP 验证必须使用唯一的临时 SQLite 数据库和存储目录，显式设置
`DATABASE_URL` 与 `STORAGE_ROOT`，避免默认相对路径或历史数据库表结构污染结果。

最终验证命令包括：

- 后端完整 pytest。
- Ruff。
- 前端生产构建。
- `scripts/verify_all.py --check-openapi`。
- 四个专项 HTTP 评测及其 JSON/Markdown 报告。

## 文档更新

更新 `README.md`、`docs/real_world_uir_dataset.md`、
`docs/交接/requirement_mapping.md`、`docs/交接/final_demo_script.md` 和
`docs/交接/final_handoff_status.md`，说明四项能力、运行命令、报告路径、真实指标和已知
限制。前端可选增强不在本次范围内。

## 验收标准

- 真实映射评测覆盖 16 份 UIR，package pass rate 为 1.0，badcase 违规数为 0。
- 采购专用 catalog 可加载、激活并被任务使用，且相对 general catalog 的真实结果
  在报告中可比较。
- 五种内容组织策略均可执行，source-link coverage 接近 1.0，结构化策略提升与否均
  有真实证据。
- 至少三个真实复核项走完 approve、candidate、pack、active 和 rerun。
- 旧任务快照保持不变，active 后 badcase 违规数为 0。
- LLM fallback 继续默认关闭，LLM 生成内容不得自动接受或激活。
- 现有主链路、package verifier、测试、lint 和前端构建不回归。
