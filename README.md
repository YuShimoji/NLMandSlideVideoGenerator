# NLMandSlideVideoGenerator

YouTube解説動画自動化システム (NLMandSlideVideoGenerator)

## プロジェクト概要

このプロジェクトは、YouTube解説動画の制作プロセスを自動化/半自動化するシステムです。現行の本番SSOTは YMM4 を使用した `CSV -> YMM4 -> 音声生成 -> 動画レンダリング` の経路です。Gemini/Google Slides/YouTube 連携は API キーがある場合にのみ有効化されます。

## ドキュメント

迷ったら `docs/INDEX.md` を起点にしてください（SSOT/導線の整理済み）。

## 現在の制作パス

- **YMM4 連携（Primary）**: CSV を YMM4 に取り込み、YMM4 内でゆっくりボイス音声を生成してそのまま mp4 をレンダリングする
- **Research workflow**: Web 資料収集と台本整合は前工程として分離し、最終的に CSV を出力して YMM4 に接続する

> 補足: YMM4 制作の手順は `docs/user_guide_manual_workflow.md` と `docs/HANDOVER.md` を参照してください。

🎬 **YouTube解説動画の自動生成システム**

NotebookLMの代替としてGoogle AI Studio Gemini APIを活用し、スライド生成から動画編集、YouTube投稿まで完全自動化するPythonアプリケーションです。

## ✨ 主な機能

- 📝 **AI台本生成** - Gemini APIによる高品質なスクリプト作成
- 🎵 **音声合成** - YMM4によるゆっくりボイス音声生成
- 🎨 **自動スライド生成** - Google Slides APIによるプレゼンテーション作成
- 🎞️ **動画編集** - YMM4による字幕付き動画合成
- 📺 **YouTube自動投稿** - メタデータ管理とサムネイル設定

## 🚀 クイックスタート

### 方法A: YMM4 連携（推奨）

**CSV を YMM4 に取り込んで動画を生成します。**

1. YMM4 をインストール
2. 本プロジェクトの YMM4 プラグイン（NLMSlidePlugin）をビルド・配置
3. CSV を用意し、YMM4 で読み込んで音声生成・レンダリング

> 📖 詳細は [手動素材ワークフローガイド](docs/user_guide_manual_workflow.md) と [HANDOVER](docs/HANDOVER.md) を参照

**Web UIを使う場合:**
```bash
streamlit run src/web/web_app.py
# ブラウザで「CSV Pipeline」ページを選択
```

---

### 方法B: フルセットアップ（API連携あり）

#### 1. 環境セットアップ

```bash
# リポジトリクローン
git clone https://github.com/YuShimoji/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator

# 自動セットアップ実行
python setup_environment.py
```

#### 2. API認証設定

```bash
# 環境変数ファイル作成
# Windows (PowerShell)
copy .env.example .env

# macOS/Linux
# cp .env.example .env

# .envファイルを編集してAPI認証情報を設定
# 主要項目（抜粋）:
#   GEMINI_API_KEY=...
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
python src/main.py --help

# 動画生成実行（Gemini を使用する場合は .env にキー設定）
python src/main.py --topic "AI技術の最新動向" --duration 300

# モジュラーパイプラインのデモ（Gemini と Slides 画像エクスポートに対応）
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
python scripts/generate_interfaces.py --spec docs/openspec_components.md --output docs/generated --component YourComponent

# 3. 実装作成
# 生成されたインターフェースを実装

# 4. 仕様検証
python scripts/validate_openspec.py

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
| **Google Slides API** | `GOOGLE_CLIENT_SECRETS_FILE`, `GOOGLE_OAUTH_TOKEN_FILE` | スライド作成 |

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

- **Python 3.10+**
- **Google AI Studio Gemini API** - AI台本生成
- **YouTube Data API v3** - 動画投稿
- **Google Slides API** - プレゼンテーション作成
- **YMM4** - 音声合成・動画編集

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
- 🐛 [Issues](https://github.com/YuShimoji/NLMandSlideVideoGenerator/issues)

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
