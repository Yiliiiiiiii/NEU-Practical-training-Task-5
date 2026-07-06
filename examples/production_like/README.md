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

The evaluator runs the current production mapping, effective-template,
review/knowledge, content-organization, package, and verifier services against
isolated synthetic fixtures. It does not use raw-document parsing, OCR, network
LLM calls, or autonomous rule activation.
