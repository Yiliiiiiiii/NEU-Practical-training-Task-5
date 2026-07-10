# Topic 5 Field Operations

- Dataset: `topic5_field_operations_v1` `1.0.0`
- Dataset SHA-256: `bc09416bb5dd75bc797fc3eb589902e85b4b76b3046d19477bb1a32a2281a989`
- Commit: `0d039e45169f9fa684e85afc08a3128fda41a509`
- Cases: 110
- Accuracy: 1.000
- Unsafe operations accepted: 0

| Category | Passed | Total | Accuracy |
| --- | ---: | ---: | ---: |
| rename | 20 | 20 | 1.000 |
| merge | 15 | 15 | 1.000 |
| split | 15 | 15 | 1.000 |
| conversion | 20 | 20 | 1.000 |
| default | 10 | 10 | 1.000 |
| nested_array | 10 | 10 | 1.000 |
| unsafe | 20 | 20 | 1.000 |

Reproduce: `backend/.venv/Scripts/python.exe scripts/eval_topic5_field_operations.py`

Claim boundary: Measures deterministic Topic 5 field operations only; it does not measure semantic extraction, retrieval, or downstream quality scoring.
