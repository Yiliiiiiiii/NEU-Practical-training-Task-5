# Real-world UIR Dataset

This directory contains traceable UIR samples derived from official public documents.
The raw cache is local-only; regenerate it from `sources/source_manifest.json` with the
collection and build scripts. The SchemaPack core still starts from UIR—these tools only
construct evaluation inputs.

The current manifest contains 45 documents across `general_doc`,
`meeting_doc`, `policy_doc`, and `procurement_doc`. The committed evaluation
evidence records 45/45 import, task execution, and package verification.

Run the pipeline from the repository root:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py
```
