param(
    [Parameter(Mandatory=$true, HelpMessage="YMM4 project directory path (e.g. data/ymm4/ymm4_project_20251201_120000)")]
    [string]$ProjectDir,
    
    [Parameter(Mandatory=$false, HelpMessage="Target video output directory")]
    [string]$OutputDir = "data/videos",

    [Parameter(Mandatory=$false, HelpMessage="Delete temporary AHK script and logs after successful copy")]
    [switch]$Cleanup
)

Write-Host "=================================="
Write-Host " RUN_AFTER_YMM4 Post-Processing   "
Write-Host "=================================="

# Directories and paths
$AbsoluteProjectDir = Resolve-Path $ProjectDir -ErrorAction SilentlyContinue

if (-not $AbsoluteProjectDir) {
    Write-Error "Project directory not found: $ProjectDir"
    exit 1
}

$ProjectPath = $AbsoluteProjectDir.Path
Write-Host "Checking YMM4 Project Directory: $ProjectPath"

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    Write-Host "Created output directory: $OutputDir"
}

# Find MP4 files
$mp4Files = Get-ChildItem -Path $ProjectPath -Filter "*.mp4" -File

if ($mp4Files.Count -eq 0) {
    Write-Warning "No MP4 files found in $ProjectPath."
    Write-Warning "Ensure that you have completed the video export in YMM4."
    exit 1
}

$successCount = 0

foreach ($file in $mp4Files) {
    # Move MP4 to final videos folder
    $destination = Join-Path $OutputDir $file.Name
    
    # Check if exists
    if (Test-Path $destination) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $newName = "$($file.BaseName)_$timestamp$($file.Extension)"
        $destination = Join-Path $OutputDir $newName
        Write-Host "File exists. Renaming to $newName"
    }

    Move-Item -Path $file.FullName -Destination $destination -Force
    Write-Host "Moved: $($file.Name) -> $destination" -ForegroundColor Green
    $successCount++
}

# Cleanup optional
if ($Cleanup -and $successCount -gt 0) {
    Write-Host "Cleaning up temporary scripts and logs..."
    
    $ahkScript = Join-Path $ProjectPath "ymm4_automation.ahk"
    $ahkLog = Join-Path $ProjectPath "ymm4_automation.log"
    
    if (Test-Path $ahkScript) { Remove-Item $ahkScript -Force }
    if (Test-Path $ahkLog) { Remove-Item $ahkLog -Force }
    
    Write-Host "Cleanup finished."
}

Write-Host "=================================="
Write-Host " Post-Processing Complete."
Write-Host " Successfully processed $successCount video(s)."
Write-Host " Check $OutputDir for your final video."
Write-Host "=================================="
