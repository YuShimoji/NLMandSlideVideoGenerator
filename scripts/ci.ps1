# CI/CD Local Audit Script
# Usage: .\scripts\ci.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Header($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

Write-Header "1. Python Unit Tests"
$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping tests."
} else {
    & $python -m pytest -q -m "not slow and not integration" --tb=short
}

Write-Header "2. Type Check (mypy)"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping type check."
} else {
    & $python -m mypy src/core/exceptions.py src/core/interfaces.py src/core/models.py --config-file mypy.ini
}

Write-Header "3. Task Report Consistency"
if (Test-Path ".\scripts\check_task_reports.js") {
    node scripts/check_task_reports.js
} else {
    Write-Host "check_task_reports.js not found, skipping."
}

Write-Header "4. YMM4 Plugin Consistency"
if (Test-Path ".\scripts\test_task007_scenariob.ps1") {
    & .\scripts\test_task007_scenariob.ps1 -SkipBuild
}

Write-Header "CI Audit Completed Successfully"
