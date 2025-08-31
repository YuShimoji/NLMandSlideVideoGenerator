# NLMandSlideVideoGenerator

YouTube解説動画自動化システム (NLMandSlideVideoGenerator)

## プロジェクト概要

このプロジェクトは、YouTubeの解説動画制作プロセスを自動化するシステムです。NotebookLMとGoogle Slideを活用し、ニュース記事やトピックから高品質な解説動画を自動生成します。

## システム構成

### 1. 入力フェーズ
- ニュース記事のURLまたは調査トピックを入力
- NotebookLMによる関連ソース（最大10件）の自動収集

### 2. 音声生成フェーズ
- NotebookLMのラジオ風音声解説機能を使用
- 生成された音声の自動ダウンロード
- 音声の文字起こしによる台本生成

### 3. スライド生成フェーズ
- Google Slideの「スライド作成サポート」機能を活用
- 台本を適切に分割してスライド生成
- 文字数制限に応じた要点抽出機能

### 4. 動画編集フェーズ
- 日本語字幕の自動付与
- スライド画像のリッチエフェクト（ズーム、パン効果）
- 最終動画の生成

### 5. アップロードフェーズ
- YouTube APIを使用した自動アップロード
- 概要欄の自動生成と設定
- 投稿予約機能

## 技術仕様

### 開発言語
- Python 3.9+

### 主要ライブラリ
- `google-api-python-client` - YouTube API
- `moviepy` - 動画編集
- `pillow` - 画像処理
- `requests` - HTTP通信
- `beautifulsoup4` - Webスクレイピング
- `openai` - AI機能（必要に応じて）

### API要件
- YouTube Data API v3
- Google Slides API（将来的な自動化用）

## プロジェクト構造

```
NLMandSlideVideoGenerator/
├── README.md
├── requirements.txt
├── config/
│   ├── settings.py
│   └── api_keys.py.example
├── src/
│   ├── __init__.py
│   ├── notebook_lm/
│   │   ├── __init__.py
│   │   ├── source_collector.py
│   │   ├── audio_generator.py
│   │   └── transcript_processor.py
│   ├── slides/
│   │   ├── __init__.py
│   │   ├── slide_generator.py
│   │   └── content_splitter.py
│   ├── video_editor/
│   │   ├── __init__.py
│   │   ├── subtitle_generator.py
│   │   ├── effect_processor.py
│   │   └── video_composer.py
│   ├── youtube/
│   │   ├── __init__.py
│   │   ├── uploader.py
│   │   └── metadata_generator.py
│   └── main.py
├── data/
│   ├── audio/
│   ├── slides/
│   ├── videos/
│   └── transcripts/
├── tests/
│   ├── __init__.py
│   ├── test_notebook_lm.py
│   ├── test_slides.py
│   ├── test_video_editor.py
│   └── test_youtube.py
└── docs/
    ├── api_reference.md
    ├── user_guide.md
    └── development_guide.md
```

## 使用方法

### 基本的な使用方法
```bash
python src/main.py --topic "調査したいトピック" --output-dir "出力ディレクトリ"
```

### 詳細オプション
```bash
python src/main.py \
  --topic "AI技術の最新動向" \
  --max-slides 20 \
  --video-quality 1080p \
  --upload-schedule "2024-01-01 12:00" \
  --private-upload
```

## 設定

### API キーの設定
1. `config/api_keys.py.example` を `config/api_keys.py` にコピー
2. 必要なAPI キーを設定

```python
# YouTube API
YOUTUBE_API_KEY = "your_youtube_api_key"
YOUTUBE_CLIENT_ID = "your_client_id"
YOUTUBE_CLIENT_SECRET = "your_client_secret"

# その他のAPI設定
OPENAI_API_KEY = "your_openai_key"  # オプション
```

## 開発ガイドライン

### コーディング規約
- PEP 8準拠
- 型ヒントの使用を推奨
- docstringの記述必須
- 単体テストの実装必須

### 品質管理
- Black（コードフォーマッター）
- isort（import整理）
- flake8（リンター）
- mypy（型チェック）

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 注意事項

- NotebookLMの利用には適切な利用規約の遵守が必要
- YouTube APIの利用制限に注意
- 著作権に配慮したコンテンツ生成を心がける

🎬 **YouTube解説動画の自動生成システム**

NotebookLMの代替としてGoogle AI Studio Gemini APIを活用し、スライド生成から動画編集、YouTube投稿まで完全自動化するPythonアプリケーションです。

## ✨ 主な機能

- 📝 **AI台本生成** - Gemini APIによる高品質なスクリプト作成
- 🎵 **多言語音声合成** - ElevenLabs、OpenAI、Azure等の複数TTS対応
- 🎨 **自動スライド生成** - Google Slides APIによるプレゼンテーション作成
- 🎞️ **動画編集** - MoviePyによる字幕付き動画合成
- 📺 **YouTube自動投稿** - メタデータ管理とサムネイル設定

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# リポジトリクローン
git clone https://github.com/yourusername/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator

# 自動セットアップ実行
python setup_environment.py
```

### 2. API認証設定

```bash
# 環境変数ファイル作成
cp .env.example .env

# .envファイルを編集してAPI認証情報を設定
# 詳細は docs/api_setup_guide.md を参照
```

### 3. 統合テスト実行

```bash
# API連携テスト
python test_api_integration.py

# デモ実行
python test_execution_demo.py
```

### 4. 本格運用開始

```bash
# ヘルプ表示
python main.py --help

# 動画生成実行
python main.py --topic "AI技術の最新動向" --duration 300
```

## 📋 必要なAPI認証情報

| サービス | 必要な認証情報 | 用途 |
|---------|---------------|------|
| **Google AI Studio** | `GEMINI_API_KEY` | スクリプト生成 |
| **YouTube API** | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` | 動画投稿 |
| **Google Slides API** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | スライド作成 |
| **音声生成API** | 各プロバイダーのAPIキー | 音声合成 |

## 🏗️ システム構成

```
src/
├── notebook_lm/          # Gemini API連携
│   ├── gemini_integration.py
│   └── audio_generator.py
├── slides/               # スライド生成
│   ├── slide_generator.py
│   └── content_splitter.py
├── audio/                # 音声処理
│   └── tts_integration.py
├── video_editor/         # 動画編集
│   ├── video_composer.py
│   ├── subtitle_generator.py
│   └── effect_processor.py
└── youtube/              # YouTube連携
    └── uploader.py
```

## 🧪 テスト

```bash
# 基本テスト
python -m pytest tests/

# モックテスト
python test_simple_mock.py

# API統合テスト
python test_api_integration.py
```

## 📚 ドキュメント

- [API設定ガイド](docs/api_setup_guide.md)
- [システム仕様書](docs/system_architecture.md)
- [開発ガイド](docs/development_guide.md)
- [プロジェクト完成報告](docs/project_completion_report.md)

## 🔧 技術スタック

- **Python 3.8+**
- **Google AI Studio Gemini API** - AI台本生成
- **YouTube Data API v3** - 動画投稿
- **Google Slides API** - プレゼンテーション作成
- **MoviePy** - 動画編集
- **複数TTS API** - 音声合成

## 🛡️ セキュリティ

- 環境変数による認証情報管理
- `.env`ファイルはGitで管理対象外
- APIキーの最小権限設定推奨
- 定期的なキーローテーション実施

## 📈 パフォーマンス

- 非同期処理による高速化
- API レート制限対応
- メモリ効率的な動画処理
- バッチ処理による大量生成対応

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチ作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエスト作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🆘 サポート

- 📖 [ドキュメント](docs/)
- 🐛 [Issues](https://github.com/yourusername/NLMandSlideVideoGenerator/issues)
- 💬 [Discussions](https://github.com/yourusername/NLMandSlideVideoGenerator/discussions)

## 🎯 ロードマップ

- [ ] リアルタイム動画生成
- [ ] 多言語字幕対応
- [ ] AI画像生成統合
- [ ] ライブ配信対応
- [ ] Web UI実装

---

**作成者**: [Your Name](https://github.com/yourusername)  
**最終更新**: 2025年8月31日
