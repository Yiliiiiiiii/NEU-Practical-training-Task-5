# API Usage Examples

These examples assume the backend is running at `http://127.0.0.1:8000`.

## Health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Catalog

List schema versions:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/schemas
```

List template versions:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/templates
```

Activate a schema version:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/schemas/policy_doc/versions/1.0.0/activate
```

## Import UIR

```powershell
$uir = Get-Content examples\production_like\uir\policy\policy_001_standard.json -Raw | ConvertFrom-Json
$body = @{ uir = $uir } | ConvertTo-Json -Depth 100
$document = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/documents/import `
  -ContentType "application/json" `
  -Body $body
$document
```

## Create And Execute Task

```powershell
$taskBody = @{
  doc_id = $document.doc_id
  schema_id = "policy_doc"
  schema_version = "1.0.0"
  template_id = "policy_doc_base_v1"
  template_version = "1.0.0"
  options = @{}
} | ConvertTo-Json -Depth 20

$task = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/tasks `
  -ContentType "application/json" `
  -Body $taskBody

$result = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/execute"

$result
```

## Read Reports

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/mapping"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/validation"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/content-organization"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/reports/chunks"
```

## Review And Knowledge

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reviews?status=pending"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/candidates
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/packs
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/metrics
```

## Package

Package metadata:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package"
```

Download ZIP:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/v1/tasks/$($task.task_id)/package/download" `
  -OutFile "standard_package.zip"
```
