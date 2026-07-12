# Topic 5 Mapping Engine v2 Evidence

This directory is separate from the immutable `topic5_mapping_v2` dataset. It
contains engine evidence only; it does not modify frozen UIR, gold, rules, or
split files.

- Calibration method: deterministic monotonic bins.
- Fit boundary: frozen public `dev` split only.
- Frozen engine commit: `e2101d0d0cc95235585fc7c2fdd25a0767e19234`.
- Test labels used during fitting: false. The fitter uses only dev decisions for
  parameter and threshold selection; full-dataset hashes may still be verified.
- External blind status: `not_run`.
- Claim boundary: reproducible public benchmark performance, not production
  blind performance or arbitrary-Schema performance.

Reproduce calibration and reports from repository root:

```text
python scripts/fit_topic5_mapping_v2_calibration.py --engine-commit e2101d0d0cc95235585fc7c2fdd25a0767e19234
python scripts/eval_topic5_mapping_v2.py --split dev --fail-on-targets
python scripts/eval_topic5_mapping_v2.py --split test --fail-on-targets
python scripts/check_topic5_mapping_v2_gate.py --output eval/topic5_mapping_engine_v2/reports/gate.json
```
