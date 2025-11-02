@echo off
chcp 65001 >nul
REM 緊急修復スクリプト

echo ========================================
echo 緊急修復スクリプト
echo ========================================

cd /d "%~dp0"

echo.
echo [1/3] Python確認...
py -3.10 --version 2>nul
if errorlevel 1 (
    echo ERROR: Pythonが見つかりません
    echo PYTHON_INSTALL_GUIDE.md を参照してインストールしてください
    pause
    exit /b 1
)

echo.
echo [2/3] 仮想環境修復...
if exist venv rmdir /s /q venv
py -3.10 -m venv venv
call venv\Scripts\activate.bat

echo.
echo [3/3] 依存関係再インストール...
pip install --upgrade pip
pip install requests
pip install moviepy
pip install pillow
pip install pysrt
pip install python-dotenv
pip install loguru
pip install google-generativeai

echo.
echo ========================================
echo 修復完了！
echo ========================================
echo.
echo 次に実行してください：
echo   .\generate_sample_videos.bat
echo.
pause
