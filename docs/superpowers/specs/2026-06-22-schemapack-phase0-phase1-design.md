# SchemaPack Phase 0-1 Design

**Source blueprint:** `SchemaPack_Agent_项目实施文档_修订版.md`

**Approved scope for this slice:** establish the project skeleton and the first executable backend contract. This slice covers Phase 0 and Phase 1 only: FastAPI health wiring, configuration, SQLite session setup, Pydantic data contracts, and demo examples that validate against those contracts.

## Architecture

The backend starts as a small FastAPI application under `backend/app`. Routers remain thin and delegate behavior to services or engines as later phases are added. Pydantic v2 models are the initial contract boundary for UIR, Target Schema, Mapping Template, Mapping, Transform, Canonical Model, reports, packages, reviews, execution snapshots, and output profiles.

The initial file layout follows the blueprint so later services can land without reshuffling:

- `backend/app/main.py` creates the FastAPI app, exposes `/health`, and mounts `/api/v1`.
- `backend/app/config.py` owns environment-driven settings such as storage root, database URL, LLM mode, offline mode, and upload limits.
- `backend/app/db/session.py` creates a SQLAlchemy engine and session factory for SQLite.
- `backend/app/db/models.py` defines the minimal tables from the blueprint.
- `backend/app/schemas/*.py` defines Pydantic contracts.
- `examples/demo/` contains two UIR samples, two Target Schemas, and two Mapping Templates.
- `storage/` is runtime output only and is ignored by source control when Git is initialized.

## Data Contracts

This slice freezes only the MVP-compatible contract shape, not every later product feature. UIR accepts metadata, blocks, assets, and normalization records. Target Schema contains `fields` and `json_schema`; the business schema applies only to `content.json.data` in later phases. Mapping Template contains aliases, regex rules, transform rules, defaults, and enum maps.

All IDs remain strings so examples can use deterministic, human-readable IDs. Timestamps are ISO 8601 strings in model contracts; database timestamps use SQLAlchemy `DateTime` defaults.

## Testing

Tests are written before implementation. The first red tests assert:

- `/health` returns `{"status": "ok"}`.
- settings expose sane defaults and support environment overrides.
- SQLAlchemy metadata includes required MVP tables.
- demo UIR, Target Schema, and Mapping Template files parse through Pydantic models.
- invalid UIR, Target Schema, and Mapping Template inputs fail validation.

## Out Of Scope

This slice does not implement field extraction, mapping, transform execution, rendering, packaging, LLM fallback, frontend pages, Docker, replay, verifier, or evaluation metrics. Those are planned after the Phase 0/1 contracts are green.

## Success Criteria

Running `pytest` in `backend/` passes all bootstrap and schema tests. The project can start locally with `uvicorn app.main:app --reload` from `backend/`, and `GET /health` returns `ok`.

## Notes

The current workspace is not a Git repository, so this design is saved but not committed. If Git is initialized later, this document should be committed with the Phase 0/1 bootstrap changes.
