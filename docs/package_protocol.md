# Package Protocol

The standard package is a ZIP with these required root entries:

- `content.json`
- `content.md`
- `chunks.json`
- `metadata.json`
- `config_snapshot.json`
- `mapping_report.json`
- `validation_report.json`
- `consistency_report.json`
- `trace.json`
- `manifest.json`

`manifest.json` never lists itself. The package ZIP SHA-256 is stored in the database and returned in the `X-SHA256` download header.

Phase 10 adds an external verifier report at:

```text
tasks/{task_id}/package_verifier_report.json
```

That report is deliberately outside the ZIP so it cannot change package payload hashes.

Manual verifier command:

```powershell
cd backend
.\.venv\Scripts\python -m app.tools.package_verifier <path-to-standard_package.zip>
```

Consumer smoke command:

```powershell
cd backend
.\.venv\Scripts\python -m app.tools.consume_package <path-to-standard_package.zip>
```
