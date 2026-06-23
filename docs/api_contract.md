# API Contract

Base path: `/api/v1`

The frozen Phase 10 OpenAPI document is `docs/openapi.json`.

## Core Workflow

1. `POST /documents/import`
2. `POST /schemas`
3. `POST /templates`
4. `POST /tasks`
5. `POST /tasks/{task_id}/generate-candidates`
6. `POST /tasks/{task_id}/map`
7. `POST /tasks/{task_id}/mappings/review`
8. `POST /tasks/{task_id}/convert`
9. `POST /tasks/{task_id}/package`
10. `GET /tasks/{task_id}/package/download`

## Phase 10 Additions

- `POST /tasks/{task_id}/replay`
- `GET /tasks/{task_id}/reports/package-verifier`

All API errors use:

```json
{"error":{"code":"NOT_FOUND","message":"task not found","details":[]}}
```

Run the contract matrix:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests\test_api_contract_matrix.py -q
```
