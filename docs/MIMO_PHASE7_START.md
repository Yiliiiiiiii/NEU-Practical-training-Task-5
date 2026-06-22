# Mimo Code Phase 7 启动任务

> 只执行 Phase 7：成果包与一致性校验。完成后停止，等待 Codex 验收。禁止开始 Phase 8 或 Phase 10 的独立外部 verifier。

## 1. 基线与分支

开始前确认当前 `HEAD` 包含：

- `58ce284`：Mimo Phase 6 功能提交；
- `5d122e8`：Codex Phase 6 验收补充修正；
- 最新版 `README.md`、`docs/MIMO_CODE_HANDOFF.md` 和本启动文档。

先运行并记录：

```powershell
git status --short
git branch --show-current
git log -8 --oneline --decorate
git merge-base --is-ancestor 5d122e8 HEAD
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..
git switch -c phase7-package-validation
```

预期基线为 `108 passed` 且 Ruff 全部通过。工作区不干净、缺少基线提交或基线失败时立即停止并报告。

## 2. 先计划，后改代码

使用 UTF-8 完整阅读：

1. `SchemaPack_Agent_项目实施文档_修订版.md`；
2. `docs/MIMO_CODE_HANDOFF.md`；
3. Phase 7 任务 7.1 至 7.5；
4. 成果包结构、Manifest、内容一致性、API 16 至 21；
5. 测试方案 18.12 至 18.15、样例与验收清单；
6. 现有 package/report schema、数据库记录、StorageService、TraceService、RenderService 和 tasks router。

在修改任何生产代码前，必须在 `docs/superpowers/plans/` 创建 Phase 7 实施计划。计划必须列出每个小任务的准确文件、先失败的测试、最小实现、验证命令、提交边界和完成标准。先提交计划，再开始 TDD。不得在实现完成后补写一份事后计划。

## 3. 不可改变的生成顺序

严格按下列顺序执行，防止 Manifest 和 consistency 循环依赖：

1. 确认同一 task 的 `content.json`、`content.md`、`chunks.json` 已存在且任务状态允许打包；
2. 生成 `metadata.json`、最小可复现的 `config_snapshot.json`、mapping report、validation report 和 trace；
3. 对内容文件运行 consistency validator，生成 `consistency_report.json`；
4. consistency 存在 critical error 时停止，不生成 completed package；
5. 对除 `manifest.json` 自身外的全部 payload 文件生成 `manifest.json`；
6. 在临时 staging 目录构建 ZIP，并对 Manifest 条目和 ZIP 内真实 payload 做内部复核；
7. 原子发布 `standard_package.zip`，保存 ZIP SHA-256，最后才设置 package/task 成功状态。

`consistency_report.json` **不得读取或校验 `manifest.json`**。Manifest 不列出自身，ZIP 哈希不写入包内，只保存在数据库和下载响应头中。独立包外 verifier 属于 Phase 10。

## 4. Phase 7 实现范围

### 4.1 Validation Report

在 `validators/` 实现确定性的 Schema validator，由 service 负责读取、持久化和导出。校验对象是 `content.json.data`，至少覆盖：

- required 缺失；
- string、integer、number、boolean、date、array、object 等当前 Target Schema 已支持类型；
- enum；
- minimum/maximum 或规格中等价 range；
- pattern；
- issue 的 level、code、message、field_id 和 JSON path；
- summary 中 error/warning/check 数量与 `passed` 一致。

写入：

```text
tasks/{task_id}/validation_report.json
validation_reports 数据库记录
```

同一 task 重复执行必须有明确的覆盖或版本策略，不能无限制造互相冲突的“当前报告”。

### 4.2 Consistency Report

在 `validators/` 实现内容一致性 validator，至少检查：

- Content JSON 与 Markdown 的 block 顺序、block_id、source_blocks 和文本/hash 对应；
- chunks 的 `source_blocks` 全部可回链 canonical/content blocks；
- chunk 文本顺序与来源 block 一致，关键内容不丢失；
- asset 引用可解析，必需 asset 缺失为 critical，可选 asset 缺失按规格记 warning；
- validation、mapping、trace 等报告结构可解析且 task/schema 引用一致；
- critical errors、warnings 和 checks 的汇总与 `passed` 一致。

写入：

```text
tasks/{task_id}/consistency_report.json
consistency_reports 数据库记录
```

一致性校验不得检查 Manifest、ZIP SHA 或 ZIP 内容。

### 4.3 Manifest

在 `engines/manifest_engine.py` 或与现有结构一致的位置实现纯文件清单逻辑。每个 `ManifestFile` 必须来自 staging 中真实文件，记录：

```text
path
required
media_type
sha256
bytes
role
```

强制约束：

- path 是 `/` 分隔的规范化相对路径；拒绝绝对路径、盘符、`..` 和路径逃逸；
- files 按 path 稳定排序；
- SHA-256 为完整 64 位十六进制；
- bytes 是真实字节数，不是字符数；
- `manifest.json` 和 ZIP 本身不得进入 files；
- 生成后重新读取 Manifest 并逐项核对真实 payload；
- 不用固定 expected hash 掩盖文件内容变化，expected fixture 只固定协议和可确定内容。

### 4.4 Package Service

创建 package service 编排 validation、consistency、Manifest、ZIP、数据库和状态。标准 ZIP 至少包含：

```text
manifest.json
metadata.json
config_snapshot.json
content.json
content.md
chunks.json
mapping_report.json
validation_report.json
consistency_report.json
trace.json
assets/                 # 有资源时
exports/                # 可选
```

`config_snapshot.json` 在本阶段生成可验证的最小完整版本，至少固化 input hash、schema/template ID 与版本、task options、程序版本，以及当前实际使用的模型/提示词版本；未使用模型时写明确的本地/禁用状态，不伪造调用。Phase 10 再扩展重放和独立 verifier 能力。

Package service 必须：

- 复用 StorageService 的路径安全规则，不硬编码绝对路径；
- 使用 Python `zipfile` 或项目已有标准库，不引入无必要大型依赖；
- 使用 task/package 专属临时 staging 路径；
- 所有门禁通过后再原子移动到最终位置；
- 持久化 `OutputPackageRecord` 和每个 `PackageFileRecord`；
- 计算并保存最终 ZIP SHA-256；
- 重复请求采用明确、可测试的幂等或版本化策略；
- 任一步失败时记录结构化 package trace，状态为 failed，不暴露部分 ZIP；
- 只有全部文件、内部 Manifest 复核和 ZIP 成功后才设置 package/task completed。

最终路径应由 service 返回，不允许 Router 拼接。路径遵循现有 storage 布局并在计划中明确。

### 4.5 API

实现并测试：

```text
POST /api/v1/tasks/{task_id}/package
GET  /api/v1/tasks/{task_id}/package/download
GET  /api/v1/tasks/{task_id}/reports/validation
GET  /api/v1/tasks/{task_id}/reports/consistency
GET  /api/v1/tasks/{task_id}/trace
```

要求：

- POST 请求支持 `package_version`，响应至少包含 package_id、status 和 zip_path；
- download 返回 `application/zip`，文件名为 `standard_package.zip`，并提供数据库中保存的 ZIP SHA-256 响应头；
- 未找到 task/package/report 返回明确 404；状态不允许、critical 校验失败或包尚未完成返回明确 409/422；
- 所有请求和 JSON 响应使用 Pydantic 模型；下载使用 FastAPI 文件响应；
- Router 只做依赖注入、service 调用、响应和异常映射，不查询多张表或编排打包步骤。

## 5. 强制 TDD 与真实链路测试

每项先写失败测试并确认失败原因，再写最小实现。至少覆盖：

1. general demo 从 UIR 导入开始，经真实 schema/template/task/mapping/convert/package API，下载并解压 ZIP，逐项校验必需文件和 Manifest。
2. policy demo 走同样真实链路，验证日期/enum/正文/assets 在包内保持一致。
3. validation required、type、enum、range、pattern 各有命中与不命中测试，issue path 指向 `data`。
4. 故意断开 chunk `source_blocks` 回链，consistency 产生 critical error 并阻止 completed package。
5. asset 必需缺失和可选缺失分别验证 error/warning 语义。
6. Manifest 排序、media type、bytes 和 SHA-256 与 staging 真实字节逐项一致，且不包含自身或 ZIP。
7. ZIP entry 不含绝对路径、盘符、反斜杠逃逸或 `..`；解压目标不能越界。
8. 注入 validation/consistency/Manifest/ZIP 写入失败，验证 failed 状态、错误 trace、数据库副作用和无可下载最终 ZIP。
9. 对已完成包损坏一个 payload，内部复核或 badcase validator 必须拒绝，不得只比较文件名。
10. 重复 package 请求验证既定幂等/版本策略，不能产生冲突的 completed 记录。
11. 五个 API 都通过 TestClient 发送真实请求，验证状态码、响应 schema、Content-Type、文件名和 SHA 响应头。
12. 下游 smoke test 直接消费解压后的 `content.json.data` 和 `chunks.json`，证明协议可用。

禁止用测试函数名、OpenAPI 路由存在、手工 SQL seed 或 mock service 代替上述真实行为。局部单元测试可以 mock，但至少两条 demo 链路必须经过真实 service、数据库、storage 和 API。

## 6. 禁止事项

- 不实现 Phase 8 前端。
- 不实现真实 LLM fallback。
- 不实现 Phase 10 的独立包外 verifier、签名、重放 API 或完整产品化配置中心。
- 不让 consistency validator 读取 Manifest。
- 不把 `manifest.json` 自身或 ZIP 放进 Manifest files。
- 不在临时 ZIP 尚未复核时写 completed。
- 不用 `tempfile` 外部绝对路径绕过 StorageService 的安全边界；临时目录必须可控并在失败后清理。
- 不把运行时 package、数据库、临时目录或测试产物提交到 Git。
- 不修改 Phase 6 已验收输出协议，除非发现有证据的阻塞性契约问题；先报告再做有回归测试的最小修正。

## 7. 完成门禁

先运行 Phase 7 定向测试，再运行：

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..
git diff --check
git status --short
```

还必须执行一次独立于 pytest 断言的手工验收：通过 API 生成包、下载 ZIP、列出 ZIP entries、解压到临时目录、重新计算每个 Manifest payload 的 bytes/SHA-256，并确认无不安全路径。报告真实结果和最终相对路径。

Phase 完成后更新 README 的实现状态、API 列表和剩余边界，提交清晰的功能/测试/文档 commit，保持工作区干净。

## 8. 完成报告附加内容

按 `docs/MIMO_CODE_HANDOFF.md` 的固定格式报告，并额外列出：

- validation 与 consistency 的全部 check/code；
- 标准 ZIP 的真实相对路径和完整 entries；
- Manifest 是否排除自身、条目数量、排序策略和实测 hash 校验结果；
- task/package 的成功、critical 失败和 I/O 失败状态证据；
- general/policy 两条真实 API 链路测试名称及其关键断言；
- 失败注入位置和“无部分 ZIP”证据；
- 五个 API 的真实请求/响应证据；
- 实施计划 commit、功能 commit 和最终 commit SHA；
- 所有偏差、遗留和未覆盖路径，不得无证据写“无”。

最后输出：

```text
PHASE 7 READY FOR CODEX ACCEPTANCE
```

然后停止，不得开始 Phase 8。
