# SchemaPack Agent Demo Workflow

This workflow exercises the current end-to-end demo path:

1. Start the backend:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Start the frontend:

   ```powershell
   cd ..
   cd frontend
   npm run dev
   ```

3. Open the workbench:

   ```text
   http://127.0.0.1:5173/
   ```

4. Use the sample UIR, then run:

   - Import
   - Create Task
   - Execute

   The sidebar includes deterministic content organization controls. The default
   `heading_aware` strategy is suitable for the demo; `parent_child` can be
   selected to generate parent chunks plus child chunks for downstream retrieval
   tests.

5. Inspect the generated outputs:

   - mapping report
   - validation report
   - content organization report
   - enriched chunk preview with strategy, title path, token estimate, source
     links, quality tags, and optional parent-child ids
   - collapsible raw JSON reports
   - review queue and knowledge pack controls
   - package metadata
   - ZIP download

## API Sequence

The same flow can be exercised without the UI:

```text
GET  /api/v1/schemas
POST /api/v1/schemas
POST /api/v1/schemas/{schema_id}/versions/{version}/activate
GET  /api/v1/templates
POST /api/v1/templates
POST /api/v1/templates/{template_id}/versions/{version}/activate
POST /api/v1/documents/import
POST /api/v1/tasks
POST /api/v1/tasks/{task_id}/execute
GET  /api/v1/tasks/{task_id}/reports/mapping
GET  /api/v1/tasks/{task_id}/reports/validation
GET  /api/v1/tasks/{task_id}/reports/content_organization
GET  /api/v1/tasks/{task_id}/reports/chunks
GET  /api/v1/reviews
GET  /api/v1/knowledge/candidates
GET  /api/v1/knowledge/packs
GET  /api/v1/knowledge/metrics
GET  /api/v1/tasks/{task_id}/package
GET  /api/v1/tasks/{task_id}/package/download
```

## Downstream Smoke

After a ZIP package is generated, verify that a downstream consumer can read it:

```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "鍒跺害 绠＄悊"
```

Export package chunks as a simple training-corpus JSONL:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl
```

The OpenAPI snapshot is exported to:

```text
docs/openapi.json
```

Regenerate it with:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

## Five-priority Evidence Run

Run the review-growth evaluator, the three content-quality evaluators, and the
downstream contract verifier. In the workbench, the **Downstream Readiness**
panel then shows live CSV, source-linked RAG, and verifier readiness for the
current task package.

