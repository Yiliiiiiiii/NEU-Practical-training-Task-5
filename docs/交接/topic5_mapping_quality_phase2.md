# Topic 5 Mapping Quality Phase 2

Phase 2 adds an independent Topic 5 standard UIR mapping benchmark and a
feature-flagged global assignment mapper.

## Scope

The measured claim is limited to:

- standard UIR inputs
- registered or inline target schemas
- declared mapping rules
- benchmarked document families in `eval/topic5_standard_uir`
- no gold leakage from blind split tuning

This is not a production shadow/blind claim unless
`production_shadow_eval_report.json` is also completed.

## Latest Gate Evidence

Evidence files:

- `reports/topic5_mapping_quality_gate_report.json`
- `reports/topic5_mapping_quality_gate_report.md`
- `reports/topic5_standard_uir_global_dev.json`
- `reports/topic5_standard_uir_global_test.json`
- `reports/topic5_standard_uir_global_blind.json`

Measured global-assignment gate:

- status: passed
- auto precision: 0.9310 on test
- auto recall: 1.0000 on test
- review-required rate: 0.0000 on test
- required missing: 0
- badcase violations: 0
- test vs blind recall gap: 0.0000

Allowed statement:

> The project can claim Topic 5 benchmark-level auto mapping recall >= 0.85
> within the declared standard UIR benchmark scope.

Forbidden overclaim:

> Production-grade arbitrary-schema or production shadow/blind recall >= 0.85.
