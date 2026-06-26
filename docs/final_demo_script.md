# SchemaPack Agent Final Demo Script

This script demonstrates the topic 5 flow from governed UIR input to a
downstream-consumable output package.

## 1. Start The System

Container profile:

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080/
```

Local development profile:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

## 2. Run The UI Demo

1. Click `Use Sample UIR`.
2. Click `Import`.
3. Select the default schema/template.
4. Click `Create Task`.
5. Click `Execute`.
6. Inspect:
   - mapping report
   - validation report
   - content organization report
   - package metadata
   - review queue
   - knowledge pack controls
7. Download the ZIP package.

## 3. Run The Evaluator

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe scripts\eval_production_like.py
```

Expected summary:

```text
production-like eval complete: 15 cases, gold=1.0, badcase=1.0
```

Open:

```text
reports/production_like_eval_report.json
reports/production_like_eval_report.md
```

Confirm:

- `badcase_pass_rate` is `1.0`.
- `package_validation.phase_b` packages all pass.
- `content_organization_summary` exists.
- `downstream_smoke_summary.failed_count` is `0`.

## 4. Verify Downstream Consumption

Smoke-test a generated ZIP:

```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "鍒跺害 绠＄悊"
```

Export training-corpus JSONL:

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl
```

## 5. Explain Boundaries

During defense, state clearly:

- Input starts from UIR; raw PDF/Word/Excel/OCR parsing is out of scope.
- LLM fallback is optional, disabled by default, and never auto-accepts.
- Review and knowledge activation are human-gated.
- Output packages are reproducible and verified by manifest checksums.

