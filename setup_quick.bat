>@echo off
chcp 65001 >nul
REM UTF-8 encoding for proper Japanese display
REM NLMandSlideVideoGenerator Setup Script

echo ========================================
echo NLMandSlideVideoGenerator セットアップ
echo ========================================

REM Change to project directory
cd /d "%~dp0"

echo.
echo [1/6] Python確認中...
py -3.10 --version 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.10以上が見つかりません
    echo.
    echo 以下の手順でPythonをインストールしてください：
    echo 1. https://www.python.org/downloads/ を開く
    echo 2. "Download Python 3.11.x" をクリック
    echo 3. インストール時に "Add Python to PATH" にチェック
    echo 4. インストール完了後、このスクリプトを再実行
    pause
    exit /b 1
)
echo Pythonが見つかりました
py -3.10 --version

echo.
echo [2/6] 仮想環境作成...
if exist venv rmdir /s /q venv
py -3.10 -m venv venv
if errorlevel 1 (
    echo ERROR: 仮想環境の作成に失敗しました
    pause
    exit /b 1
)
echo 仮想環境作成完了

echo.
echo [3/6] 仮想環境アクティベート...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

echo.
echo [4/6] pipアップグレード...
python -m pip install --upgrade pip --quiet

echo.
echo [5/6] 依存関係インストール...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: 依存関係のインストールに失敗しました
    echo インターネット接続を確認してください
    pause
    exit /b 1
)

echo.
echo [6/6] ディレクトリ作成...
python -c "from config.settings import create_directories; create_directories()" 2>nul

echo.
echo ========================================
echo ✅ セットアップ完了！
echo ========================================
echo.
echo 次に以下のコマンドを実行してください：
echo   .\generate_sample_videos.bat
echo.
echo これで3つのサンプル動画が自動生成されます。
echo.
pause
