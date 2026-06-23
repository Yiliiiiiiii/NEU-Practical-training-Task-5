param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:5173"
)

Write-Host "SchemaPack Agent Phase 10 demo"
Write-Host "Backend:  $BackendUrl"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""
Write-Host "1. Start backend:"
Write-Host "   cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --reload"
Write-Host "2. Start frontend:"
Write-Host "   cd frontend; npm run dev"
Write-Host "3. Open the desktop workbench and run import -> mapping -> convert -> package."
Write-Host "4. Verify package:"
Write-Host "   cd backend; .\.venv\Scripts\python -m app.tools.package_verifier <zip>"
Write-Host "5. Consumer smoke:"
Write-Host "   cd backend; .\.venv\Scripts\python -m app.tools.consume_package <zip>"
Write-Host "6. Evaluation:"
Write-Host "   cd backend; .\.venv\Scripts\python -m app.tools.evaluate_mappings ..\examples\eval\eval_cases.json"
