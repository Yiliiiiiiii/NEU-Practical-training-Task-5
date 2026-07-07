# Phase D/E/F Handoff

Generated at: 2026-07-07T12:46:18.601682+00:00

## Summary

- Dataset size: 50
- Phase D average recall: 0.742603
- Phase D strict pass: 39/50
- Policy recall: 0.665575
- Meeting recall: 0.763704
- General recall: 0.824206
- Required missing: 2
- Review required: 21
- Badcase violations: 0
- LLM auto accepted: 0
- Package verification: 50/50
- Secret leaks: 0

## Phase D Status

- Achieved: strict_pass >= 38/50, meeting_doc recall >= 0.76, required_missing <= 2, badcase violations = 0, package verification = 50/50.
- Not achieved: average_recall >= 0.78, policy_doc recall >= 0.75, general_doc recall >= 0.85, review_required <= 18.
- Current bottleneck is policy_doc: recall remains 0.665575 with 2 required-missing items.

## UIR Quality Gate Result

- Total UIR evaluated: 60
- Pass: 12
- Review: 48
- Reject: 0
- Unsupported: 0
- Allow auto accept count: 12

## DeepSeek Result

- configured: True
- provider smoke: passed
- suggestions: 2
- evidence-linked suggestions: report-only smoke path; no accepted mapping mutation
- measurable contribution: 0.0 in production mapping evaluator
- failure modes: 0 warnings; no secret leak detected by smoke

## Review Judge Result

- pending reviewed: 979
- approve suggestions: 0
- reject suggestions: 26
- keep pending: 953
- applied approve: 0
- applied reject: 0
- unsafe skipped: 953
- reviewer_type: codex_review_judge / ai_review_subagent simulation, not human reviewer

## 0.85 Status

- 50-sample score: average_recall 0.742603
- blind-set score: None
- can claim 0.85: false
- if not, why: No independent production shadow/blind UIR corpus with gold labels is present in this workspace.; current 50-sample average recall is below 0.85 and no independent production blind set is available.

## Remaining Gaps

- policy_doc: required issuer/publish_date edge cases and long-tail policy fields remain the main bottleneck.
- meeting_doc: current strict pass 15/15; remaining review items are intentionally not auto-accepted.
- general_doc: `real_general_011` and `real_general_013` remain below recall threshold.

## Safety

- badcase: 0
- LLM auto accepted: 0
- secret redaction: passed; exact secret hits 0
- old snapshots: not modified intentionally.
- knowledge pack scope: no active knowledge pack activation in this sprint.

## Reports

- `reports/phase_d_non_procurement_mapping_eval_report.json/.md`
- `reports/phase_d_semantic_mapping_quality_report.json/.md`
- `reports/phase_d_strict_validation_failure_analysis.json/.md`
- `reports/phase_d_report_consistency.json/.md`
- `reports/deepseek_provider_smoke_report.json/.md`
- `reports/deepseek_ablation_report.json/.md`
- `reports/review_judge_subagent_report.json/.md`
- `reports/ai_review_apply_report.json/.md`
- `reports/secret_redaction_audit_report.json/.md`
- `reports/production_shadow_dataset_plan.md`
- `reports/blind_set_eval_report.json/.md`

## Commands

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_candidate_service_non_procurement.py -q
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\phase_d_non_procurement_mapping_eval_report.json --markdown reports\phase_d_non_procurement_mapping_eval_report.md
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```
