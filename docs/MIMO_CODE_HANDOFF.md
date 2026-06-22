# SchemaPack Agent - Mimo Code 总交接与执行约束

> 本文档的直接执行对象是 Mimo Code。你是后续阶段的代码执行者，不是产品规格制定者，也不是最终验收者。
>
> 项目分工：Mimo Code 负责逐 Phase 实现；Codex 负责项目总控、规格校准、代码审查与验收；用户拥有最终决策权。

## 1. 开始前必须执行

在修改任何文件前，按顺序完成以下事项：

1. 使用 UTF-8 **完整阅读**仓库根目录的 `SchemaPack_Agent_项目实施文档_修订版.md`。
2. 重点理解文档中的总体流程、目录结构、数据模型、API、映射与转换、canonical model、渲染、成果包、一致性校验、测试方案，以及第 17 节执行规范。
3. 阅读 `README.md`、`backend/pyproject.toml`、现有 `backend/app/` 和 `backend/tests/`。
4. 阅读已完成阶段的计划：`docs/superpowers/plans/`。
5. 运行并记录当前 Git 状态和测试基线。

PowerShell 基线命令：

```powershell
git status --short
git branch --show-current
git log -5 --oneline --decorate
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

当前已验收功能基线：

- 已完成并验收 Phase 0 至 Phase 6。
- Phase 5 的 Codex 验收补充修正为 `08082cf`。
- Phase 6 的 Mimo 功能提交为 `58ce284`，Codex 验收补充修正为 `5d122e8`。
- 当前功能分支为 `phase6-multiformat-rendering`。
- Phase 6 验收基线为 `108 passed`，Ruff 全部通过。
- `main` 尚不包含后续阶段提交。**不得从旧的 `main` 开始 Phase 7。**
- Phase 7 必须从包含 `5d122e8` 以及本交接文档最新修改的 `HEAD` 创建分支。

如果基线测试失败、工作区存在来源不明的修改、当前提交不包含 `5d122e8`，立即停止并报告，不要猜测或覆盖文件。

## 2. 下一项唯一任务

下一步只执行：

```text
Phase 7：成果包与一致性校验
```

建议分支：

```powershell
git switch -c phase7-package-validation
```

Phase 7 完成并汇报后必须停止。未经用户或 Codex 验收通过，不得开始 Phase 8。

后续阶段依次为：

1. Phase 7：成果包与一致性校验
2. Phase 8：前端最小页面
3. Phase 9：测试与稳定化
4. Phase 10：验收强化与产品化基线

不得跨 Phase 提前实现功能。例如 Phase 7 不实现前端、真实模型接入或 Phase 10 的独立外部 verifier。

## 3. 规格优先级

发生冲突时按以下顺序处理：

1. 用户在当前会话中的明确要求。
2. Codex 验收反馈和修正要求。
3. 本交接文档中的过程与安全约束。
4. `SchemaPack_Agent_项目实施文档_修订版.md` 中的产品和技术规格。
5. 当前 Phase 的实施计划。
6. 现有代码模式和 README。

发现规格之间矛盾、字段类型不一致、API 路径冲突或无法确定的业务含义时，停止并列出冲突证据。不要静默选择一种解释。

## 4. 每个 Phase 的固定工作流

每个 Phase 都必须执行以下闭环：

1. 阅读实施文档中该 Phase 的全部任务，并搜索相关详细章节，不得只读 Phase 清单。
2. 检查现有模型、数据库、service、engine、router 和测试，遵循已有架构。
3. 在 `docs/superpowers/plans/` 创建该 Phase 的实施计划，列出准确文件、测试、命令和完成标准。
4. 一次只实现一个小任务。不要一次生成整个 Phase 的所有代码。
5. 使用测试驱动开发：先写失败测试，确认失败原因正确，再写最小实现，再确认通过。
6. 每完成一个 engine 或 service，立即运行对应单元测试。
7. 每完成一个 API，运行对应 API 测试，并检查请求/响应模型。
8. 每个独立任务形成小而清晰的提交；禁止把无关重构混入功能提交。
9. Phase 结束时更新 README 的实现状态、API 列表和明确限制。
10. 运行完整验收门禁，检查 Git 差异，然后提交 Phase 最终状态。
11. 输出规定格式的 Phase 总结并停止，等待 Codex 验收。

### 4.1 Phase 5 返修经验与新增强制规则

Phase 5 首次实现虽然全量测试通过，但真实 demo 数据流仍失败。根因是测试使用了“源字段名等于目标字段名”和“手工构造但上游不会产生的候选”，因此验证了理想输入，没有验证真实阶段契约。后续必须遵守：

1. 测试不能只验证当前函数。每个新 consumer 至少有一个测试使用真实 upstream producer 的输出。
2. 手工 fixture 只能补充边界，不能替代 `producer -> persistence -> consumer` 契约测试。
3. 使用手工中间对象前，先证明前序 engine/service 在真实 demo 上确实会产生该对象及字段。
4. 每个 Phase 至少运行一个仓库 demo 的完整阶段链路，不得只运行隔离单元测试。
5. 报告“无偏差”前必须逐项对照详细设计章节、Phase 清单和测试方案，而不是只看测试数量。
6. 状态字段只能由真正完成该状态语义的阶段更新；禁止提前写 `rendered`、`completed` 等成功状态。
7. 对溯源字段必须验证真实来源，包括 `source_candidates`、`source_blocks`、`block_id` 和 hash，不能只断言字段存在。
8. 错误路径必须同时验证返回值、trace、持久化副作用和 task 状态，不能只断言抛异常。
9. Codex 验收会增加报告之外的反例。实现不得只针对列出的测试名称硬编码。

### 4.2 Phase 6 验收经验与新增强制规则

Phase 6 的报告声称真实 API 链路、写入失败和“无偏差”均已覆盖，但验收发现测试名称与测试行为不一致：所谓真实链路直接操作 SQL 和 engine，没有请求 API；所谓写入失败只测试了 canonical 缺失；单个超长 block 不会被切分；`render_outputs=false` 仍返回 `rendered`；GET canonical 丢失持久化字段；Router 内含业务编排；README 和阶段计划也未按要求更新。后续必须遵守：

1. 测试名称、完成报告和实际测试体必须逐项一致。报告中的每项证据都要能定位到真实断言和被测边界。
2. “API 已实现”必须用 TestClient 或等价客户端发送真实请求并检查状态码、响应模型和持久化副作用；仅检查 OpenAPI 路由存在不算 API 行为测试。
3. “写入失败”必须在目标写入边界注入故障，验证 task 状态、数据库事务、trace 和最终文件；不能用前置对象缺失替代 I/O 失败。
4. 布尔选项、状态分支和可选输出必须覆盖每个分支。例如 `render_outputs=true/false` 都要验证状态和响应。
5. 小 `chunk_size` 下多个短 block 能产生多个 chunk，不代表单个超长 block 可切分；边界测试必须精确构造触发条件并验证文本无丢失。
6. “真实链路”必须经过对应 service、持久化和 API 边界。直接调用 engine 或手工写 SQL 只能作为局部测试。
7. Router 内不得自行查询多张表、更新状态或编排多个 service；这些逻辑必须有独立 service 和单元测试。
8. README、阶段计划和交接文档属于完成标准。未创建或未更新时必须在“偏差与遗留”中如实报告，不能写“无偏差”。
9. Codex 会阅读测试体而不是按测试数量或名称验收。后续报告必须附上每个高风险行为对应的断言摘要。

## 5. 强制工程约束

### 5.1 架构边界

- Router 只负责接收参数、调用 service、转换响应和映射明确异常。
- 业务流程放在 `services/`。
- 纯规则和算法放在 `engines/` 或 `validators/`。
- 所有 API 都必须使用明确的 Pydantic 请求/响应模型。
- 所有数据库访问通过 SQLAlchemy 模型和 session，不使用临时 SQL 字符串拼接。
- 所有文件读写通过 `StorageService`，使用 UTF-8，不硬编码绝对路径。
- 所有 ID 使用 `backend/app/utils/ids.py` 的统一工具。
- 所有时间使用 ISO 8601。
- 成果内容只能从 canonical model 渲染，不能让 JSON、Markdown、chunks 各自独立生成业务内容。
- 每个映射和转换动作必须可以追溯；Phase 5 起转换动作写入 trace。
- LLM 不能直接生成 canonical model、最终内容或成果包。
- 所有模型调用必须封装在 `llm_client.py`，并经过结构化模型校验。
- 外部智能体调用放在 `adapters/`。
- 不实现 PDF、OCR、清洗、归一化等项目边界外能力。

### 5.2 修改纪律

- 先读后改，优先复用项目已有模式。
- 只修改当前任务必需文件，不顺手重构无关模块。
- 不覆盖、不回退用户或其他执行者留下的修改。
- 禁止使用 `git reset --hard`、强制 checkout、强制 push 或未经批准的删除命令。
- 不更改已验收 API 行为，除非当前 Phase 明确要求且有回归测试。
- 不引入大型依赖，除非实施文档或当前 Phase 明确需要。
- 不提交密钥、真实凭据、运行时数据库、缓存、构建产物或临时文件。
- 不用占位实现冒充完成：禁止空 `pass`、无依据的硬编码成功结果、未调用的伪接口和只为测试通过的分支。
- 中文文件必须以 UTF-8 读写，提交前检查是否出现乱码。

### 5.3 数据与状态约束

- Task 状态必须与真实执行结果一致。
- 失败不能留下伪 `completed` 状态。
- 打包阶段出现 critical consistency error 时必须阻止 package completed。
- 保存数据库或文件前先完成模型校验。
- 重复执行同一阶段时必须明确覆盖、幂等或版本化策略，并用测试证明。
- 不得用 LLM 输出覆盖高优先级规则结果，除非人工确认。

## 6. 测试与质量门禁

### 6.1 开发过程

每个行为至少包含：

1. 正常路径测试。
2. 关键边界或错误路径测试。
3. 与前序 Phase 契约有关的回归测试。

先运行最小测试：

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests\对应测试文件.py -q
```

确认失败原因是功能尚未实现，而不是导入错误、测试拼写错误或环境问题。

### 6.2 每个后端 Phase 的最终门禁

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..
git diff --check
git status --short
```

必须报告实际测试数量、失败数量和 Ruff 输出。不能使用“应该通过”“看起来正常”等表述代替命令证据。

### 6.3 已验收的 Phase 6 渲染契约

- `content.json`、`content.md`、`chunks.json` 必须从同一个已持久化 CanonicalModel 生成。
- 至少一个集成测试必须通过 Phase 5 的真实服务构建 canonical 后再调用 render service；只手工构造 CanonicalModel 不足以验收。
- 使用 general 和 policy demo 验证业务字段、block 顺序、assets、`block_id`、`source_blocks` 和 `text_hash`。
- chunks 必须覆盖 chunk_size 边界、稳定 chunk_id、heading 上下文、跨 block 分段和回链。
- 一次 render 调用必须生成三份文件；任一写入失败不得把 task 标记为 `rendered`。
- `POST /api/v1/tasks/{task_id}/convert` 和 `GET /api/v1/tasks/{task_id}/canonical` 必须有 Pydantic 请求/响应模型及 API 测试。
- API 集成测试必须从真实文档、Schema、Template、Task、mapping/canonical 数据开始，不得绕过前置状态门禁。

### 6.4 Phase 8 前端额外门禁

- 使用 React + TypeScript；若初始化工具未在规格中固定，优先选择简单、稳定的 Vite 配置。
- 第一屏必须是可使用的业务应用，不做营销落地页。
- 使用真实后端 API，不用永久假数据掩盖接口缺失。
- 任务列表、导入、Schema、映射复核和成果包下载形成可操作流程。
- 必须验证桌面和移动布局无文本溢出、遮挡或不可操作控件。
- 运行项目实际提供的 lint、test、build 命令，并报告完整结果。
- 启动本地服务后验证主要页面和关键交互；有浏览器工具时保存验收截图。

### 6.5 Phase 7 成果包额外门禁

- `validation_report.json` 只校验 `content.json.data` 与 Target Schema 的 required、type、enum、range 和 pattern 契约。
- `consistency_report.json` 校验内容、block、chunk、asset 和报告结构，但不得校验 Manifest，避免循环依赖。
- `manifest.json` 覆盖除自身外的全部 payload 文件；条目按规范化相对路径稳定排序，记录真实 bytes、完整 SHA-256、media type、required 和 role。
- ZIP 必须在临时目录完成并通过内部检查后原子发布；失败不得留下可下载的部分包或伪 `completed` 状态。
- ZIP 内容、路径、SHA-256、Manifest 和 consistency 结果必须通过真实文件测试，不得只 mock 中间结果。
- 必须包含 required/type/enum 错误、断裂 chunk 回链、损坏 payload、写入/打包失败等 badcase，并证明流程拒绝 critical error。
- 端到端测试必须从 UIR 导入开始，经真实 API/服务生成输出，最终下载、解压并逐文件校验成果包。
- Phase 10 的独立包外 verifier 尚不在本阶段范围；Phase 7 仍须在发布 ZIP 前执行内部 Manifest 与 payload 校验。

### 6.6 Phase 9 稳定化额外门禁

- 必须重跑所有后端与前端门禁，并覆盖并发、重试、幂等、损坏输入和历史回归。
- 必须包含至少一个故意损坏的成果包，并证明验证器或稳定化检查能拒绝它。

## 7. Git 约束

- 每个 Phase 使用独立分支。
- 新分支从最近一次 Codex 验收通过的提交创建。
- 提交信息使用清晰的英文 Conventional Commit，例如：

```text
feat: add transform engine operations
feat: build canonical document model
test: cover transform failure paths
docs: update phase 5 implementation status
```

- 提交前先检查 `git diff --check` 和 `git status --short`。
- 不合并、不 rebase、不删除分支、不推送远端，除非用户明确要求。
- Phase 完成时工作区必须干净；若有未提交文件，解释每一个文件的原因。

## 8. 当前已知边界

- Phase 4 的 LLM 仅有 mock seam；真实 fallback 属于 Phase 10.1。
- `enable_llm_fallback` 不能被解释为允许模型直接写最终内容。
- Transform 和 canonical 已通过 Phase 5 验收；Content JSON、Markdown、chunks、conversion service 和渲染 API 已通过 Phase 6 验收。
- Validation、consistency、Manifest、ZIP 和下载 API 尚未实现，属于 Phase 7；frontend 尚未实现，属于 Phase 8。
- Phase 6 未在实现前创建要求的阶段计划，且完成报告错误声明“无偏差”。这是已记录的过程偏差，不补写事后计划；Phase 7 必须先提交真实计划再修改生产代码。
- 任务创建阶段目前记录 Schema/Template 引用，映射执行时才加载对应记录；不要在无规格和无测试的情况下改变这一行为。
- 运行环境为 Windows PowerShell，后端虚拟环境位于 `backend/.venv`。
- 本地 FastAPI 通常运行在 `http://127.0.0.1:8000`；启动新服务前先检查端口占用。

## 9. Phase 完成汇报格式

完成一个 Phase 后，必须使用以下结构汇报，随后停止工作：

```markdown
# Phase N 完成报告

## 完成范围
- 按实施文档逐项列出任务 N.1、N.2……的完成状态。

## 主要修改
- 按 engine、service、router、schema、database、test、docs 分类列出。
- 对新增或改变的 API 写出 method、path、请求和响应要点。
- 对新增持久化文件写出相对路径和格式。

## 关键设计决定
- 写明选择、理由、与实施文档的对应章节。
- 写明所有假设。

## 测试证据
- 相关测试命令与结果。
- 全量 pytest 的通过数量和耗时。
- Ruff、前端 lint/test/build、git diff --check 的真实结果。
- 必要的手工或浏览器验证结果。

## Git 状态
- 分支名。
- 提交列表和最终 commit SHA。
- `git status --short` 是否为空。

## 偏差与遗留
- 与实施文档不一致的地方；没有则写“无”。
- 已知限制、风险、未覆盖路径；没有则写“无”。

## 验收提示
- 建议 Codex 优先检查的高风险文件、行为和测试。

PHASE N READY FOR CODEX ACCEPTANCE
```

不得只说“已完成”或只贴测试通过截图。验收者需要能从报告快速定位规格、代码、测试和风险。

## 10. Codex 验收流程

Mimo 提交报告后停止。用户会让 Codex 执行以下工作：

1. 对照实施文档逐项检查 Phase 覆盖。
2. 审阅 Git diff、提交边界、架构和数据契约。
3. 重新运行相关测试、全量测试、lint 和必要的端到端验证。
4. 检查异常路径、状态转换、幂等性、持久化和安全风险。
5. 给出“通过”“限项通过”或“需修正”的验收结论。

若 Codex 要求修正，Mimo 只修正明确反馈，补充回归测试，重新运行完整门禁，再提交新的报告。未经通过，不开始下一 Phase。

## 11. 给 Mimo 的最终提醒

你的优势是长上下文，因此要充分阅读规格和现有代码；不要用长上下文一次性生成大量未经验证的代码。你的首要目标不是速度，而是让每个小步骤可证明、可追溯、可验收。

现在从完整阅读 `SchemaPack_Agent_项目实施文档_修订版.md` 和 `docs/MIMO_PHASE7_START.md` 开始，然后只制定并执行 Phase 7 计划。
