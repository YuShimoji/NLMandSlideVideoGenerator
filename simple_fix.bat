@echo off
REM シンプル修復スクリプト（文字化け対策）
REM UTF-8対応で作成

echo ========================================
echo NLMandSlideVideoGenerator シンプル修復
echo ========================================

cd /d "%~dp0"

echo.
echo [1/4] Python確認...
python --version
if errorlevel 1 (
    echo ERROR: Pythonが見つかりません
    echo PYTHON_INSTALL_GUIDE.md を参照してください
    pause
    exit /b 1
)

echo.
echo [2/4] 仮想環境作成...
if exist venv rmdir /s /q venv
python -m venv venv
if errorlevel 1 (
    echo ERROR: 仮想環境作成失敗
    pause
    exit /b 1
)

echo.
echo [3/4] 仮想環境アクティベート...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: アクティベート失敗
    pause
    exit /b 1
)

echo.
echo [4/4] 依存関係インストール...
python -m pip install --upgrade pip
pip install requests moviepy pillow pysrt python-dotenv loguru google-generativeai
if errorlevel 1 (
    echo ERROR: インストール失敗
    pause
    exit /b 1
)

echo.
echo ========================================
echo 修復完了！
echo ========================================
echo.
echo 次に実行: .\generate_sample_videos.bat
echo.
pause
