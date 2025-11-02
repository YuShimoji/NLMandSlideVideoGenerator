# NLMandSlideVideoGenerator - 最終解決ガイド
# このファイルには完全な解決手順が記載されています

## 🚨 現在の根本問題
- PythonがWindows Storeのリダイレクトになっている
- PowerShellのエンコーディング問題
- スクリプト実行環境の不安定さ

## ✅ 最終解決手順

### ステップ1: Pythonを完全にアンインストール
1. Windows設定 → アプリ → アプリと機能
2. "Python" で検索してすべてアンインストール
3. Windows StoreのPythonアプリも削除

### ステップ2: Pythonを正しくインストール
1. https://www.python.org/downloads/ をブラウザで開く
2. "Download Python 3.11.x" をクリック
3. ダウンロードした `python-3.11.x-amd64.exe` を実行
4. **重要:** インストール時に以下の設定を必ずチェック
   - ✅ Add Python 3.11 to PATH
   - ✅ Install for all users (推奨)
   - その他のオプションはデフォルトでOK

### ステップ3: Python動作確認
1. **新しい**コマンドプロンプトを開く (重要!)
2. 以下のコマンドを実行:

```cmd
python --version
pip --version
```

正しくインストールされていれば以下のように表示される:
```
Python 3.11.x
pip 23.x.x from C:\Python311\Lib\site-packages\pip (python 3.11)
```

### ステップ4: プロジェクト環境構築
1. コマンドプロンプトでプロジェクトフォルダへ移動:

```cmd
cd C:\Users\PLANNER007\NLMandSlideVideoGenerator
```

2. 仮想環境作成:

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

3. 依存関係インストール:

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### ステップ5: テスト実行
1. 基本テスト:

```cmd
python -c "import moviepy; print('MoviePy OK')"
python -c "import requests; print('Requests OK')"
python -c "from PIL import Image; print('Pillow OK')"
```

2. プロジェクトテスト:

```cmd
python test_basic.py
```

### ステップ6: サンプル動画生成
1. 完全な動画生成:

```cmd
python run_modular_demo.py --topic "AI技術の最新動向" --quality 1080p --thumbnail --thumbnail-style modern
```

## 🎯 ワンライナー解決スクリプト

上記の手順が面倒な場合は、以下のスクリプトを新規作成して実行してください:

### setup_final.bat (新規作成)
```batch
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
python test_basic.py

echo ========================================
echo セットアップ完了！
echo ========================================
echo.
echo 動画生成コマンド:
echo python run_modular_demo.py --topic "トピック名" --thumbnail
echo.
pause
```

## 📊 期待される最終結果

正しくセットアップが完了すると、以下のように動作します:

```cmd
# 1. 基本動画生成 (5-10分)
python run_modular_demo.py --topic "Pythonプログラミング"

# 生成されるファイル:
# data/videos/generated_video_xxx.mp4 (720p/1080p)
# data/thumbnails/thumbnail_xxx.png (1280x720)
# data/transcripts/transcript_xxx.json

# 2. 高品質動画生成
python run_modular_demo.py --topic "機械学習入門" --quality 1080p --thumbnail --thumbnail-style educational

# 3. Gemini API連携 (APIキーを.envに設定後)
python run_modular_demo.py --topic "量子コンピューティング" --thumbnail
```

## 🚨 トラブルシューティング

### Q: Pythonインストール後も認識されない
```cmd
# PATH環境変数の確認
echo %PATH%

# Pythonの場所を確認
where python

# 手動でPATHに追加 (一時対応)
set PATH=C:\Python311;%PATH%
```

### Q: pip install が失敗する
```cmd
# プロキシ設定を確認
pip install --proxy http://proxy.company.com:8080 requests

# キャッシュクリア
pip cache purge
```

### Q: 動画生成でエラー
```cmd
# MoviePyのテスト
python -c "import moviepy.editor as mp; print('OK')"

# ffmpeg確認 (MoviePyが必要)
# https://ffmpeg.org/download.html からインストール
```

## 🎯 推奨ワークフロー

1. ✅ Python 3.11 を公式サイトからインストール (PATH追加を忘れずに)
2. ✅ 新しいコマンドプロンプトで `python --version` を確認
3. ✅ `setup_final.bat` を実行して環境構築
4. ✅ `python run_modular_demo.py --topic "テスト"` で動画生成
5. ✅ 生成された動画を `data\videos\` で確認

---

**まずはPythonを正しくインストールしてください。それが解決すればすべてがうまく動作します！**
