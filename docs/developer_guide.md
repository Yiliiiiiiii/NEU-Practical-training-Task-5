# Developer Guide

## Project Structure

- `backend/app/api/v1/`: FastAPI routes.
- `backend/app/schemas/`: Pydantic contracts.
- `backend/app/services/`: deterministic conversion services.
- `backend/app/db/models.py`: SQLAlchemy tables created at startup/test setup.
- `frontend/src/`: React/Vite workbench.
- `examples/production_like/`: schemas, templates, UIR fixtures, and expectations.
- `scripts/`: evaluator, package consumers, OpenAPI export, and verification.
- `docs/`: project workflow and handoff documents.

## Main Pipeline

The core line is:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

`TaskExecutionService` owns orchestration. Keep new capabilities optional and
backward-compatible with existing reports and package names.

## Frontend Workbench

The React/Vite workbench in `frontend/src/App.tsx` is a local operator console
for sample UIR import, task creation/execution, report inspection, review
actions, knowledge-pack activation, audit log reads, and package download. Keep
new controls close to the workflow they affect and preserve the existing
`/api` proxy contract.

## Adding Schema Or Template Versions

Use the catalog APIs or add fixtures under `examples/production_like/`. Templates
must validate aliases, regex rules, enum maps, defaults, and transform targets
against the target schema.

## Adding Mapping Rules

Extend `MappingService` in strategy order. New decisions must include
confidence, `confidence_tier`, structured `evidence`, `risk_flags`,
`badcase_filter`, and `review_required_reason` when needed. LLM suggestions must
remain review-required. Keep retry and cap handling in `LLMFallbackService` and
`MappingService`; provider errors should remain warnings unless
`strict_llm=true` is explicitly requested.

## Adding Chunk Strategies

Extend `ContentOrganizationOptions` and `ChunkOrganizerService`. Preserve old
behavior when task options omit `content_organization`. Chunks should keep
source links, title paths, quality tags, and stable report summary keys.

## Updating Package Spec

Update `docs/package_spec.md`, `ManifestService.role`, `PackageService`, and
`PackageVerifierService` together. Run strict verifier tests after changing
required files, roles, media types, or checksum rules.

## Governance

API key auth is optional and disabled by default. Audit logs should record ids,
hash prefixes, paths, status, and small metadata only. Do not log API keys, LLM
keys, full UIR payloads, or package contents. Use
`redact_sensitive_values` for any new persisted options or audit metadata.

## Verification

Common commands:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..\frontend
npm ci
npm test
npm run build
```

Backend test clients create isolated SQLite databases under pytest-managed
temporary directories, initialize their metadata, and override `get_db`.
Running the suite does not depend on an initialized `backend/schemapack.db`.
Frontend verification uses the committed lockfile, so prefer `npm ci` over
`npm install` after checkout.

Unified command:

```powershell
python scripts\verify_all.py --check-openapi
```

The production-like evaluator remains optional for local fast loops:

```powershell
.\backend\.venv\Scripts\python.exe scripts\eval_production_like.py
```

## Common Issues

- Re-run `scripts/export_openapi.py` after route or schema changes.
- Keep `LLM_FALLBACK_ENABLED=false` unless explicitly testing the optional
  adapter.
- Configure LLM credentials only through environment variables; task options
  are intentionally redacted and cannot supply credentials.
- Re-run `npm ci` when `frontend/package-lock.json` changes.
- Treat `storage/`, `reports/`, and `.codegraph/` as local runtime artifacts.
