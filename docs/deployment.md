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

## LLM Fallback

Offline/default-safe modes:

```powershell
$env:LLM_MODE="disabled"
$env:OFFLINE_MODE="true"
```

OpenAI-compatible mode:

```powershell
$env:LLM_MODE="openai_compatible"
$env:LLM_BASE_URL="https://your-compatible-host/v1"
$env:LLM_API_KEY="<secret>"
$env:LLM_MODEL="schema-map-model"
$env:LLM_PROMPT_VERSION="prompt-v10"
```

Local automated tests use mock transports and do not claim a live cloud model call.
