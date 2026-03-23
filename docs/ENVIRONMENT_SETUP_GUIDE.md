# New Environment Setup Guide (v1.1)

最終更新: 2026-03-18

このプロジェクトを別の端末で動作させるためのセットアップ手順です。

## 1. 動作環境の要件 (Prerequisites)

- **OS**: Windows 11 (YMM4 が Windows 専用)
- **Git**: リポジトリのクローン用
- **Python**: 3.11 以上
- **ffmpeg**: パスが通っていること (`ffmpeg -version` で確認)
- **YMM4**: YukkuriMovieMaker4 最新版

## 2. セットアップ手順 (Setup Steps)

### リポジトリの取得

```powershell
git clone <repository_url>
cd NLMandSlideVideoGenerator
```

### Python 環境の構築

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **注意**: 別 PC への移行時や venv を再作成した場合は `pip install -r requirements.txt` を再実行してください。特に `google-genai` (Gemini API SDK) が欠けると、台本構造化・alignment・キーワード抽出が全てモックフォールバックで動作し、品質が大幅に低下します。

### API キーの設定

`.env.example` をコピーして `.env` を作成し、必要な API キーを設定:

```powershell
copy .env.example .env
```

主要な環境変数:

- `GEMINI_API_KEY` — Gemini API (台本構造化・分類・翻訳)
- `PEXELS_API_KEY` — ストック画像検索 (Pexels)
- `PIXABAY_API_KEY` — ストック画像検索 (Pixabay、フォールバック)
- `BRAVE_API_KEY` — Web 検索 (Brave Search API)
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` — YouTube 投稿 (使う場合)

詳細は `docs/api_setup_guide.md` を参照してください。

### YMM4 プラグインの配置

NLMSlidePlugin を YMM4 のプラグインフォルダに配置します。

```powershell
# ビルド & 配置 (PowerShell)
.\scripts\deploy_ymm4_plugin.ps1
```

詳細は `docs/ymm4_export_spec.md` を参照してください。

## 3. アプリの起動 (Running the App)

### CLI (推奨)

```powershell
.\venv\Scripts\Activate.ps1
python scripts/research_cli.py pipeline --topic "テーマ" --auto-images
```

### Web UI (Streamlit)

```powershell
.\venv\Scripts\Activate.ps1
streamlit run src/web/web_app.py
```

## 4. 動作確認

```powershell
# テスト実行
pytest tests/ -q

# 環境チェック
python scripts/check_environment.py
```

## 5. トラブルシューティング (Troubleshooting)

- **テストが失敗する**: `venv` 内の依存が最新か確認 (`pip install -r requirements.txt`)
- **動画が生成されない**: `ffmpeg` のパスを確認してください
- **YMM4連携**: NLMSlidePlugin が YMM4 のプラグインフォルダにあるか確認

詳細は `docs/TROUBLESHOOTING.md` を参照してください。
