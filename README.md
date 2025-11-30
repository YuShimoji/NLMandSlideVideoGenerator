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

### 方法A: APIなしで今すぐ試す（推奨）

**サンプルファイルを使って、5分で動画生成を体験できます。**

```bash
# 1. リポジトリクローン & 依存関係インストール
git clone https://github.com/yourusername/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator
pip install -r requirements.txt

# 2. サンプル音声を生成（無音のテスト用WAV）
python scripts/generate_sample_audio.py

# 3. 動画生成を実行
python scripts/run_csv_pipeline.py \
  --csv samples/basic_dialogue/timeline.csv \
  --audio-dir samples/basic_dialogue/audio \
  --topic "AI技術解説サンプル"

# 4. 出力確認
# data/videos/ に動画が出力されます
```

**Web UIを使う場合:**
```bash
streamlit run src/web/web_app.py
# ブラウザで「CSV Pipeline」ページを選択
```

> 📖 詳細は [手動素材ワークフローガイド](docs/user_guide_manual_workflow.md) を参照

---

### 方法B: フルセットアップ（API連携あり）

#### 1. 環境セットアップ

```bash
# リポジトリクローン
git clone https://github.com/yourusername/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator

# 自動セットアップ実行
python setup_environment.py
```

#### 2. API認証設定

```bash
# 環境変数ファイル作成
cp .env.example .env

# .envファイルを編集してAPI認証情報を設定
# 主要項目（抜粋）:
#   GEMINI_API_KEY=...
#   TTS_PROVIDER=none|elevenlabs|openai|azure|google_cloud
#   ELEVENLABS_API_KEY=... (必要に応じて ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL)
#   OPENAI_API_KEY=... (必要に応じて OPENAI_TTS_MODEL, OPENAI_TTS_VOICE, OPENAI_TTS_FORMAT)
#   AZURE_SPEECH_KEY=..., AZURE_SPEECH_REGION=... (必要に応じて AZURE_SPEECH_VOICE)
#   GOOGLE_CLIENT_SECRETS_FILE=./google_client_secret.json
#   GOOGLE_OAUTH_TOKEN_FILE=./token.json
# 詳細は docs/api_setup_guide.md を参照
```

### 3. 統合テスト実行

```bash
# API連携テスト（モック中心、実APIキー未設定でも可）
python test_api_integration.py

# デモ実行
python test_execution_demo.py
```

### 4. 本格運用開始

```bash
# ヘルプ表示
python main.py --help

# 動画生成実行（Gemini+TTS を使用する場合は .env にキー設定 & TTS_PROVIDER を指定）
python main.py --topic "AI技術の最新動向" --duration 300

# モジュラーパイプラインのデモ（Gemini+TTS と Slides 画像エクスポートに対応）
python run_modular_demo.py --topic "AI技術の最新動向" --quality 1080p
```

## 🧩 モジュラーパイプラインの使い方

実装を疎結合化したモジュラーパイプラインを追加しました。依存性注入により各役割（ソース収集/音声/台本/スライド/合成/メタデータ/アップロード）を差し替え可能です。

### デモ実行

```bash
python run_modular_demo.py --topic "AI技術の最新動向" --quality 1080p

# アップロードまで実行したい場合（認証設定が必要）
# python run_modular_demo.py --topic "AI技術の最新動向" --quality 1080p --upload --public --thumbnail --thumbnail-style modern
```

生成物は `data/` 配下に出力されます。

### 追加ファイル
- `src/core/interfaces.py` — 各モジュールのProtocolインターフェイス
- `src/core/pipeline.py` — 依存性注入可能なモジュラーパイプライン
- `run_modular_demo.py` — モジュラーパイプラインのデモ実行スクリプト

## 🛠️ OpenSpec開発ワークフロー

プロジェクトはOpenSpec（オープン仕様言語）に基づく構造化開発を採用しています。新機能開発時は以下の手順で進めます。

### コンポーネント開発手順

```bash
# 1. OpenSpec仕様定義
# docs/openspec_components.md に新規コンポーネントを定義

# 2. インターフェース生成
python scripts/generate_interfaces.py --spec docs/openspec_components.md --component YourComponent

# 3. 実装作成
# 生成されたインターフェースを実装

# 4. 仕様検証
python scripts/validate_openspec.py --component YourComponent

# 5. ドキュメント生成
python scripts/generate_docs.py

# 6. テスト実行
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### OpenSpecツール

- `scripts/validate_openspec.py` — コンポーネント仕様検証
- `scripts/generate_interfaces.py` — インターフェース自動生成
- `scripts/generate_docs.py` — ドキュメント自動生成

### 仕様遵守の重要性

OpenSpecにより以下の品質が保証されます：
- **インターフェース一貫性**: 全実装が同じ契約を満たす
- **自動検証**: 実装の仕様準拠を自動チェック
- **ドキュメント同期**: コードとドキュメントの自動同期
- **交換可能性**: コンポーネントのプラグイン可能交換

詳細は [OpenSpec開発ガイド](docs/openspec_guide.md) を参照してください。

## 🪟 Windows 環境でのUnicode表示について

Windowsコンソールの既定コードページ（cp932）で絵文字などの出力時に `UnicodeEncodeError` が発生する問題に対応しました。以下のスクリプトでは標準出力/標準エラーをUTF-8に再設定しています。

- `run_api_test.py`
- `run_debug_test.py`
- `test_api_integration.py`
- `test_execution_demo.py`
- `test_simple_mock.py`

サブプロセス実行時も `encoding='utf-8', errors='replace'` を設定済みです。追加で問題が出る場合は、以下も有効です。

- `PYTHONIOENCODING=utf-8` 環境変数の利用
- Windows Terminal で UTF-8 を使用

## 🔁 後方互換のための変更点

- `slides/slide_generator.py`
  - `SlideInfo`: 旧フィールド `layout`/`duration` を `layout_type`/`estimated_duration` にマッピング（`__post_init__`）
  - `SlidesPackage`: `presentation_id`/`title` を省略可能に
  - テスト用 `create_slides_from_content()` を用意
- `youtube/uploader.py`
  - `UploadResult.uploaded_at` を Optional[datetime] に
- `youtube/metadata_generator.py`
  - `VideoMetadata` に `language`/`privacy_status` を Optional で追加
  - `thumbnail_suggestions` を Optional[List[str]] に
- `notebook_lm/audio_generator.py`
  - `AudioInfo.language` を設定（`settings.YOUTUBE_SETTINGS.default_audio_language`）

これらにより、既存のテスト・デモスクリプトとの後方互換性が維持されます。

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

### ユーザー向け
- [手動素材ワークフローガイド](docs/user_guide_manual_workflow.md) - **APIなしで動画生成**
- [CSV入力フォーマット仕様](docs/spec_csv_input_format.md) - CSV/WAVの準備方法
- [サンプルファイル](samples/README.md) - すぐに試せるサンプル

### セットアップ
- [API設定ガイド](docs/api_setup_guide.md)
- [Google API設定](docs/google_api_setup.md)
- [環境チェック](scripts/check_environment.py) - `python scripts/check_environment.py`

### 開発者向け
- [システム仕様書](docs/system_architecture.md)
- [開発ガイド](docs/development_guide.md)
- [Transcript I/O仕様](docs/spec_transcript_io.md)
- [YMM4エクスポート仕様](docs/ymm4_export_spec.md)
- [バックログ](docs/backlog.md)

### OpenSpec
- [OpenSpec開発ガイド](docs/openspec_guide.md)
- [OpenSpecコンポーネント仕様](docs/openspec_components.md)
- [OpenSpec開発ワークフロー](docs/openspec_workflow.md)

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

### 完了済み ✅
- [x] CSVタイムライン → 動画生成パイプライン
- [x] Web UI実装（Streamlit）
- [x] YMM4エクスポート連携
- [x] フォールバック戦略（MoviePy/FFmpeg）
- [x] 長文自動分割機能

### 進行中 🚧
- [ ] Google Slides API完全連携
- [ ] NotebookLM代替（Gemini + TTS統合）

### 将来 📋
- [ ] リアルタイム動画生成
- [ ] 多言語字幕対応
- [ ] AI画像生成統合
- [ ] ライブ配信対応

---

**最終更新**: 2025年12月1日
