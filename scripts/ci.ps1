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

Write-Header "2. Type Check (mypy - src/)"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping type check."
} else {
    & $python -m mypy src/ --config-file mypy.ini --ignore-missing-imports
}

Write-Header "3. Lint Check (ruff)"
if (-not (Test-Path $python)) {
    Write-Warning "Python venv not found. Skipping lint check."
} else {
    & $python -m ruff check src/
}

Write-Header "4. Task Report Consistency"
if (Test-Path ".\scripts\check_task_reports.js") {
    node scripts/check_task_reports.js
} else {
    Write-Host "check_task_reports.js not found, skipping."
}

Write-Header "5. YMM4 Plugin Consistency (optional)"
$ymm4Dir = "$env:LOCALAPPDATA\YukkuriMovieMaker4"
if (-not (Test-Path $ymm4Dir)) {
    Write-Host "YMM4 not installed - skipping plugin consistency check." -ForegroundColor Yellow
} elseif (Test-Path ".\scripts\test_task007_scenariob.ps1") {
    & .\scripts\test_task007_scenariob.ps1 -SkipBuild
}

Write-Header "CI Audit Completed Successfully"
