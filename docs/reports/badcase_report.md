# Badcase Report

Versioned badcases live in `examples/badcases/`:

- `badcase_missing_required.json`
- `badcase_type_error.json`
- `badcase_mapping_ambiguous.json`
- `badcase_broken_block_link.json`

Phase 10 package verifier tests additionally cover:

- Missing manifest
- Manifest self-reference
- Unsafe ZIP paths
- Backslash paths
- Extra payload files
- Missing payload files
- Byte-count mismatch
- SHA-256 mismatch
- Invalid JSON
- Oversized JSON payloads

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests\test_phase9_badcases.py tests\test_phase10_package_verifier.py -q
```
