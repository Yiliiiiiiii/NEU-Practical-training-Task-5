# SchemaPack Agent Web Workflow Runbook

本文档说明如何在网页端完成：

`导入 -> 映射 -> DeepSeek fallback -> 人工确认 -> 转换 -> 打包 -> verifier`

适用环境：Windows + PowerShell，项目目录默认 `F:\p2`。

## 1. 启动前检查

先确认后端已配置 DeepSeek：

```text
F:\p2\backend\.env
```

关键配置应为：

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
OFFLINE_MODE=false
```

只修改 `LLM_API_KEY`，不要把真实 key 写入文档或提交到 git。

启动后端：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动前端：

```powershell
cd F:\p2\frontend
npm run dev
```

打开网页：

```text
http://127.0.0.1:5173
```

## 2. 导入并创建任务

1. 打开左侧 `Import / Setup`。
2. 点击 `Load policy demo` 或 `Load general demo`。
3. 确认 `UIR Document`、`Target Schema`、`Mapping Template` 三个编辑区都是合法 JSON。
4. 点击 `Create task`。
5. 成功后页面会显示类似 `Task task_xxx`，并自动把当前任务带入后续页面。

建议优先使用 `Load policy demo` 做验收，因为它覆盖日期、正文块、报告和打包链路更完整。

## 3. 生成候选并运行映射

1. 打开左侧 `Mapping / Review`。
2. 确认 `Task ID` 已填入当前任务；如果为空，粘贴 task_id 后点击 `Use task`。
3. 点击 `Generate candidates`。
4. 保持 `DeepSeek fallback` 勾选。
5. 点击 `Run mapping`。

运行完成后，页面会显示：

- `Candidates`
- `Mappings`
- `Need review`
- 映射表格中的 source、target、method、confidence、status

注意：DeepSeek fallback 只会在确定性规则没有完成映射时触发。内置 demo 可能已经被规则完全命中，因此不一定每次都出现 `llm_fallback` 方法。若要专门验收 fallback，可在创建任务前把 `Mapping Template` 中某个字段的 alias 或 regex 临时改掉，让规则无法命中该字段，然后再创建任务并运行映射。

## 4. 人工确认

1. 在 `Mapping / Review` 页面查看 `Need review` 行。
2. 对每一行检查 source value、target field、method、confidence、evidence。
3. 如目标字段不正确，在该行的下拉框里选择正确 target。
4. 点击该行 `Confirm`。
5. 重复直到需要复核的行都确认完成。

如果仍有 `review_required` 状态，转换会被阻止。此时回到映射页继续确认剩余行。

## 5. 转换

1. 打开左侧 `Detail / Read`。
2. 点击 `Refresh`，确认当前任务信息已加载。
3. 点击 `Convert task`。
4. 成功后状态应变为 `rendered`。

转换成功后，可在页面中查看 canonical、mapping report、validation report、consistency report 和 trace。若转换失败，优先检查是否还有未确认映射，或 required 字段是否缺失。

## 6. 打包

1. 打开左侧 `Package / Create`。
2. 确认任务状态是 `rendered` 或 `completed`。
3. `Package version` 可保持默认 `1.0.0`。
4. 点击 `Build package`。

成功后页面会显示：

- `Package ID`
- `Status`
- `ZIP path`
- `SHA-256`
- `External verifier`

其中 `External verifier` 应显示 `Verifier passed`，并显示已验证 payload 数量和 issue 数量。

## 7. 下载与 verifier

网页内 verifier：

1. 在 `Package / Create` 点击 `Build package`。
2. 查看 `External verifier`。
3. 验收通过时应看到 `Verifier passed`。
4. issue 数量应为 `0 issues`。

下载 ZIP：

1. 点击 `Download ZIP`。
2. 浏览器会下载 `standard_package.zip`。
3. 页面会显示下载响应头中的 `Download header` SHA-256。

可选 CLI 二次验收：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m app.tools.package_verifier "C:\Users\<你的用户名>\Downloads\standard_package.zip"
.\.venv\Scripts\python -m app.tools.consume_package "C:\Users\<你的用户名>\Downloads\standard_package.zip"
```

期望结果：

- verifier 输出 `passed: true`
- verifier 输出 `issues: []`
- consumer 能读取业务字段、block 链接和 chunk 链接

## 8. 常见问题

### DeepSeek 没有被调用

检查：

1. 后端 `.env` 中 `OFFLINE_MODE=false`。
2. 后端 `.env` 中 `LLM_BASE_URL=https://api.deepseek.com`。
3. 后端 `.env` 中 `LLM_API_KEY` 是真实 DeepSeek key。
4. 修改 `.env` 后已经重启后端。
5. Mapping 页 `DeepSeek fallback` 已勾选。
6. 当前任务确实存在规则无法命中的目标字段。

### Run mapping 成功但没有 llm_fallback

这通常不是错误。说明 alias、regex 或其他确定性规则已经完成映射。要验收 fallback，需要故意让某个字段无法被规则命中。

### Convert task 按钮不可用或转换失败

检查 Mapping 页是否还有 `Need review` 行。所有需要人工确认的映射都确认后，再回到 `Detail / Read` 转换。

### Build package 按钮不可用

任务必须先转换成功，状态达到 `rendered` 或 `completed` 后才能打包。

### External verifier 没有显示

重新点击 `Build package`。如果仍未显示，检查后端日志中是否有 `package verifier report not found` 或存储写入错误。
