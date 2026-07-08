# Phase G UIR 0.85 Handoff

## Summary

- Current 50-sample average recall: 0.742603
- Current strict pass: 39/50
- Policy recall: 0.665575
- Meeting recall: 0.763704
- General recall: 0.824206
- Required missing: 2
- Review required: 21
- Badcase violations: 0
- LLM auto accepted: 0
- Package verification: 50/50
- Secret leaks: 0

## Review Scope Fix

- current evaluator review_required: 21
- scoped review items found: 1105
- historical skipped: not reliable; current queue records do not carry enough run/split metadata
- procurement skipped: not reliable; dry-run scope still found multiple schema families
- consistency: failed for Phase G apply purposes; apply-guarded was not run

## Policy Hardening

- policy recall before: 0.665575
- policy recall after: 0.665575 on current 50-sample report
- strict pass before: 11/20
- strict pass after: 11/20
- remaining policy gaps: issuer/date-role ambiguity, source evidence ranking, and gold-aligned policy measures still need corpus-level tuning

## General Hardening

- general recall before: 0.824206
- general recall after: 0.824206 on current 50-sample report
- remaining general gaps: service object and summary review-required cases remain in the current evaluator

## DeepSeek Ablation

- provider configured: true; smoke passed with suggestion_count=2 and secret_leak_detected=false
- candidate count: 0
- evidence-linked candidate count: 0
- judge-supported count: 0
- recall delta: 0.0
- required_missing delta: 0
- review_required delta: 0
- safety result: badcase=0, llm_auto_accepted=0, secret_leaks=0
- effectiveness: DeepSeek reachable but no measurable contribution in this round

## Review Judge

- dry-run: completed
- apply-guarded: not run
- applied approve: 0
- applied reject: 0
- kept pending: 1105
- unsafe skipped: 1105

## Knowledge Pack

- draft created: false
- impact preview: blocked
- activated: false
- scope: phase_g
- badcase result: 0

## Production Shadow / Blind

- production shadow exists: false
- blind doc count: 0
- gold coverage: blocked
- blind average recall: 0.0
- auto precision: 0.0
- mapped_or_review recall: 0.0
- can claim 0.85: false
- if false, why: independent production blind UIR corpus with gold labels is missing

## Final Claim

Cannot claim:
The system has Phase G code/test/report improvements, but it cannot honestly claim 0.85+ because the production blind corpus is missing, current blind eval is blocked, DeepSeek has no measurable contribution in this round, Review Judge scope is not consistent with the 50-sample evaluator, and current local 50-document recall remains below 0.85.

## Commands

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_review_scope_filtering.py backend\tests\test_run_review_judge_subagent.py backend\tests\test_policy_publish_date_extractor.py backend\tests\test_policy_issuer_extractor.py backend\tests\test_policy_effective_date_extractor.py backend\tests\test_policy_measures_extractor.py backend\tests\test_policy_target_audience_extractor.py backend\tests\test_policy_date_role_classifier.py backend\tests\test_general_contact_extractor.py backend\tests\test_general_service_object_extractor.py backend\tests\test_general_application_conditions_ranking.py backend\tests\test_deepseek_candidate_ablation.py backend\tests\test_production_shadow_gold_coverage.py backend\tests\test_general_process_steps_extractor.py -q
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
backend\.venv\Scripts\python.exe scripts\eval_deepseek_smoke.py --out reports\phase_g_deepseek_smoke_report.json --markdown reports\phase_g_deepseek_smoke_report.md
backend\.venv\Scripts\python.exe scripts\eval_deepseek_candidate_ablation.py --base-url http://127.0.0.1:8000 --dataset examples\real_world --focus-doc-type policy_doc --focus-fields issuer,publish_date,effective_date,policy_measures,target_audience,document_number --out reports\phase_g_deepseek_candidate_ablation_report.json --markdown reports\phase_g_deepseek_candidate_ablation_report.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\phase_g_non_procurement_mapping_eval_report.json --markdown reports\phase_g_non_procurement_mapping_eval_report.md
backend\.venv\Scripts\python.exe scripts\audit_secret_redaction.py --out reports\phase_g_secret_redaction_audit_report.json --markdown reports\phase_g_secret_redaction_audit_report.md
backend\.venv\Scripts\python.exe scripts\check_production_shadow_gold_coverage.py --manifest examples\production_shadow\manifest.json --gold examples\production_shadow\gold\mapping_gold.jsonl --out reports\production_shadow_gold_coverage_report.json --markdown reports\production_shadow_gold_coverage_report.md
backend\.venv\Scripts\python.exe scripts\eval_production_shadow_mapping.py --base-url http://127.0.0.1:8000 --manifest examples\production_shadow\manifest.json --split blind --gold examples\production_shadow\gold\mapping_gold.jsonl --badcases examples\production_shadow\gold\badcases.jsonl --out reports\phase_g_blind_set_eval_report.json --markdown reports\phase_g_blind_set_eval_report.md
```
