@echo off
chcp 65001 > NUL
setlocal enabledelayedexpansion

echo ====================================
echo YMM4 Plugin Build Script
echo ====================================
echo.

if not exist "Directory.Build.props" (
    echo [ERROR] Directory.Build.props not found!
    echo Please run setup_build_props.bat first to configure YMM4 path.
    echo.
    pause
    exit /b 1
)

echo [INFO] Checking .NET SDK...
dotnet --version > NUL 2>&1
if errorlevel 1 (
    echo [ERROR] .NET SDK not found!
    echo Please install .NET 10 SDK from: https://dotnet.microsoft.com/download
    echo.
    pause
    exit /b 1
)

echo [INFO] .NET SDK version:
dotnet --version
echo.

echo [INFO] Building NLMSlidePlugin...
echo.
dotnet build -c Release

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================
echo [SUCCESS] Build completed!
echo ====================================
echo.
echo Next Steps:
echo 1. Launch YMM4
echo 2. Go to Settings ^> Plugins ^> Plugin List
echo 3. Verify "NLM Slide Plugin" appears in the list
echo.
pause
