FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STORAGE_ROOT=/data/storage
ENV DATABASE_URL=sqlite:////data/db/schemapack.db
ENV LLM_MODE=disabled
ENV LLM_FALLBACK_ENABLED=false
ENV OFFLINE_MODE=true

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/backend/app
COPY examples /app/examples

RUN mkdir -p /data/storage /data/db

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "python -c \"from app.database import init_db; init_db()\" && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
