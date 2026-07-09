$ErrorActionPreference = "Stop"

$HandoffDir = -join ([char[]](20132, 25509))
$EvidenceRoot = Join-Path -Path (Join-Path -Path "docs" -ChildPath $HandoffDir) -ChildPath "evidence\strengthen_stage"

New-Item -ItemType Directory -Force -Path `
  "$EvidenceRoot\mapping", `
  "$EvidenceRoot\mapping\splits", `
  "$EvidenceRoot\llm", `
  "$EvidenceRoot\review", `
  "$EvidenceRoot\content", `
  "$EvidenceRoot\package", `
  "$EvidenceRoot\operation", `
  "$EvidenceRoot\final" | Out-Null

backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
Pop-Location

backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md `
  --timeout 60

backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-dir "$EvidenceRoot\mapping\splits"

backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
  --report reports\non_procurement_mapping_eval_report.json `
  --out-json "$EvidenceRoot\mapping\mapping_gap_analysis.json" `
  --out-md "$EvidenceRoot\mapping\mapping_gap_analysis.md"

backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
  --out-json "$EvidenceRoot\mapping\mapping_overfit_risk_report.json" `
  --out-md "$EvidenceRoot\mapping\mapping_overfit_risk_report.md"

try {
  backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
    --report "$EvidenceRoot\mapping\splits\summary.json" `
    --min-assisted-recall 0.85 `
    --max-badcase-violations 0 `
    --max-required-missing 0 `
    --max-dev-test-gap 0.05 `
    --max-test-blind-gap 0.05 `
    *> "$EvidenceRoot\mapping\mapping_quality_gate_result.md"
} catch {
  "Mapping gate failed; see split summary." | Out-File -FilePath "$EvidenceRoot\mapping\mapping_quality_gate_result.md" -Encoding utf8 -Append
}

backend\.venv\Scripts\python.exe scripts\eval_deepseek_mapping_suggestions.py `
  --mode report-only `
  --max-cases 15 `
  --out-json "$EvidenceRoot\llm\deepseek_mapping_live_eval_report.json" `
  --out-md "$EvidenceRoot\llm\deepseek_mapping_live_eval_report.md"

backend\.venv\Scripts\python.exe scripts\eval_codex_review_subagent.py `
  --mode dry-run `
  --out-json "$EvidenceRoot\review\codex_review_subagent_live_report.json" `
  --out-md "$EvidenceRoot\review\codex_review_subagent_live_report.md"

backend\.venv\Scripts\python.exe scripts\eval_content_tag_summary_quality.py `
  --out-json "$EvidenceRoot\content\content_tag_summary_quality_report.json" `
  --out-md "$EvidenceRoot\content\content_tag_summary_quality_report.md"

backend\.venv\Scripts\python.exe scripts\eval_basic_stage_package_consistency.py `
  --out-json "$EvidenceRoot\package\package_consistency_report.json" `
  --out-md "$EvidenceRoot\package\package_consistency_report.md"

backend\.venv\Scripts\python.exe scripts\eval_field_operations_quality.py `
  --out-json "$EvidenceRoot\operation\field_operation_quality_report.json" `
  --out-md "$EvidenceRoot\operation\field_operation_quality_report.md"

backend\.venv\Scripts\python.exe scripts\eval_schema_validation_localization.py `
  --out-json "$EvidenceRoot\operation\schema_validation_localization_report.json" `
  --out-md "$EvidenceRoot\operation\schema_validation_localization_report.md"

backend\.venv\Scripts\python.exe scripts\build_strengthen_stage_final_gate.py `
  --evidence-root "$EvidenceRoot" `
  --out "$EvidenceRoot\final\strengthen_stage_final_gate_result.md"
