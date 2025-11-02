>@echo off
chcp 65001 >nul
REM UTF-8 encoding for proper Japanese display
REM サンプル動画生成スクリプト

REM Change to project directory
cd /d "%~dp0"

echo ========================================
echo サンプル動画生成
========================================

REM 仮想環境アクティベート
if not exist venv\Scripts\activate.bat (
    echo ERROR: 仮想環境が見つかりません
    echo 先に setup_quick.bat を実行してください
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo [準備] 出力ディレクトリ作成...
python -c "from config.settings import create_directories; create_directories()" 2>nul

echo.
echo ========================================
echo サンプル1: 基本動画生成（字幕なし）
echo ========================================
python run_modular_demo.py --topic "Python入門" --quality 720p

if errorlevel 1 (
    echo ERROR: サンプル1の生成に失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo サンプル2: サムネイル付き動画
echo ========================================
python run_modular_demo.py --topic "機械学習の基礎" --quality 1080p --thumbnail --thumbnail-style modern

if errorlevel 1 (
    echo ERROR: サンプル2の生成に失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo サンプル3: 教育スタイルのサムネイル
echo ========================================
python run_modular_demo.py --topic "データサイエンス入門" --quality 1080p --thumbnail --thumbnail-style educational

if errorlevel 1 (
    echo ERROR: サンプル3の生成に失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo すべてのサンプル動画生成完了！
echo ========================================
echo.
echo 生成されたファイルは data フォルダに保存されています:
echo.
if exist data\videos\ (
    echo 動画ファイル:
    for %%f in (data\videos\*.mp4) do echo   %%f
)

echo.
if exist data\thumbnails\ (
    echo サムネイルファイル:
    for %%f in (data\thumbnails\*.png) do echo   %%f
)
echo.
echo 完了しました！生成された動画を確認してください。
echo.
pause
