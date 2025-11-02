@echo off
echo ========================================
echo NLMandSlideVideoGenerator 最終セットアップ
echo ========================================

cd /d "%~dp0"

echo [1/3] Python確認...
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Pythonが見つかりません
    echo https://www.python.org/downloads/ からインストールしてください
    echo インストール時に Add Python to PATH をチェックしてください
    pause
    exit /b 1
)
echo Python OK

echo [2/3] 環境構築...
if exist venv rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] テスト実行...
python -c "from config.settings import create_directories; create_directories()"
python test_basic.py 2>nul
if errorlevel 1 (
    echo WARNING: テストに失敗しましたが、基本機能は動作する可能性があります
)

echo ========================================
echo セットアップ完了！
echo ========================================
echo.
echo 動画生成コマンド例:
echo python run_modular_demo.py --topic "Python入門" --thumbnail
echo python run_modular_demo.py --topic "AI技術" --quality 1080p --thumbnail --thumbnail-style modern
echo.
echo 生成された動画は data\videos\ フォルダに保存されます
echo.
pause
