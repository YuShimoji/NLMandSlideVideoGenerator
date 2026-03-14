# NLMandSlideVideoGenerator

YouTube解説動画自動化システム (NLMandSlideVideoGenerator)

## プロジェクト概要

このプロジェクトは、YouTube解説動画の制作プロセスを自動化/半自動化するシステムです。現行の本番SSOTは Path A の単一経路構成です。Path A は `CSV -> YMM4 -> 音声生成 -> 動画レンダリング` の主経路として稼働中です。Gemini/Google Slides/YouTube 連携は API キーがある場合にのみ有効化されます。

## ドキュメント

迷ったら `docs/INDEX.md` を起点にしてください（SSOT/導線の整理済み）。

## 現在の制作パス

- **Path A（Primary）**: CSV を YMM4 に取り込み、YMM4 内でゆっくりボイス音声を生成してそのまま mp4 をレンダリングする
- **Research workflow**: Web 資料収集と台本整合は前工程として分離し、最終的に CSV を出力して Path A に接続する

> 補足: YMM4 は現在唯一サポートされている音声/動画レンダリング方法です。制作の手順は `docs/user_guide_manual_workflow.md` と `docs/HANDOVER.md` を参照してください。

YouTube解説動画(16:9スライド形式)の制作を半自動化するシステムです。CSVタイムラインからYMM4経由で音声生成+動画レンダリングを行います。

## 🚀 クイックスタート

### 方法A: APIなしで今すぐ試す（推奨）

**サンプルファイルを使って、5分で動画生成を体験できます。**

```bash
# 1. リポジトリクローン & 依存関係インストール
git clone https://github.com/YuShimoji/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator
pip install -r requirements.txt

# 2. YMM4を起動し、NLMSlidePluginでCSVをインポート
# 3. YMM4内でゆっくりボイス音声を自動生成
# 4. YMM4で動画をレンダリング（書き出し）→ 最終 mp4

# 詳細は docs/user_guide_manual_workflow.md を参照
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
git clone https://github.com/YuShimoji/NLMandSlideVideoGenerator.git
cd NLMandSlideVideoGenerator
python setup_environment.py
```

#### 2. API認証設定

```bash
copy .env.example .env
# .envファイルを編集:
#   GEMINI_API_KEY=...
#   GOOGLE_CLIENT_SECRETS_FILE=./google_client_secret.json
#   GOOGLE_OAUTH_TOKEN_FILE=./token.json
# 詳細は docs/api_setup_guide.md を参照
```

### 3. テスト実行

```bash
# ユニットテスト
python -m pytest tests/ -q -m "not slow and not integration" --tb=short

# YMM4 プラグインテスト（手動）
# 1. YMM4起動 → NLMSlidePluginでCSVインポート
# 2. YMM4内で音声生成 → 動画レンダリング
```

### 4. 本格運用開始

```bash
# YMM4制作（Path A: CSV → YMM4 で音声+動画レンダリング）
# 1. YMM4を起動し、NLMSlidePluginでCSVをインポート
# 2. YMM4内でゆっくりボイス音声を自動生成
# 3. YMM4で動画をレンダリング（書き出し）→ 最終 mp4

# 詳細は docs/user_guide_manual_workflow.md を参照
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

## 🪟 Windows 環境でのUnicode表示について

Windowsコンソールの既定コードページ（cp932）で絵文字などの出力時に `UnicodeEncodeError` が発生する場合は、以下の対策が有効です。

- `PYTHONIOENCODING=utf-8` 環境変数の利用
- Windows Terminal で UTF-8 を使用
- サブプロセス実行時: `encoding='utf-8', errors='replace'` を設定

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
| **YMM4** | ローカルインストール (v4.33+) | 音声生成+動画レンダリング |

## 🏗️ システム構成

```
src/
├── notebook_lm/          # Gemini API連携
│   ├── gemini_integration.py
│   └── audio_generator.py
├── slides/               # スライド生成
│   ├── slide_generator.py
│   └── content_splitter.py
├── audio/                # 音声処理データ型
│   └── models.py
├── video_editor/         # 動画編集データ型
│   └── models.py
└── youtube/              # YouTube連携
    └── uploader.py
```

## 🧪 テスト

```bash
# Python ユニットテスト
python -m pytest tests/ -q -m "not slow and not integration" --tb=short

# .NET プラグインテスト
dotnet test ymm4-plugin/tests/NLMSlidePlugin.Tests.csproj -c Release --nologo -q
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

## 技術スタック

- **Python 3.11+** / **.NET 10.0** (YMM4 plugin, v4.50+対応)
- **YMM4** - 音声生成+動画レンダリング (唯一の推奨方法)
- **Google AI Studio Gemini API** - AI台本生成 (optional)
- **Streamlit** - Web UI
- **FastAPI** - API server

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
- [x] CSVタイムライン入力仕様
- [x] Web UI実装（Streamlit）
- [x] YMM4プラグイン統合
- [x] 長文自動分割機能

### 進行中
- [ ] YMM4 SDK統合 (GenerateVoiceAsync, ImportFromCsv, AddToTimelineAsync)
- [ ] E2E制作完走 (CSV→YMM4→mp4)

### 将来
- [ ] 多言語アライメント精度向上
- [ ] クラウドレンダリング対応

---

**最終更新**: 2026年3月7日
