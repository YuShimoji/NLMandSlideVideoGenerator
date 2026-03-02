# CI/CD Local Audit Script
# Usage: .\scripts\ci.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Header($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

Write-Header "1. Environment Check"
node .shared-workflows/scripts/sw-doctor.js

Write-Header "2. Python Unit Tests"
$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping tests."
} else {
    & $python -m pytest -q -m "not slow and not integration" --tb=short
}

Write-Header "3. Type Check (mypy)"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping type check."
} else {
    & $python -m mypy src/core/exceptions.py src/core/interfaces.py src/core/models.py --config-file mypy.ini
}

Write-Header "4. Orchestrator Audit"
node .shared-workflows/scripts/orchestrator-audit.js

Write-Header "5. YMM4 Plugin Consistency"
if (Test-Path ".\scripts\test_task007_scenariob.ps1") {
    # Skip build but check contracts
    & .\scripts\test_task007_scenariob.ps1 -SkipBuild
}

Write-Header "CI Audit Completed Successfully"
