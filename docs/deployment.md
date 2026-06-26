# SchemaPack Agent Deployment

This project includes a minimal containerized deployment profile for local or
single-host demos. It packages the FastAPI backend and the React/Vite frontend
behind Nginx.

## Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080/
```

The backend is also exposed directly for API/debug checks:

```text
http://127.0.0.1:8000/health
```

## Services

- `backend` builds from `backend/Dockerfile`, initializes SQLite tables at
  startup, serves FastAPI on port `8000`, and reads production-like schema and
  template fixtures from the image.
- `frontend` builds from `frontend/Dockerfile`, serves the static Vite build
  through Nginx on port `8080`, and proxies `/api/*` and `/health` to the
  backend service.
- Root-level `Dockerfile.backend` and `Dockerfile.frontend` mirror the service
  Dockerfiles for delivery checklists that expect those names.

## Runtime Data

Compose creates two named volumes:

- `schemapack_storage` mounted at `/data/storage` for imported UIR files,
  generated reports, and packages.
- `schemapack_db` mounted at `/data/db` for the SQLite database file.

To reset local runtime data:

```powershell
docker compose down -v
```

## Environment Profiles

Use `.env.example` for local Python development. Use
`.env.production.example` as the container profile reference:

```text
APP_ENV=production
STORAGE_ROOT=/data/storage
DATABASE_URL=sqlite:////data/db/schemapack.db
LLM_MODE=disabled
LLM_FALLBACK_ENABLED=false
OFFLINE_MODE=true
```

The production profile keeps LLM fallback disabled by default. To enable a
configured OpenAI-compatible endpoint, set `LLM_FALLBACK_ENABLED=true`,
`LLM_MODE=openai_compatible`, `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
Authentication, TLS termination, audit logging, and multi-tenant controls are
not part of this deployment profile.
