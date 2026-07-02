param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173,
  [switch]$NoBrowser,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[SchemaPack] $Message" -ForegroundColor Cyan
}

function Test-PortListening {
  param([int]$Port)
  $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return $null -ne $connection
}

function Assert-PathExists {
  param(
    [string]$Path,
    [string]$Hint
  )
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "$Path not found. $Hint"
  }
}

function Quote-ForPowerShell {
  param([string]$Value)
  return "'" + ($Value -replace "'", "''") + "'"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPython = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
$frontendDir = Join-Path $repoRoot "frontend"
$frontendPackageJson = Join-Path $frontendDir "package.json"
$frontendUrl = "http://127.0.0.1:$FrontendPort/"

Assert-PathExists $backendPython "Create the backend virtualenv and install backend dependencies first."
Assert-PathExists $frontendPackageJson "Check that the frontend directory exists. Run npm ci in frontend before first use."

$backendBusy = Test-PortListening $BackendPort
$frontendBusy = Test-PortListening $FrontendPort

if ($backendBusy) {
  Write-Host "Port $BackendPort is already listening; backend will not be started again." -ForegroundColor Yellow
}

if ($frontendBusy) {
  Write-Host "Port $FrontendPort is already listening; frontend will not be started again." -ForegroundColor Yellow
}

$quotedRepoRoot = Quote-ForPowerShell $repoRoot
$quotedBackendPython = Quote-ForPowerShell $backendPython
$quotedFrontendDir = Quote-ForPowerShell $frontendDir

$backendCommand = "Set-Location -LiteralPath $quotedRepoRoot; " +
  "Write-Host 'Backend API: http://127.0.0.1:$BackendPort' -ForegroundColor Cyan; " +
  "& $quotedBackendPython -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort"

$frontendCommand = "Set-Location -LiteralPath $quotedFrontendDir; " +
  "Write-Host 'Frontend workbench: http://127.0.0.1:$FrontendPort' -ForegroundColor Cyan; " +
  "npm run dev -- --port $FrontendPort"

if ($DryRun) {
  Write-Step "Dry run: no windows will be opened."
  Write-Host ""
  Write-Host "Backend command:"
  Write-Host $backendCommand
  Write-Host ""
  Write-Host "Frontend command:"
  Write-Host $frontendCommand
  Write-Host ""
  Write-Host "Workbench URL: $frontendUrl"
  exit 0
}

if (-not $backendBusy) {
  Write-Step "Opening backend terminal..."
  Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCommand
  ) -WorkingDirectory $repoRoot
}

if (-not $frontendBusy) {
  Write-Step "Opening frontend terminal..."
  Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCommand
  ) -WorkingDirectory $frontendDir
}

if (-not $NoBrowser) {
  Write-Step "Opening browser: $frontendUrl"
  Start-Process $frontendUrl
}

Write-Host ""
Write-Host "Startup requested. Close the opened PowerShell windows to stop services." -ForegroundColor Green
