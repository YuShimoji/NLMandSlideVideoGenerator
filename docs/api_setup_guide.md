# API設定ガイド

## 🔑 必要なAPI認証情報

### ✅ 設定が必要（実値は書かない）
- **Google AI Studio (Gemini API)**: `GEMINI_API_KEY`
  - Python側: Gemini統合（`src/notebook_lm/gemini_integration.py`）
  - YMM4プラグイン側: 台本テキスト補完・校正（`CsvScriptCompletionPlugin`）
- **Pexels**: `PEXELS_API_KEY` — ストック写真検索 (200 req/hour)
- **Pixabay**: `PIXABAY_API_KEY` — ストック写真検索フォールバック (5000 req/hour)
- **Brave Search**: `BRAVE_API_KEY` — Web検索 ($5/月無料枠)
- **YouTube API**: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`
- **Google Slides API**: `GOOGLE_CLIENT_SECRETS_FILE`, `GOOGLE_OAUTH_TOKEN_FILE`

> **Note**: 音声生成（TTS）は YMM4 内蔵のゆっくりボイスを使用します。外部TTS API（ElevenLabs/OpenAI/Azure）は 2026-03-04 に削除済みです。

## 🚀 セットアップ手順

### 1. 環境変数設定

`.env`ファイルを作成（`.env.example` をコピーして編集）:
```env
# Google AI Studio (Gemini API)
GEMINI_API_KEY=your_gemini_api_key_here

# ストック画像検索
PEXELS_API_KEY=your_pexels_api_key_here
PIXABAY_API_KEY=your_pixabay_api_key_here

# Web検索 (Brave Search API)
BRAVE_API_KEY=your_brave_api_key_here

# YouTube API
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here

```

### 2. Google OAuth設定

**Google Cloud Console**で以下を設定:

1. **プロジェクト作成**
   - プロジェクト名: `nlm-slide-video-generator`

2. **API有効化**
   - YouTube Data API v3 ✅
   - Google Slides API ✅
   - Google Drive API（推奨）

3. **OAuth同意画面設定**
   - アプリケーション名: `NLM Slide Video Generator`
   - スコープ追加:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/presentations`
     - `https://www.googleapis.com/auth/drive.file`

4. **認証情報作成**
   - OAuth 2.0 クライアントID
   - アプリケーションの種類: デスクトップアプリケーション

### 3. 初回認証実行

```python
# API統合テスト実行（キー未設定の場合はスキップされます）
python run_api_test.py
```

## API動作テスト

### Gemini API テスト
```python
from src.notebook_lm.gemini_integration import GeminiIntegration
from config.settings import settings

gemini = GeminiIntegration(settings.GEMINI_API_KEY)
# テスト実行
```

### YouTube API テスト
```python
from src.youtube.uploader import YouTubeUploader

uploader = YouTubeUploader()
auth_result = await uploader.authenticate()
print(f"YouTube認証: {'成功' if auth_result else '失敗'}")
```

### YMM4プラグイン テキスト補完テスト
```powershell
# GEMINI_API_KEY を設定してから .NET テストを実行
$env:GEMINI_API_KEY = "your_key"
dotnet test ymm4-plugin/tests/NLMSlidePlugin.Tests.csproj -c Release --nologo -q
```

## セキュリティ注意事項

### 1. API キーの保護
- `.env`ファイルを`.gitignore`に追加
- 本番環境では環境変数を使用
- API キーをコードに直接記述しない

### 2. 権限設定
- 必要最小限のスコープのみ許可
- 定期的なキーローテーション
- 使用量監視の設定

### 3. レート制限対応
- **Gemini API**: 15リクエスト/分 (無料枠)
- **Pexels**: 200リクエスト/時
- **Pixabay**: 5,000リクエスト/時
- **Brave Search**: $5/月無料枠
- **YouTube API**: 10,000クォータ/日

## 🔍 トラブルシューティング

### よくある問題

**1. YouTube認証エラー**
```
解決方法:
- OAuth同意画面の設定確認
- リダイレクトURIの設定確認
- スコープの設定確認
```

**2. Gemini API制限エラー**
```
解決方法:
- APIキーの有効性確認
- 請求設定の確認
- レート制限の確認
```

**3. YMM4プラグインでGemini APIが動作しない**
```
解決方法:
- システム環境変数にGEMINI_API_KEYが設定されているか確認
- YMM4を再起動（環境変数の再読み込み）
- APIキー未設定時は入力テキストがそのまま返される（フォールバック動作）
```

## 📊 API使用量監視

### 推奨監視項目
- **Gemini API**: リクエスト数、トークン使用量
- **YouTube API**: クォータ使用量

### 監視コマンド
```bash
# API使用状況確認（キー未設定の場合はスキップされます）
python run_api_test.py
```
