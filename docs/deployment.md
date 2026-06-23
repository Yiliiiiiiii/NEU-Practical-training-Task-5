# Deployment

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## DeepSeek LLM Fallback

Offline/default-safe modes:

```powershell
$env:LLM_MODE="disabled"
$env:OFFLINE_MODE="true"
```

SchemaPack Agent is configured to use DeepSeek for live fallback calls:

```powershell
$env:LLM_MODE="openai_compatible"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_API_KEY="<your-deepseek-api-key>"
$env:LLM_MODEL="deepseek-v4-flash"
$env:LLM_PROMPT_VERSION="deepseek-phase10-v1"
```

Local automated tests use mock transports and do not claim a live cloud model call.
