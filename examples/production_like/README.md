# Production-like Evaluation Dataset

This synthetic dataset validates SchemaPack Agent topic 5 boundaries with four
domains: `policy_doc`, `contract_doc`, `meeting_doc`, and `general_doc`.

The samples use the current repository contracts:

- `TargetSchema` JSON files in `schemas/`
- `MappingTemplate` JSON files in `mapping_templates/`
- `UIRDocument` JSON files in `uir/<domain>/`
- machine-readable expectations in `expected/`

The data is synthetic. It does not include raw PDF, Word, Excel, image, OCR, or
other source parsing inputs.

Run the evaluation from the repository root:

```powershell
python scripts/eval_production_like.py
```

The script writes:

- `reports/production_like_eval_report.json`
- `reports/production_like_eval_report.md`
- package-like artifacts under `reports/packages/`

The current checkout does not include production mapping, effective-template,
knowledge, or package services. The evaluator therefore reuses the Pydantic
contracts and executes a deterministic harness while explicitly reporting that
service-layer gap in the generated report.
