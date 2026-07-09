$ErrorActionPreference = "Stop"

function Run-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$Command
  )
  Write-Host ""
  Write-Host $Name
  & $Command
}

function Invoke-Native {
  param(
    [Parameter(Mandatory = $true)][scriptblock]$Command
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE"
  }
}

$HandoffDir = -join ([char[]](0x4EA4, 0x63A5))
$EvidenceRoot = Join-Path (Join-Path "docs" $HandoffDir) "evidence\basic_stage"
New-Item -ItemType Directory -Force -Path `
  "$EvidenceRoot\mapping", "$EvidenceRoot\llm", "$EvidenceRoot\review", `
  "$EvidenceRoot\content", "$EvidenceRoot\package", "$EvidenceRoot\final" | Out-Null

Run-Step "[1/9] Verify backend, ruff, frontend build, openapi" {
  Invoke-Native { backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi }
}

Run-Step "[2/9] Frontend tests" {
  Push-Location frontend
  try {
    Invoke-Native { npm.cmd test }
  } finally {
    Pop-Location
  }
}

Run-Step "[3/9] Non-procurement mapping eval" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
      --baseline reports\non_procurement_baseline_report.json `
      --out reports\non_procurement_mapping_eval_report.json `
      --markdown reports\non_procurement_mapping_eval_report.md `
      --timeout 60
  }
}

Run-Step "[4/9] Split evaluator" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_mapping_splits.py `
      --report reports\non_procurement_mapping_eval_report.json `
      --out-dir "$EvidenceRoot\mapping\splits"
  }
}

Run-Step "[5/9] Gap analysis and overfit scan" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\analyze_mapping_gaps.py `
      --report reports\non_procurement_mapping_eval_report.json `
      --out-json "$EvidenceRoot\mapping\mapping_gap_analysis.json" `
      --out-md "$EvidenceRoot\mapping\mapping_gap_analysis.md"
  }

  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\check_mapping_overfit_risk.py `
      --out-json "$EvidenceRoot\mapping\mapping_overfit_risk_report.json" `
      --out-md "$EvidenceRoot\mapping\mapping_overfit_risk_report.md"
  }
}

Run-Step "[6/9] Mapping quality gate" {
  try {
    Invoke-Native {
      backend\.venv\Scripts\python.exe scripts\check_mapping_quality_gate.py `
        --report "$EvidenceRoot\mapping\splits\summary.json" `
        --min-assisted-recall 0.85 `
        --max-badcase-violations 0 `
        --max-required-missing 0 `
        --max-dev-test-gap 0.05 `
        --max-test-blind-gap 0.05 `
        *> "$EvidenceRoot\mapping\mapping_quality_gate_result.md"
    }
  } catch {
    Write-Host "Mapping quality gate failed; failure is recorded and evidence packaging continues."
  }
}

Run-Step "[7/9] DeepSeek suggestion eval" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_deepseek_mapping_suggestions.py `
      --mode report-only `
      --out-json "$EvidenceRoot\llm\deepseek_mapping_suggestion_eval_report.json" `
      --out-md "$EvidenceRoot\llm\deepseek_mapping_suggestion_eval_report.md"
  }
}

Run-Step "[8/9] Codex review subagent eval and content quality eval" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_codex_review_subagent.py `
      --mode dry-run `
      --out-json "$EvidenceRoot\review\codex_review_subagent_report.json" `
      --out-md "$EvidenceRoot\review\codex_review_subagent_report.md"
  }

  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_content_tag_summary_quality.py `
      --out-json "$EvidenceRoot\content\content_tag_summary_quality_report.json" `
      --out-md "$EvidenceRoot\content\content_tag_summary_quality_report.md"
  }
}

Run-Step "[9/9] Package consistency and final matrix" {
  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\eval_basic_stage_package_consistency.py `
      --out-json "$EvidenceRoot\package\package_consistency_report.json" `
      --out-md "$EvidenceRoot\package\package_consistency_report.md"
  }

  Invoke-Native {
    backend\.venv\Scripts\python.exe scripts\build_basic_stage_acceptance_matrix.py `
      --out "$EvidenceRoot\final\basic_stage_acceptance_matrix.md"
  }
}

@"
# Basic-stage Reproducibility Commands

Run from repository root:

````powershell
.\scripts\run_basic_stage_verification.ps1
````

The mapping quality gate may fail while the basic-stage evidence pack remains reproducible. The failure is recorded in:

````text
$EvidenceRoot\mapping\mapping_quality_gate_result.md
````
"@ | Set-Content -LiteralPath "$EvidenceRoot\final\basic_stage_reproducibility_commands.md" -Encoding UTF8

Copy-Item -LiteralPath "$EvidenceRoot\mapping\mapping_quality_gate_result.md" `
  -Destination "$EvidenceRoot\final\basic_stage_final_gate_result.md" -Force
