# Quick Start: API Key Setup

最短手順でGemini APIキーを設定し、TASK_003のBLOCKED状態を解除します。

## 前提条件

- Googleアカウント（Google AI Studio用）
- `python-dotenv` インストール済み（`requirements.txt`に含まれています）

## ステップ1: Gemini APIキー取得

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. Googleアカウントでログイン
3. 「Get API Key」または「Create API Key」をクリック
4. 新しいAPIキーが表示されるので、コピーして保存

> [!WARNING]
> APIキーは秘密情報です。他人と共有したり、GitHubにコミットしないでください。

## ステップ2: `.env` ファイル作成

プロジェクトルートディレクトリで以下を実行:

```bash
# .env.example から .env を作成
cp .env.example .env

# Windows (PowerShell) の場合
Copy-Item .env.example .env
```

`.env` ファイルを開いて、以下の行を編集:

```env
# 変更前
GEMINI_API_KEY=your_gemini_api_key_here

# 変更後（実際のAPIキーに置き換える）
GEMINI_API_KEY=AIzaSy... (あなたのAPIキー)
```

## ステップ3: 設定確認

APIキーが正しく設定されているか確認:

```bash
python scripts/verify_api_keys.py
```

**期待される出力**:
```
✅ Gemini API: Connected
   Model: gemini-1.5-flash
   Status: Ready
```

## ステップ4: 動作テスト（オプション）

NotebookLM関連のスモークテストを実行:

```bash
python -m pytest tests/smoke_test_notebook_lm.py -v
```

**期待される結果**:
- `GEMINI_API_KEY` が設定されていれば、実APIを使用してテスト実行
- フォールバック動作テストも引き続きPASS

## トラブルシューティング

### エラー: "GEMINI_API_KEY not found"

**原因**: `.env` ファイルが存在しないか、読み込めていない

**解決方法**:
1. `.env` ファイルがプロジェクトルートに存在するか確認
2. `GEMINI_API_KEY=` の行が正しく記述されているか確認
3. `python-dotenv` がインストールされているか確認: `pip install python-dotenv`

### エラー: "Invalid API key"

**原因**: APIキーが無効または誤っている

**解決方法**:
1. [Google AI Studio](https://aistudio.google.com/app/apikey) で新しいAPIキーを作成
2. `.env` ファイルの `GEMINI_API_KEY` を更新
3. APIキーの前後にスペースや引用符が含まれていないか確認

### エラー: "Quota exceeded"

**原因**: APIの無料枠を超過

**解決方法**:
1. [Google AI Studio](https://aistudio.google.com/) でクォータ使用状況を確認
2. 請求設定を確認（必要に応じて有料プランへ）
3. レート制限を守る（60リクエスト/分）

## 次のステップ

APIキー設定が完了したら、TASK_003をBLOCKED → DONEに更新できます:

1. `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` でStatusを `DONE` に更新
2. NotebookLM機能を使った動画生成パイプラインをテスト
3. 必要に応じてWorkerレポートを作成

## 参考資料

- [API Setup Guide](api_setup_guide.md): 詳細な設定手順
- [Google API Setup](google_api_setup.md): Google Slides/YouTube API設定
- [Gemini API Documentation](https://ai.google.dev/docs)
