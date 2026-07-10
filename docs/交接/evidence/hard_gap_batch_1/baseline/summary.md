# Topic 5 Hard-Gap Batch 1 Baseline

- Commit: `233b1a9f46382040e4f3e83361466cb53fe6511c`
- Backend: 885 passed, 0 failed.
- Ruff: clean.
- Frontend: 24 tests passed across 8 files; production build passed.
- Focused Topic 5/Package/SchemaPack/content-organization/transform tests: 133 passed across 19 files.
- OpenAPI export: 65 paths.
- Existing mapping-quality and SchemaPack contract gates: passed.
- Existing package verification rate in the mapping gate: 1.0.

## Pre-existing warnings

- `meeting_doc` automatic mapping precision is 0.8 on dev, test, and blind splits.
- `policy_doc` automatic mapping precision is 0.8 on dev, test, and blind splits.
- The first verification invocation was terminated by an orchestration timeout of one second. The authoritative rerun completed successfully; this is not a repository failure.

## Reproduction

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

Raw command output is stored beside this summary.

