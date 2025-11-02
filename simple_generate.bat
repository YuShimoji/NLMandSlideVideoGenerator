@echo off
REM シンプル動画生成スクリプト
cd /d "%~dp0"

echo ========================================
echo サンプル動画生成
echo ========================================

if not exist venv\Scripts\activate.bat (
    echo ERROR: 仮想環境が見つかりません
    echo 先に simple_fix.bat を実行してください
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo [準備] ディレクトリ作成...
python -c "from config.settings import create_directories; create_directories()"

echo.
echo ========================================
echo サンプル1: 基本動画生成
echo ========================================
python run_modular_demo.py --topic "Python入門" --quality 720p
if errorlevel 1 (
    echo ERROR: サンプル1失敗
    pause
    exit /b 1
)

echo.
echo ========================================
echo サンプル2: モダンサムネイル付き動画
echo ========================================
python run_modular_demo.py --topic "機械学習の基礎" --quality 1080p --thumbnail --thumbnail-style modern
if errorlevel 1 (
    echo ERROR: サンプル2失敗
    pause
    exit /b 1
)

echo.
echo ========================================
echo サンプル3: 教育スタイルサムネイル
echo ========================================
python run_modular_demo.py --topic "データサイエンス入門" --quality 1080p --thumbnail --thumbnail-style educational
if errorlevel 1 (
    echo ERROR: サンプル3失敗
    pause
    exit /b 1
)

echo.
echo ========================================
echo すべてのサンプル動画生成完了！
echo ========================================
echo.
echo 生成されたファイル:
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
echo 完了しました！
echo.
pause
