@echo off
title NLM Slide Video Generator
echo.
echo  ========================================
echo   NLM Slide Video Generator v1.0
echo  ========================================
echo.

cd /d "%~dp0desktop"

:: Check if node_modules exists
if not exist "node_modules" (
    echo  [INFO] Installing dependencies...
    call npm install
    echo.
)

echo  [INFO] Starting application...
echo.
call npm start
