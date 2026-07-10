# Topic 5 Field Operations

- Dataset: `topic5_field_operations_v1` `1.0.0`
- Dataset SHA-256: `d95ddc02218a6897d0c82ef0a7e68197598493483e2713c7b04df2c97d295254`
- Commit: `783a8530b3b3b7bb0e5099a78a23c3540446683c`
- Cases: 119
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
| unsafe | 29 | 29 | 1.000 |

Reproduce: `backend/.venv/Scripts/python.exe scripts/eval_topic5_field_operations.py`

Claim boundary: Measures deterministic Topic 5 field operations only; it does not measure semantic extraction, retrieval, or downstream quality scoring.
