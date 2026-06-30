# SchemaPack Agent Deployment

This project includes two supported local profiles:

- local development: FastAPI backend on `127.0.0.1:8000` and Vite frontend on
  `127.0.0.1:5173`;
- Docker Compose demo: backend plus Nginx-served frontend on
  `127.0.0.1:8080`, with the backend also exposed on `127.0.0.1:8000`.

The production runtime boundary remains UIR input to schema-governed package
output. Raw PDF/Word/Excel/image/OCR parsing is outside this deployment profile.

## Local Backend And Frontend

From the repository root, verify the baseline:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Start the backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000`.

## Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080/
```

The backend health endpoint remains available for API/debug checks:

```text
http://127.0.0.1:8000/health
```

Stop the profile:

```powershell
docker compose down
```

Reset container runtime data:

```powershell
docker compose down -v
```

## Services

- `backend` builds from `backend/Dockerfile`, initializes SQLite tables at
  startup, serves FastAPI on port `8000`, and reads schema/template fixtures
  from the image.
- `frontend` builds from `frontend/Dockerfile`, serves the static Vite build
  through Nginx on port `8080`, and proxies `/api/*` and `/health` to the
  backend service.
- Root-level `Dockerfile.backend` and `Dockerfile.frontend` mirror the service
  Dockerfiles for delivery checklists that expect those names.

## SQLite And Storage Locations

Local Python development uses the configured `DATABASE_URL` and storage root
from `.env` or defaults. In the repository profile, that commonly means:

```text
backend/schemapack.db
storage/
```

Docker Compose creates two named volumes:

- `schemapack_storage` mounted at `/data/storage` for imported UIR files,
  generated reports, and packages.
- `schemapack_db` mounted at `/data/db` for the SQLite database file.

The container database URL in `.env.production.example` points to:

```text
sqlite:////data/db/schemapack.db
```

## Environment Profiles

Use `.env.example` for local Python development. Use
`.env.production.example` as the Docker Compose reference. The production
example includes:

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

Keep secrets in environment variables or the deployment secret manager around
this project. Do not put API keys or LLM keys in task options, reports, fixtures,
or committed `.env` files.

## Optional API-Key Authentication

API-key authentication is disabled by default:

```text
API_KEY_AUTH_ENABLED=false
API_KEYS=
```

Enable it for `/api/v1/*` with:

```text
API_KEY_AUTH_ENABLED=true
API_KEYS=dev-key-1,dev-key-2
```

When enabled, callers must send `X-API-Key`. `/health` remains anonymous.

## Optional LLM Modes

LLM fallback is default-disabled:

```text
LLM_MODE=disabled
LLM_FALLBACK_ENABLED=false
```

Supported modes are:

- `disabled`: no provider calls; deterministic mapping still runs.
- `stub`: deterministic local suggestion behavior for tests and demos.
- `openai_compatible`: configured network endpoint for review-only suggestions.

To enable an OpenAI-compatible endpoint, configure:

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

Fallback suggestions remain review-required. Provider errors become mapping
warnings unless global `LLM_STRICT_FAILURE=true` or task option
`strict_llm=true` explicitly requests failure.

## Audit Logs And Retention

Audit logging is enabled by default for task execution and package downloads.
Audit entries should contain identifiers, paths, status, and small metadata; do
not log API keys, LLM keys, full UIR payloads, or package contents.

Artifact retention cleanup is disabled by default and has a dry-run mode:

```powershell
backend\.venv\Scripts\python.exe scripts\retention_cleanup.py --storage-root storage --days 30 --dry-run --json
backend\.venv\Scripts\python.exe scripts\retention_cleanup.py --storage-root storage --days 30 --delete
```

## Boundaries Not Provided By This Profile

This repository does not provide built-in TLS termination, SSO, tenant-aware
authorization, RBAC, managed secret storage, hosted credential provisioning, or
enterprise model/provider monitoring. Add those through the target deployment
platform before using the service outside a trusted local or single-host demo
environment.
