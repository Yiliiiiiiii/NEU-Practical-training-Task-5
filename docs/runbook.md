# SchemaPack Agent 启动运行操作文档

本文档适用于 Windows + PowerShell 环境。项目根目录假设为：

```powershell
F:\p2
```

## 1. 前置检查

确认已安装：

- Python 3.13 或兼容版本
- Node.js 18+ 或 20+
- npm

检查命令：

```powershell
python --version
node --version
npm --version
```

## 2. 配置 DeepSeek API Key

本地配置文件位置：

```text
F:\p2\backend\.env
```

只需要确认或修改这一行：

```env
LLM_API_KEY=你的_DeepSeek_API_Key
```

当前项目固定使用 DeepSeek：

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_PROMPT_VERSION=deepseek-phase10-v1
OFFLINE_MODE=false
```

说明：`openai_compatible` 表示使用 OpenAI 兼容协议，不表示调用 OpenAI 服务。实际请求地址由 `LLM_BASE_URL=https://api.deepseek.com` 决定。

安全要求：

- 不要把真实 API Key 写入 `.env.example`、README 或聊天窗口。
- `backend/.env` 已被 git ignore，不会进入版本库。

## 3. 首次安装后端依赖

打开 PowerShell：

```powershell
cd F:\p2\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

如果 `.venv` 已经存在，可跳过创建虚拟环境，只执行安装依赖：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## 4. 启动后端

在第一个 PowerShell 窗口运行：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

期望返回：

```json
{"status":"ok"}
```

OpenAPI 文档：

```text
http://127.0.0.1:8000/docs
```

## 5. 首次安装前端依赖

打开第二个 PowerShell 窗口：

```powershell
cd F:\p2\frontend
npm install
```

如果 `node_modules` 已经存在，通常可跳过。

## 6. 启动前端

在第二个 PowerShell 窗口运行：

```powershell
cd F:\p2\frontend
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

默认 API 地址：

```text
http://127.0.0.1:8000/api/v1
```

如果需要手动指定 API 地址：

```powershell
cd F:\p2\frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
npm run dev
```

## 7. 推荐运行顺序

1. 启动后端。
2. 打开 `http://127.0.0.1:8000/health` 确认后端正常。
3. 启动前端。
4. 打开 `http://127.0.0.1:5173`。
5. 在前端执行导入、建任务、候选生成、映射、转换、打包流程。

## 8. DeepSeek Fallback 使用方式

后端 `.env` 配置好 DeepSeek 后，还需要在映射请求中开启：

```json
{
  "enable_llm_fallback": true,
  "review_threshold": 0.8
}
```

在前端工作台里，对应的是映射阶段的 LLM fallback 开关。开启后，规则无法稳定映射的字段会尝试调用 DeepSeek，并进入人工复核。

## 9. 常用验证命令

后端测试：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m pytest -q
```

后端完整质量门禁：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m pytest --cov=app --cov-branch --cov-report=json:coverage.json -q
.\.venv\Scripts\python tests\coverage_gate.py coverage.json
.\.venv\Scripts\python -m ruff check .
```

前端质量门禁：

```powershell
cd F:\p2\frontend
npm run test:coverage
npm run lint
npm run build
```

## 10. 常见问题

### 后端端口 8000 被占用

换一个端口启动：

```powershell
cd F:\p2\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

然后前端指定新的 API 地址：

```powershell
cd F:\p2\frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8001/api/v1"
npm run dev
```

### 前端端口 5173 被占用

Vite 会自动提示可用端口，或手动指定：

```powershell
cd F:\p2\frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

### DeepSeek 没有被调用

检查：

1. `backend/.env` 中 `LLM_MODE=openai_compatible`
2. `backend/.env` 中 `OFFLINE_MODE=false`
3. `backend/.env` 中 `LLM_API_KEY` 是真实 key
4. 重启过后端
5. 映射请求或前端开关启用了 `enable_llm_fallback=true`

### 修改 `.env` 后不生效

`.env` 只在后端启动时读取。修改后需要停止并重启后端服务。

## 11. 关闭服务

在对应 PowerShell 窗口按：

```text
Ctrl + C
```

分别关闭后端和前端。
