# API設定ガイド

## 🔑 必要なAPI認証情報

### ✅ 設定済み
- **Google AI Studio (Gemini API)**: `AIzaSyBjkCSS4DJuajzf9zFfXGJtrrRzTAupdss`
- **YouTube API**: クライアントID・シークレット設定済み
- **Google Slides API**: YouTube APIと同じ認証情報を使用

### 🔧 追加設定が必要

#### 1. 音声生成API（いずれか選択）

**推奨: ElevenLabs**
```bash
# ElevenLabsアカウント作成
https://elevenlabs.io/

# API キー取得後
export ELEVENLABS_API_KEY="your_api_key_here"
```

**代替案: OpenAI**
```bash
# OpenAI Platform
https://platform.openai.com/

export OPENAI_API_KEY="your_api_key_here"
```

**代替案: Azure Speech Services**
```bash
# Azure Portal
https://portal.azure.com/

export AZURE_SPEECH_KEY="your_key_here"
export AZURE_SPEECH_REGION="eastus"
```

## 🚀 セットアップ手順

### 1. 環境変数設定

`.env`ファイルを作成:
```env
# Google AI Studio (Gemini API)
GEMINI_API_KEY=AIzaSyBjkCSS4DJuajzf9zFfXGJtrrRzTAupdss

# YouTube API
YOUTUBE_CLIENT_ID=1066326089631-1i3fsdtksk6p7l5tq52urf41imnkfsm4.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=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

# 音声生成API（選択）
ELEVENLABS_API_KEY=your_elevenlabs_key
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
# 認証テスト実行
python config/api_keys.py
```

## 🧪 API動作テスト

### Gemini API テスト
```python
from src.notebook_lm.gemini_integration import GeminiIntegration
from config.api_keys import api_keys

gemini = GeminiIntegration(api_keys.GEMINI_API_KEY)
# テスト実行
```

### YouTube API テスト
```python
from src.youtube.uploader import YouTubeUploader
from config.api_keys import api_keys

uploader = YouTubeUploader()
auth_result = await uploader.authenticate()
print(f"YouTube認証: {'成功' if auth_result else '失敗'}")
```

### 音声生成API テスト
```python
from src.audio.tts_integration import TTSIntegration
from config.api_keys import api_keys

tts = TTSIntegration({
    "elevenlabs": api_keys.ELEVENLABS_API_KEY,
    "openai": api_keys.OPENAI_API_KEY,
    "azure_speech": api_keys.AZURE_SPEECH_KEY
})

status = tts.get_provider_status()
print("TTS プロバイダー状況:", status)
```

## ⚠️ セキュリティ注意事項

### 1. API キーの保護
- `.env`ファイルを`.gitignore`に追加
- 本番環境では環境変数を使用
- API キーをコードに直接記述しない

### 2. 権限設定
- 必要最小限のスコープのみ許可
- 定期的なキーローテーション
- 使用量監視の設定

### 3. レート制限対応
- **Gemini API**: 60リクエスト/分
- **YouTube API**: 10,000クォータ/日
- **ElevenLabs**: プランに応じて制限

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

**3. 音声生成失敗**
```
解決方法:
- APIキーの確認
- プロバイダーの選択
- ネットワーク接続確認
```

## 📊 API使用量監視

### 推奨監視項目
- **Gemini API**: リクエスト数、トークン使用量
- **YouTube API**: クォータ使用量
- **音声生成API**: 文字数、音声時間

### 監視コマンド
```python
# API使用状況確認
python -c "
from config.api_keys import api_keys
status = api_keys.validate_keys()
print('API状況:', status)
"
```
