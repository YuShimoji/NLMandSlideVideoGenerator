# YMM4 Plugin Auto-Deployment Script
# Usage: .\scripts\deploy_ymm4_plugin.ps1 [-Configuration Release|Debug] [-SkipBuild] [-SkipBackup]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release",
    [switch]$SkipBuild,
    [switch]$SkipBackup,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-DeployStep([string]$Message) {
    Write-Host "[DEPLOY] $Message" -ForegroundColor Cyan
}

function Write-DeployWarning([string]$Message) {
    Write-Host "[DEPLOY-WARN] $Message" -ForegroundColor Yellow
}

function Write-DeployError([string]$Message) {
    Write-Host "[DEPLOY-ERROR] $Message" -ForegroundColor Red
}

function Get-DotnetPath() {
    $cmd = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $fallback = "C:\Program Files\dotnet\dotnet.exe"
    if (Test-Path $fallback) {
        return $fallback
    }

    throw "dotnet executable was not found."
}

function Get-Ymm4Dir([string]$PropsPath) {
    if (-not (Test-Path $PropsPath)) {
        throw "Directory.Build.props not found: $PropsPath"
    }

    [xml]$xml = Get-Content -Raw -Encoding UTF8 $PropsPath
    $value = $xml.Project.PropertyGroup.YMM4DirPath
    if (-not $value) {
        throw "YMM4DirPath is missing in Directory.Build.props"
    }

    $trimmed = $value.Trim()
    if (-not (Test-Path $trimmed)) {
        Write-DeployWarning "YMM4DirPath does not exist: $trimmed"
        Write-DeployWarning "Please update ymm4-plugin/Directory.Build.props with your YMM4 installation path."
        throw "YMM4DirPath does not exist: $trimmed"
    }

    return $trimmed.TrimEnd('\')
}

function Test-Ymm4Running([string]$Ymm4Dir) {
    $ymm4Exe = Join-Path $Ymm4Dir "YukkuriMovieMaker.exe"
    $processes = Get-Process -Name "YukkuriMovieMaker" -ErrorAction SilentlyContinue
    return ($null -ne $processes -and $processes.Count -gt 0)
}

# Initialize
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$root = $PSScriptRoot | Split-Path -Parent
$pluginRoot = Join-Path $root "ymm4-plugin"
$propsPath = Join-Path $pluginRoot "Directory.Build.props"
$csprojPath = Join-Path $pluginRoot "NLMSlidePlugin.csproj"
$deployLogDir = Join-Path $root "logs\deploy"
New-Item -ItemType Directory -Path $deployLogDir -Force | Out-Null

$deployLog = Join-Path $deployLogDir "$timestamp.log"
$summaryPath = Join-Path $deployLogDir "$timestamp-summary.md"

Write-DeployStep "=== YMM4 Plugin Auto-Deployment ==="
Write-DeployStep "Configuration: $Configuration"
Write-DeployStep "SkipBuild: $SkipBuild"
Write-DeployStep "SkipBackup: $SkipBackup"
Write-DeployStep "Force: $Force"

# Check prerequisites
if (-not (Test-Path $csprojPath)) {
    Write-DeployError "Project file not found: $csprojPath"
    throw "Project file not found: $csprojPath"
}

$dotnetPath = Get-DotnetPath
$ymm4Dir = Get-Ymm4Dir $propsPath

Write-DeployStep "dotnet: $dotnetPath"
Write-DeployStep "YMM4DirPath: $ymm4Dir"

# Check if YMM4 is running
if (Test-Ymm4Running -Ymm4Dir $ymm4Dir) {
    if (-not $Force) {
        Write-DeployWarning "YukkuriMovieMaker is currently running."
        Write-DeployWarning "Please close YMM4 before deploying the plugin, or use -Force to override."
        throw "YMM4 is running. Close it or use -Force."
    }
    else {
        Write-DeployWarning "YMM4 is running, but Force flag is set. Proceeding with deployment."
    }
}

# Build plugin
if (-not $SkipBuild) {
    Write-DeployStep "Building plugin ($Configuration)..."
    & $dotnetPath build $csprojPath -c $Configuration *>&1 | Tee-Object -FilePath $deployLog | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-DeployError "Build failed. See log: $deployLog"
        throw "Build failed. See log: $deployLog"
    }
}
else {
    Write-DeployStep "Skipping build (SkipBuild flag set)."
}

# Locate built DLL
$builtDll = Join-Path $pluginRoot "bin\$Configuration\net9.0-windows\NLMSlidePlugin.dll"
if (-not (Test-Path $builtDll)) {
    Write-DeployError "Built DLL not found: $builtDll"
    throw "Built DLL not found: $builtDll"
}

# Prepare deployment directory
$pluginDeployDir = Join-Path $ymm4Dir "user\plugin\NLMSlidePlugin"
$deployedDll = Join-Path $pluginDeployDir "NLMSlidePlugin.dll"

if (-not (Test-Path $pluginDeployDir)) {
    Write-DeployStep "Creating plugin directory: $pluginDeployDir"
    New-Item -ItemType Directory -Path $pluginDeployDir -Force | Out-Null
}

# Backup existing DLL
if ((Test-Path $deployedDll) -and (-not $SkipBackup)) {
    $backupDir = Join-Path $deployLogDir "backups"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $backupPath = Join-Path $backupDir "NLMSlidePlugin-$timestamp.dll"
    Write-DeployStep "Backing up existing DLL to: $backupPath"
    Copy-Item -Path $deployedDll -Destination $backupPath -Force
}

# Deploy DLL
Write-DeployStep "Deploying DLL..."
Copy-Item -Path $builtDll -Destination $deployedDll -Force

# Verify deployment
if (-not (Test-Path $deployedDll)) {
    Write-DeployError "Deployment failed. DLL not found at: $deployedDll"
    throw "Deployment failed."
}

$builtInfo = Get-Item $builtDll
$deployedInfo = Get-Item $deployedDll
$builtHash = (Get-FileHash $builtDll -Algorithm SHA256).Hash
$deployedHash = (Get-FileHash $deployedDll -Algorithm SHA256).Hash

$hashMatch = ($builtHash -eq $deployedHash)
if (-not $hashMatch) {
    Write-DeployError "Hash mismatch! Built and deployed DLLs differ."
    throw "Hash mismatch after deployment."
}

Write-DeployStep "Deployment successful!"
Write-DeployStep "Built Size: $($builtInfo.Length) bytes"
Write-DeployStep "Deployed Size: $($deployedInfo.Length) bytes"
Write-DeployStep "SHA256: $deployedHash"

# Generate summary
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$summary = @"
# YMM4 Plugin Deployment Summary

- Timestamp(UTC): $utc
- Configuration: $Configuration
- Built DLL: $builtDll
- Built Size: $($builtInfo.Length) bytes
- Deployed DLL: $deployedDll
- Deployed Size: $($deployedInfo.Length) bytes
- SHA256(Built): $builtHash
- SHA256(Deployed): $deployedHash
- Hash Match: $($hashMatch ? "✅ MATCH" : "❌ MISMATCH")

## Next Steps
1. Launch YukkuriMovieMaker.exe
2. Verify NLMSlidePlugin appears in the plugin list
3. Open the CSV import tool from the Tools menu
4. Test CSV import with a sample file

## Rollback
If the deployment causes issues, restore from backup:
``````powershell
# Find latest backup
`$backup = Get-ChildItem "$deployLogDir\backups" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item -Path `$backup.FullName -Destination "$deployedDll" -Force
``````
"@

$summary | Set-Content -Encoding UTF8 $summaryPath
Write-DeployStep "Deployment summary: $summaryPath"

Write-Host "`n✅ YMM4 Plugin deployment completed successfully!" -ForegroundColor Green
