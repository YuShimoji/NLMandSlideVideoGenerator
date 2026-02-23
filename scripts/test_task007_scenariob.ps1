param(
    [string]$ProjectRoot = ".",
    [string]$Configuration = "Release",
    [switch]$SkipBuild,
    [switch]$LaunchYmm4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[TASK_007] $Message"
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
        throw "YMM4DirPath does not exist: $trimmed"
    }

    return $trimmed.TrimEnd('\')
}

function Test-PluginContractsFromSource([string]$ToolSourcePath) {
    if (-not (Test-Path $ToolSourcePath)) {
        throw "Tool source not found: $ToolSourcePath"
    }

    $content = Get-Content -Raw -Encoding UTF8 $ToolSourcePath
    if ($content -notmatch "class\s+CsvImportToolPlugin\s*:\s*IToolPlugin") {
        throw "CsvImportToolPlugin : IToolPlugin declaration is missing."
    }
    if ($content -notmatch "class\s+CsvImportToolViewModel\s*:\s*INotifyPropertyChanged") {
        throw "CsvImportToolViewModel : INotifyPropertyChanged declaration is missing."
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$root = Resolve-Path $ProjectRoot
$pluginRoot = Join-Path $root "ymm4-plugin"
$propsPath = Join-Path $pluginRoot "Directory.Build.props"
$csprojPath = Join-Path $pluginRoot "NLMSlidePlugin.csproj"
$artifactDir = Join-Path $root ("logs\task007_scenariob\" + $timestamp)
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

$dotnetPath = Get-DotnetPath
$ymm4Dir = Get-Ymm4Dir $propsPath

$buildLog = Join-Path $artifactDir "build.log"
$summaryPath = Join-Path $artifactDir "summary.md"

if (-not (Test-Path $csprojPath)) {
    throw "Project file not found: $csprojPath"
}

Write-Step "dotnet: $dotnetPath"
Write-Step "YMM4DirPath: $ymm4Dir"

if (-not $SkipBuild) {
    Write-Step "Building plugin ($Configuration)..."
    & $dotnetPath build $csprojPath -c $Configuration *>&1 | Tee-Object -FilePath $buildLog | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed. See log: $buildLog"
    }
}

$builtDll = Join-Path $pluginRoot ("bin\" + $Configuration + "\net9.0-windows\NLMSlidePlugin.dll")
$deployedDll = Join-Path $ymm4Dir "user\plugin\NLMSlidePlugin\NLMSlidePlugin.dll"
$toolSource = Join-Path $pluginRoot "ToolPlugin\CsvImportToolPlugin.cs"

if (-not (Test-Path $builtDll)) {
    throw "Built dll not found: $builtDll"
}
if (-not (Test-Path $deployedDll)) {
    throw "Deployed dll not found: $deployedDll"
}

$builtInfo = Get-Item $builtDll
$deployedInfo = Get-Item $deployedDll
$builtHash = (Get-FileHash $builtDll -Algorithm SHA256).Hash
$deployedHash = (Get-FileHash $deployedDll -Algorithm SHA256).Hash

Write-Step "Checking plugin contracts..."
Test-PluginContractsFromSource -ToolSourcePath $toolSource

if ($LaunchYmm4) {
    $ymm4Exe = Join-Path $ymm4Dir "YukkuriMovieMaker.exe"
    if (Test-Path $ymm4Exe) {
        Write-Step "Launching YMM4..."
        Start-Process -FilePath $ymm4Exe | Out-Null
    }
}

$hashState = if ($builtHash -eq $deployedHash) { "MATCH" } else { "DIFF" }
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$summary = @"
# TASK_007 ScenarioB AutoCheck

- Timestamp(UTC): $utc
- Dotnet: $dotnetPath
- Configuration: $Configuration
- Built DLL: $builtDll
- Built Size: $($builtInfo.Length)
- Deployed DLL: $deployedDll
- Deployed Size: $($deployedInfo.Length)
- SHA256(Built): $builtHash
- SHA256(Deployed): $deployedHash
- Hash Match: $hashState
- Contract(Source): CsvImportToolPlugin implements IToolPlugin = PASS
- Contract(Source): CsvImportToolViewModel implements INotifyPropertyChanged = PASS

## Next Manual Checks
1. Open YMM4 and confirm NLMSlidePlugin in plugin list.
2. Open tool menu and run CSV timeline import.
3. Confirm timeline placement and audio/text sync.
"@

$summary | Set-Content -Encoding UTF8 $summaryPath
Write-Step "AutoCheck completed. Summary: $summaryPath"
