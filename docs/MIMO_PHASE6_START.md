# Mimo Code Phase 6 启动任务

> 只执行 Phase 6：多形态渲染。完成后停止，等待 Codex 验收。禁止开始 Phase 7。

## 1. 基线与分支

开始前确认当前 `HEAD` 包含：

- `c2552bb`：Mimo Phase 5 返修；
- `08082cf`：Codex Phase 5 验收补充修正；
- 最新版 `docs/MIMO_CODE_HANDOFF.md`。

先运行：

```powershell
git status --short
git log -5 --oneline --decorate
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..
git switch -c phase6-multiformat-rendering
```

工作区不干净、缺少基线提交或基线测试失败时停止并报告。

## 2. 必读规格

完整阅读 `SchemaPack_Agent_项目实施文档_修订版.md`，重点核对：

- Phase 6 任务 6.1 至 6.4；
- 7.10 Content JSON、7.11 Content Markdown、7.12 Chunks JSON；
- 12.2 至 12.10 Canonical Model 与多形态渲染；
- API 14 `POST /api/v1/tasks/{task_id}/convert`；
- API 15 `GET /api/v1/tasks/{task_id}/canonical`；
- 测试方案 18.8 至 18.11；
- 样例说明 19.8 至 19.10；
- 第 17 节执行规范。

然后在 `docs/superpowers/plans/` 创建 Phase 6 实施计划。计划完成自查后才能修改生产代码。

## 3. 允许的 Phase 6 范围

### 3.1 Content JSON

创建专用 Pydantic 输出模型和 JSON renderer。主协议至少包含：

```text
content_version = "1.1"
doc_id
task_id
schema_ref = {schema_id, version}
metadata
data
blocks
assets
```

约束：

- `data` 只投影 `canonical.fields[*].value`；
- `metadata` 来自 canonical.doc_meta 和确定性的摘要/关键词 fallback；
- blocks/assets 只能来自同一个 canonical；
- 保留 `block_id`、`source_blocks`、`text_hash` 和 asset 引用；
- 不把 Target Schema 业务字段混入稳定外层协议；
- 创建并使用可版本化的 expected JSON fixture，不用只断言几个键存在。

### 3.2 Content Markdown

Markdown renderer 必须包含：

- YAML front matter：doc_id、task_id、schema_id；
- 从 canonical 标准字段选择标题，找不到时使用明确 fallback；
- 每个 block 前的 `block_id/source_blocks` HTML 注释；
- heading 层级、paragraph 文本；
- asset Markdown 占位符；
- 与 canonical block 顺序和文本一致。

创建 expected Markdown fixture，并验证所有 canonical block 都有对应注释和文本。

### 3.3 Chunks JSON

创建 `chunk_engine.py` 和 chunks renderer。输出至少包含：

```text
chunks_version = "1.0"
doc_id
task_id
chunks[]
```

每个 chunk 至少包含：

```text
chunk_id
order
text
source_blocks
title_path
labels
summary
keywords
text_hash
```

约束：

- 按 canonical block 顺序累积；
- `chunk_size` 从 task options 或显式参数读取，必须有稳定默认值；
- chunk_id 使用稳定规则 `chk_{task_id}_{order}`；
- heading 作为后续正文的上下文和 title_path；
- chunk 切分不能丢文本或重排 block；
- source_blocks 去重且都能回链 canonical.blocks；
- text_hash 使用完整 SHA-256 表达，不截断为不可验证的短标识；
- summary/keywords 使用确定性本地 fallback，不调用真实 LLM；
- labels 至少给出结构稳定的 content/management/quality 三类容器，不伪造尚未执行的 validation/consistency 通过状态。

### 3.4 Render Service 与 API

创建统一 render service，一次调用从同一个已持久化 canonical 生成：

```text
tasks/{task_id}/content.json
tasks/{task_id}/content.md
tasks/{task_id}/chunks.json
```

实现：

```text
POST /api/v1/tasks/{task_id}/convert
GET  /api/v1/tasks/{task_id}/canonical
```

API 必须使用 Pydantic 请求/响应模型。`POST /convert` 请求支持：

```json
{"render_outputs": true}
```

成功响应至少包含：

```json
{
  "task_id": "...",
  "status": "rendered",
  "outputs": ["content.json", "content.md", "chunks.json"]
}
```

状态约束：

- 只有三份输出全部成功写入后才能设置 `rendered`；
- canonical 不存在、任务状态不允许、输出写入失败时不得设置 `rendered`；
- 不重新实现 Phase 5 transform；convert service 复用 CanonicalService 和 RenderService；
- 重复 convert 必须有明确幂等策略，测试证明不会产生不一致内容；
- Router 只做参数、service 调用、响应和明确异常映射。

## 4. 强制真实链路测试

手工 CanonicalModel 单元测试只能作为补充。至少新增以下测试：

1. general demo 经真实 document/schema/template/task/candidate/mapping/canonical service 后生成三种输出。
2. policy demo 经同样真实链路生成输出，验证日期、enum、正文 merge 和 assets 引用。
3. content.json 与 expected fixture 对比，并验证 data 来自 canonical fields。
4. content.md 与 expected fixture 关键结构对比，每个 block 有注释和文本。
5. chunks 在小 chunk_size 下产生至少两个 chunk，文本无丢失、source_blocks 全部可回链。
6. 相同 canonical 和 options 重复渲染，输出内容与 chunk_id 稳定。
7. 任一 storage 写入失败时 task 不得变成 rendered。
8. canonical 不存在时 POST convert 返回明确 404/409，而不是 500。
9. GET canonical 返回持久化模型并符合响应模型。
10. API OpenAPI 中存在两个新路由，method 和 response schema 正确。

真实链路测试不得手工创建上游不会产生的 candidate、mapping 或 canonical。确需手工对象时，在测试注释中说明它对应哪个真实 producer 契约，并另有真实链路测试兜底。

## 5. 禁止事项

- 不实现 validation_report、consistency_report、manifest、ZIP 或下载 API；这些属于 Phase 7。
- 不创建前端。
- 不接入真实 LLM。
- 不修改 Phase 5 已验收语义，除非 Phase 6 发现真实契约问题；发现后先报告，不能静默重写。
- 不以测试数量代替规格覆盖，不在报告中无证据写“无偏差”。

## 6. 完成门禁

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..
git diff --check
git status --short
```

启动 FastAPI 后还要实际调用两个新 API，并检查生成文件内容。完成后提交清晰的 Phase 6 commit，工作区保持干净。

按 `docs/MIMO_CODE_HANDOFF.md` 输出完成报告，并额外列出：

- 三种输出的真实相对路径；
- general/policy 两条真实链路测试名称；
- task 状态变化证据；
- 幂等与写入失败测试；
- 所有偏差和未实现内容。

最后输出：

```text
PHASE 6 READY FOR CODEX ACCEPTANCE
```

然后停止，不得开始 Phase 7。
