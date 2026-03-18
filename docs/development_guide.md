# 開発ガイド

最終更新: 2026-03-18

## 開発環境のセットアップ

### 1. 必要な環境
- Python 3.11以上
- Git
- Windows 11 (YMM4 が Windows 専用)
- 十分なディスク容量（動画ファイル用）

### 2. プロジェクトのクローンとセットアップ
```bash
# プロジェクトディレクトリに移動
cd "<repo_root>"

# 仮想環境作成
python -m venv venv

# 仮想環境アクティベート（Windows）
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 3. 設定ファイルの準備
```bash
# 環境変数ファイル作成
copy .env.example .env
```

### 4. API キーの設定
`.env` に必要なAPI キーを設定：
- `GEMINI_API_KEY` — 台本生成・セグメント分類・キーワード抽出・翻訳・台本補完
- `PEXELS_API_KEY` — ストック写真検索 (Pexels)
- `PIXABAY_API_KEY` — ストック写真検索 (Pixabay、フォールバック)
- `BRAVE_API_KEY` — Web検索 (Brave Search API)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` — YouTube投稿 (アップロードを使う場合)

詳細は `docs/api_setup_guide.md` を参照してください。

**注**: 外部TTS連携コードは 2026-03-04 に全削除されました。音声生成は YMM4 内蔵ゆっくりボイスのみを使用してください。

## 開発フロー

### 1. ブランチ戦略
- trunk-based development: `master` ブランチのみ
- 機能開発・修正はすべて `master` に直接コミット

### 2. コミット規約
```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント更新
style: コードスタイル修正
refactor: リファクタリング
test: テスト追加・修正
chore: その他の変更
```

### 3. 開発手順
1. 実装・テスト
2. `pytest tests/` で全テスト通過を確認
3. コミット・プッシュ

### 4. 手動E2Eワークフローの確認

- ユーザー視点の手動ワークフロー全体像は `docs/user_guide_manual_workflow.md` を参照してください。
- 制作パス: **CSV → YMM4（NLMSlidePlugin でインポート → 音声生成 → 動画レンダリング）**。YMM4 が最終レンダラー。
- 新機能の開発後は、**CSV → YMM4** フローで動作確認を行ってください（YMM4 GUI 操作のため自動テスト不可）。

## テスト実行

### 基本テスト
```bash
# 全テスト実行
pytest tests/

# 特定のテストファイル実行
pytest tests/test_basic.py

# カバレッジ付きテスト
pytest --cov=src tests/
```

### 主要テストファイル
```bash
# Gemini統合テスト
pytest tests/test_gemini_integration.py

# スライド生成テスト
pytest tests/test_slide_builder.py

# ビジュアルリソーステスト
pytest tests/test_stock_image_client.py tests/test_ai_image_provider.py tests/test_resource_orchestrator.py

# YouTube投稿テスト
pytest tests/test_sp038_youtube_publish.py

# パイプライン統合テスト
pytest tests/test_research_pipeline.py tests/test_pipeline_integration.py

# スタイルテンプレートテスト
pytest tests/test_style_template.py
```

## コード品質管理

### 1. リンター
```bash
# ruffでリント
ruff check src/

# mypyで型チェック
mypy src/ --config-file mypy.ini --ignore-missing-imports
```

### 2. CI パイプライン
`.github/workflows/ci-main.yml` で以下を自動実行:
- pytest (全テスト)
- mypy (型チェック)
- ruff (リント)
- ドキュメントコマンド参照チェック (`scripts/check_doc_command_references.py`)
- .NET ビルド (`ymm4-plugin/`)

## デバッグ

### 1. ログ設定
```python
from src.core.logger import SimpleLogger

logger = SimpleLogger(__name__)
logger.info("...")
logger.error("...")
```

### 2. 環境変数でのデバッグ
```bash
# デバッグモード有効
set DEBUG=true

# ログレベル設定
set LOG_LEVEL=DEBUG
```

### 3. テスト用データ
```bash
# テスト用ディレクトリ作成
python -c "from config.settings import create_directories; create_directories()"
```

## パフォーマンス最適化

### 1. API呼び出しの最適化
- レート制限の遵守 (Pexels 200req/h, Pixabay 5000req/h, Gemini 15req/min)
- 指数バックオフリトライ (1s→2s→4s)
- MD5ハッシュベースキャッシュ (AI生成画像)

### 2. ファイル管理
- PipelineState で途中再開可能 (`--resume`)
- 不要な一時ファイルの管理

## トラブルシューティング

### よくある問題

#### 1. YMM4プラグインの動作確認

YMM4 で NLMSlidePlugin が認識されない場合、プラグインDLLの配置場所を確認してください。
詳細は `docs/ymm4_export_spec.md` を参照。

#### 2. Google APIの認証エラー
- API キーの確認
- OAuth設定の確認
- 権限スコープの確認

#### 3. ファイルパスエラー
- Windows パス区切り文字の確認
- 絶対パスの使用

詳細なトラブルシューティングは `docs/TROUBLESHOOTING.md` を参照してください。

## 参考資料

- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Gemini API](https://ai.google.dev/docs)
- [Pexels API](https://www.pexels.com/api/documentation/)
- [Pixabay API](https://pixabay.com/api/docs/)
- [Brave Search API](https://api.search.brave.com/app/documentation)
