# 開発ガイド

## 開発環境のセットアップ

### 1. 必要な環境
- Python 3.9以上
- Git
- 十分なディスク容量（動画ファイル用）

### 2. プロジェクトのクローンとセットアップ
```bash
# プロジェクトディレクトリに移動
cd "c:/Users/thank/Storage/Media Contents Projects/NLMandSlideVideoGenerator"

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
cp .env.example .env

# API設定ファイル作成
cp config/api_keys.py.example config/api_keys.py
```

### 4. API キーの設定
`config/api_keys.py` に以下のAPI キーを設定：
- YouTube API キー
- Google API キー（将来用）
- OpenAI API キー（オプション）

## 開発フロー

### 1. ブランチ戦略
- `main`: 本番用ブランチ
- `develop`: 開発用ブランチ
- `feature/*`: 機能開発用ブランチ
- `hotfix/*`: 緊急修正用ブランチ

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
1. 機能ブランチ作成
2. 実装・テスト
3. コードレビュー
4. マージ

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

### 個別モジュールテスト
```bash
# NotebookLMテスト
pytest tests/test_notebook_lm.py

# スライド生成テスト
pytest tests/test_slides.py

# 動画編集テスト
pytest tests/test_video_editor.py

# YouTubeテスト
pytest tests/test_youtube.py
```

## コード品質管理

### 1. フォーマッター
```bash
# Blackでフォーマット
black src/ tests/

# isortでimport整理
isort src/ tests/
```

### 2. リンター
```bash
# flake8でリント
flake8 src/ tests/

# mypyで型チェック
mypy src/
```

### 3. pre-commitフック
```bash
# pre-commitインストール
pre-commit install

# 手動実行
pre-commit run --all-files
```

## デバッグ

### 1. ログ設定
```python
from loguru import logger

# デバッグレベル設定
logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

### 2. 環境変数でのデバッグ
```bash
# デバッグモード有効
export DEBUG=true

# ログレベル設定
export LOG_LEVEL=DEBUG
```

### 3. テスト用データ
```bash
# テスト用ディレクトリ作成
python -c "from config.settings import create_directories; create_directories()"
```

## パフォーマンス最適化

### 1. 動画処理の最適化
- 並列処理の活用
- メモリ使用量の監視
- 一時ファイルの適切な管理

### 2. API呼び出しの最適化
- レート制限の遵守
- 適切なリトライ処理
- キャッシュの活用

### 3. ファイル管理
- 不要ファイルの自動削除
- ディスク容量の監視
- 圧縮の活用

## トラブルシューティング

### よくある問題

#### 1. MoviePyのインストールエラー
```bash
# ffmpegのインストール
# Windows: https://ffmpeg.org/download.html からダウンロード
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
```

#### 2. Google APIの認証エラー
- API キーの確認
- OAuth設定の確認
- 権限スコープの確認

#### 3. メモリ不足エラー
- 動画解像度の調整
- 処理の分割実行
- 一時ファイルの削除

#### 4. ファイルパスエラー
- パス区切り文字の確認
- 絶対パスの使用
- 権限の確認

### ログの確認
```bash
# アプリケーションログ
tail -f logs/app.log

# エラーログのみ
grep "ERROR" logs/app.log
```

## 本番環境への展開

### 1. 環境変数の設定
```bash
# 本番用設定
export DEBUG=false
export LOG_LEVEL=INFO
export DATABASE_URL="postgresql://..."
```

### 2. 依存関係の確認
```bash
# セキュリティチェック
pip-audit

# 依存関係の更新
pip-compile requirements.in
```

### 3. 監視の設定
- アプリケーションメトリクス
- エラー率の監視
- リソース使用量の監視

## 貢献ガイドライン

### 1. Issue作成
- 明確なタイトル
- 詳細な説明
- 再現手順（バグの場合）
- 期待する動作

### 2. Pull Request
- 関連するIssueの参照
- 変更内容の説明
- テストの追加
- ドキュメントの更新

### 3. コードレビュー
- 機能の正確性
- パフォーマンス
- セキュリティ
- 保守性

## 参考資料

### 技術ドキュメント
- [MoviePy Documentation](https://moviepy.readthedocs.io/)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Google Slides API](https://developers.google.com/slides)

### ベストプラクティス
- [Python Code Style](https://pep8.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [Semantic Versioning](https://semver.org/)

## サポート

### 質問・相談
- GitHub Issues
- 開発チーム内での相談
- ドキュメントの確認

### バグ報告
1. 現象の詳細記録
2. 再現手順の整理
3. 環境情報の収集
4. Issueの作成
