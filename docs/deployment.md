# SchemaPack Agent 部署说明

本项目支持两种本地运行方式：

- 本地开发：FastAPI backend 运行在 `127.0.0.1:8000`，Vite frontend 运行在 `127.0.0.1:5173`。
- Docker Compose demo：backend 加 Nginx 托管的 frontend，入口为 `127.0.0.1:8080`，backend 同时暴露在 `127.0.0.1:8000`。

生产运行边界仍然是从 UIR 输入到 schema-governed package 输出。Raw PDF、Word、Excel、image、OCR parsing 不属于此部署 profile。

## 本地 Backend 与 Frontend

从仓库根目录先验证基线：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

推荐一键启动：

```powershell
.\scripts\start_dev.ps1
```

手动启动 backend：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端启动 frontend：

```powershell
cd frontend
npm ci
npm run dev
```

打开：

```text
http://127.0.0.1:5173/
```

Vite development server 会把 `/api` 代理到 `http://127.0.0.1:8000`。

## Docker Compose

从仓库根目录运行：

```powershell
docker compose up --build
```

打开：

```text
http://127.0.0.1:8080/
```

Backend health endpoint 仍可用于 API/debug 检查：

```text
http://127.0.0.1:8000/health
```

停止容器 profile：

```powershell
docker compose down
```

重置容器运行时数据：

```powershell
docker compose down -v
```

## Services

- `backend` 从 `backend/Dockerfile` 构建，启动时初始化 SQLite tables，在 port `8000` 提供 FastAPI，并从镜像读取 schema/template fixtures。
- `frontend` 从 `frontend/Dockerfile` 构建，通过 Nginx 在 port `8080` 提供静态 Vite build，并把 `/api/*` 与 `/health` 代理到 backend service。
- 根目录的 `Dockerfile.backend` 和 `Dockerfile.frontend` 与 service Dockerfiles 对齐，用于需要这些文件名的交付检查。

## SQLite 与 Storage 位置

本地 Python 开发使用 `.env` 或默认值中的 `DATABASE_URL` 和 storage root。仓库 profile 下通常是：

```text
backend/schemapack.db
storage/
```

Docker Compose 创建两个 named volumes：

- `schemapack_storage` 挂载到 `/data/storage`，用于 imported UIR files、generated reports 和 packages。
- `schemapack_db` 挂载到 `/data/db`，用于 SQLite database file。

容器数据库 URL 在 `.env.production.example` 中指向：

```text
sqlite:////data/db/schemapack.db
```

## Environment Profiles

本地 Python 开发使用 `.env.example`。Docker Compose 参考 `.env.production.example`。production 示例包含：

```text
APP_ENV=production
STORAGE_ROOT=/data/storage
DATABASE_URL=sqlite:////data/db/schemapack.db
LLM_MODE=disabled
LLM_FALLBACK_ENABLED=false
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=0
LLM_MAX_SUGGESTIONS_PER_TASK=20
LLM_STRICT_FAILURE=false
OFFLINE_MODE=true
API_KEY_AUTH_ENABLED=false
API_KEYS=
AUDIT_LOG_ENABLED=true
ARTIFACT_RETENTION_ENABLED=false
ARTIFACT_RETENTION_DRY_RUN=true
```

Secret 应放在环境变量或目标部署平台的 secret manager 中。不要把 API keys 或 LLM keys 写入 task options、reports、fixtures 或提交的 `.env` 文件。

## 可选 API-Key Authentication

API-key authentication 默认关闭：

```text
API_KEY_AUTH_ENABLED=false
API_KEYS=
```

如需保护 `/api/v1/*`，启用：

```text
API_KEY_AUTH_ENABLED=true
API_KEYS=dev-key-1,dev-key-2
```

启用后调用方必须发送 `X-API-Key`。`/health` 保持匿名可访问。

## 可选 LLM Modes

LLM fallback 默认关闭：

```text
LLM_MODE=disabled
LLM_FALLBACK_ENABLED=false
```

支持模式：

- `disabled`：不调用 provider；确定性 Mapping 仍运行。
- `stub`：用于测试和 demo 的确定性本地 suggestion 行为。
- `openai_compatible`：配置网络 endpoint，用于仅 Review 的 suggestion。

启用 OpenAI-compatible endpoint：

```text
LLM_FALLBACK_ENABLED=true
LLM_MODE=openai_compatible
LLM_BASE_URL=https://your-compatible-endpoint/v1
LLM_API_KEY=...
LLM_MODEL=...
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=0
LLM_MAX_SUGGESTIONS_PER_TASK=20
LLM_STRICT_FAILURE=false
```

Fallback suggestions 必须保持 review-required。Provider errors 会变成 mapping warnings，除非全局 `LLM_STRICT_FAILURE=true` 或 task option `strict_llm=true` 显式要求失败。

## Audit Logs 与 Retention

Audit logging 默认用于 task execution 和 package downloads。Audit entries 只应包含 identifiers、paths、status 和小型 metadata；不要记录 API keys、LLM keys、完整 UIR payload 或 package contents。

Artifact retention cleanup 默认关闭，并支持 dry-run：

```powershell
backend\.venv\Scripts\python.exe scripts\retention_cleanup.py --storage-root storage --days 30 --dry-run --json
backend\.venv\Scripts\python.exe scripts\retention_cleanup.py --storage-root storage --days 30 --delete
```

## 此 Profile 不提供的能力

仓库本身不提供内置 TLS termination、SSO、tenant-aware authorization、RBAC、managed secret storage、hosted credential provisioning 或 enterprise model/provider monitoring。若要在可信本地或单机 demo 之外使用，需要在目标部署平台补齐这些能力。
