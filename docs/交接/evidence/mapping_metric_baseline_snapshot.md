# Mapping Metric Baseline Snapshot

## Reproducible Command

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```

## Current Metrics

- dataset_size: 50
- average_recall: 0.808873015873016
- auto_mapping_recall: 0.7774798927613941
- assisted_mapping_recall: 0.8096514745308311
- review_required_rate: 0.043583535108958835
- review_required_count: 18
- required_missing_count: 0
- badcase_violations: 0
- package_verification_pass: 50

## Metric Definition

- auto_mapping_recall counts only automatically accepted correct mappings.
- assisted_mapping_recall counts automatically accepted correct mappings plus review-required correct candidates.
- legacy mapping_recall/average_recall is retained as assisted mapping recall for historical compatibility.
- review_required_rate reports the share of mapping outputs that require human review.

## Known Inconsistencies

- Historical README and Phase D/Phase I reports used `average recall` or `mapping_recall` without always naming the assisted-recall denominator.
- This snapshot is the baseline for the 0.85 sprint; older reports should be treated as historical.

## Decision

Use this report as the baseline for the 0.85 improvement sprint.
