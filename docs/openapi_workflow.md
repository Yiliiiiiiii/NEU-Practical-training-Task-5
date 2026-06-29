# OpenAPI Workflow

Regenerate `docs/openapi.json` whenever routes, request models, response models,
or auth-visible API behavior changes.

## Export

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

The script imports the FastAPI app and writes `docs/openapi.json`.

## Check Diff

```powershell
git diff -- docs/openapi.json
```

Review path, schema, and response changes before committing.

## API Key Auth

OpenAPI export does not require an API key because it imports the app locally.
When calling a running secured API, pass:

```powershell
$headers = @{ "X-API-Key" = "your-dev-key" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/tasks
```

`/health` remains anonymous.

## Common Issues

- If imports fail, install backend dependencies with
  `.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.
- If `docs/openapi.json` changes unexpectedly, check whether Pydantic schemas or
  router response models changed.
- Re-export after adding routes such as audit or governance endpoints.
