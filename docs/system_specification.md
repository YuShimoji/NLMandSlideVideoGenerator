# システム仕様書

最終更新: 2026-03-16

## 1. システム概要

### 1.1 目的

Web調査から台本生成、ビジュアルリソース取得、CSV組立、YMM4レンダリングまでを一気通貫で実行できる動画制作パイプラインを提供する。Python (CLI/Web UI) で前工程を、YMM4 + NLMSlidePlugin で最終レンダリングを担当する。

### 1.2 システム名

NLMandSlideVideoGenerator

### 1.3 対象ユーザー

- YouTube コンテンツクリエイター（ゆっくり解説動画）
- YukkuriMovieMaker4 (YMM4) を活用した編集者

### 1.4 ステージ構成

| Stage | 主目的 | 主なモジュール |
| --- | --- | --- |
| Stage 1: 素材用意 | Web調査・台本生成 | Research CLI, Gemini Script Provider, NotebookLM Provider |
| Stage 2: ビジュアル+CSV | 画像取得・分類・CSV組立・検証 | SegmentClassifier, StockImageClient, AIImageProvider, TextSlideGenerator, Orchestrator, CsvAssembler, Pre-Export Validator |
| Stage 3: YMM4レンダリング | CSVインポート・音声合成・動画出力 | CsvImportDialog, StyleTemplateLoader, VoiceSpeakerDiscovery |
| Stage 4: 投稿配信 | メタデータ・サムネイル・投稿 | MetadataGenerator, ThumbnailGenerator, YouTubeUploader |

### 1.5 現行実装状態 (2026-03-18)

- **Stage 1**: Research CLI一気通貫 (collect→script→align→review→pipeline) 実装済み
- **Stage 2**: VisualResourceOrchestrator (stock→AI→slideフォールバック) + Pre-Export Validation 実装済み。1262テストPASS
- **Stage 3**: NLMSlidePlugin CSVインポート + style_template.json統一テンプレート + 8種アニメーション実機テストPASS
- **Stage 4**: メタデータ・サムネイル・YouTube投稿・字幕 (SRT/ASS/VTT) 生成実装済み

## 2. 機能要件

### 2.1 コア機能（Stage別）

#### 2.1.1 Stage 1: 素材収集・台本生成

- **入力**: トピック、参考URL
- **処理**:
  - Research CLI (`collect`): Web調査・情報収集
  - Research CLI (`script`): Gemini APIによる台本生成
  - Research CLI (`align`): 台本-素材整合
  - Research CLI (`review`): 品質レビュー
- **出力**: ScriptBundle (台本セグメント群)

#### 2.1.2 Stage 2: ビジュアルリソース+CSV生成

- **入力**: ScriptBundle, スライド画像 (オプション)
- **処理**:
  - SegmentClassifier: Gemini/ヒューリスティックによるvisual/textual分類
  - StockImageClient: Pexels/Pixabay APIで背景画像検索+ダウンロード (日本語→英語翻訳付き)
  - AIImageProvider: Gemini Imagen 4でAI画像生成 (stock失敗時フォールバック)
  - TextSlideGenerator: テキスト主体セグメント用スライドPNG自動生成 (Pillow描画、テーマ切替、キャッシュ)
  - VisualResourceOrchestrator: 全リソース統合+連続多様性制御
  - AnimationAssigner: 8種アニメーション自動割当
  - CsvAssembler: 4列CSV生成 (speaker, text, image_path, animation_type)
  - Pre-Export Validator: 品質検証
- **出力**: 4列CSV + ダウンロード済み画像群

#### 2.1.3 Stage 3: YMM4レンダリング

- **入力**: 4列CSV, style_template.json
- **処理**:
  - CsvImportDialog: CSVインポート→AudioItem+TextItem+ImageItem自動配置
  - StyleTemplateLoader: 字幕/アニメーション/クロスフェード/タイミング設定の統一読み込み
  - VoiceSpeakerDiscovery: YMM4内蔵ボイスの自動検出・話者割当
  - WavDurationReader: WAV実尺によるタイムライン同期
  - ValidateImportItems: インポート前品質チェック
- **出力**: mp4動画ファイル

#### 2.1.4 Stage 4: 投稿配信

- **入力**: mp4, ScriptBundle
- **処理**: メタデータ・タグ・サムネイル自動生成、YouTube投稿
- **出力**: 投稿結果 or メタデータJSON + サムネイル

### 2.2 支援機能

#### 2.2.1 NotebookLM統合 (`src/notebook_lm/`)

- **SourceCollector**: Web情報収集 + 信頼度スコアリング
- **GeminiIntegration**: Gemini APIによる台本生成・フォールバックチェーン管理 (gemini-2.5-flash → gemini-2.0-flash → モック)
- **TranscriptProcessor**: 音声文字起こし結果の構造化 (SRT変換、キーポイント抽出、精度算出)
- **ScriptAlignment**: 台本と素材の整合チェック
- **CsvTranscriptLoader**: CSV形式の台本読み込み

#### 2.2.2 スライド分割 (`src/slides/`)

- **ContentSplitter**: トランスクリプトセグメントをスライド単位に分割 (トピック変化検出、話者変化判定、時間ギャップ検出)
- **SlideGenerator**: スライドパッケージ生成
- **GoogleSlidesClient**: Google Slides APIによるプレゼンテーション作成 (オプション)

#### 2.2.3 YouTube投稿 (`src/youtube/`)

- **MetadataGenerator**: 台本・トピック・引用元から概要欄・タグ・チャプター・ハッシュタグ・SEO最適化を自動生成
- **YouTubeUploader**: YouTube Data APIによる動画投稿・手動投稿フォールバック

#### 2.2.4 サムネイル生成 (`src/core/thumbnails/`)

- **TemplateThumbnailGenerator**: テンプレートベースのサムネイル自動生成 (Pillow描画)
- **AIThumbnailGenerator**: AI画像を活用したサムネイル生成

#### 2.2.5 運用API (`src/server/`) [オプション]

- **OperationalAPIServer**: FastAPIベースの運用ダッシュボード
  - ヘルスチェック、Prometheusメトリクス (オプション)
  - パイプラインジョブ管理、クリーンアップタスク

### 2.3 品質管理機能

- **Pre-Export Validation**: 画像存在確認、アニメーション種別検証、行数チェック
- **ValidateImportItems (C#)**: 連続同一画像検出、gap/overlap検出、合計時間チェック、統計サマリー
- **スタイルテンプレート**: 3プリセット (default/cinematic/minimal) + バリアント生成

### 2.4 エラーハンドリング

- **API**: 指数バックオフリトライ (1s→2s→4s)、429/5xx自動リトライ、401/403即時失敗
- **フォールバック連鎖**: Pexels→Pixabay→Gemini Imagen→TextSlideGenerator→空欄
- **Geminiモデルフォールバック**: gemini-2.5-flash → gemini-2.0-flash → モック
- **パイプライン再開**: PipelineState永続化 + CLI `--resume` (SP-034)
- **例外階層**: `PipelineError` → `StageError` / `ConfigError` / `APIError` 等 (`src/core/exceptions.py`)

## 3. 非機能要件

### 3.1 性能要件

- **処理時間**: 30分動画のCSV生成 (Stage 2) は5分以内
- **同時処理**: シングルユーザー前提 (CLI/Web UI)
- **API制限**: Pexels 200req/hour, Pixabay 5000req/hour, Gemini 15req/min

### 3.2 可用性要件

- **ステージ単位の復旧**: PipelineState永続化により失敗ステップから再開可能 (`--resume`)
- **フォールバック**: 各外部API障害時に代替パスあり (stock→AI→slide)

### 3.3 セキュリティ要件

- API キーは `.env` と OS 環境変数で管理
- ストック画像のattribution情報を `StockImage.photographer` で保持
- `validate_api_keys()` でインポート前にAPIキー有効性を検証

### 3.4 保守性要件

- Python/C# 二層構成。共有設定は `style_template.json` で一元管理
- Python 1262テスト (pytest, カバレッジ84%/コア92%)、C# 34テスト (dotnet test) によるコンパイル検証
- Ruff 0 errors、Mypy 0 errors (CI 5段階全緑)
- ドキュメントは `docs/` に集約、`docs/spec-index.json` でインデックス管理
- ドメイン固有例外階層 (`src/core/exceptions.py`) で統一エラーハンドリング

## 4. システム構成

### 4.1 データフロー

```text
[トピック入力] → [Web調査] → [Gemini台本生成] → [ScriptBundle]
                                                      ↓
[SegmentClassifier] → [Pexels/Pixabay] → [Gemini Imagen] → [TextSlideGenerator] → [VisualResourcePackage]
                                                                                          ↓
[CsvAssembler] → [Pre-Export Validation] → [4列CSV]
                                                ↓
[YMM4 CSVインポート] → [StyleTemplate適用] → [音声合成] → [mp4]
                                                              ↓
[メタデータ生成] → [サムネイル生成] → [YouTube投稿]
```

### 4.2 外部システム連携

| API | 用途 | レート制限 |
| --- | --- | --- |
| Gemini 2.5 Flash | 台本生成/分類/キーワード抽出/翻訳/台本補完 | 15 req/min (free) |
| Gemini Imagen 4 | AI画像生成 (有料プラン必須) | -- |
| Pexels | ストック写真検索 | 200 req/hour (free) |
| Pixabay | ストック写真検索 (フォールバック) | 5000 req/hour (free) |
| YouTube Data API | 動画投稿 | 10,000 units/day |
| Google Slides API | プレゼンテーション生成 (オプション) | 300 req/min |

## 5. 技術仕様

### 5.1 開発環境

- **言語**: Python 3.11 (前工程) / C# .NET (NLMSlidePlugin)
- **エントリポイント**: CLI (`scripts/research_cli.py`), Web UI (`streamlit run src/web/web_app.py`)
- **テンプレート管理**: `config/style_template*.json`
- **venv**: `venv/` (Windows, `.\venv\Scripts\activate`)

### 5.2 主要ライブラリ

```python
# AI/API
google-genai             # Gemini SDK (旧google-generativeai から移行済み)
requests                 # Pexels/Pixabay API

# 画像・音声
Pillow                   # サムネイル・テキストスライド生成
pydub                    # 音声処理

# Web UI / Server
streamlit                # Web UI
fastapi + uvicorn        # 運用API (オプション)

# テスト・品質
pytest                   # 1262テストPASS
ruff                     # Linter (0 errors)
mypy                     # 型チェック (0 errors)
```

### 5.3 ディレクトリ構成

```text
src/
├── main.py                          # エントリポイント
├── core/
│   ├── pipeline.py                  # メインパイプライン
│   ├── pipeline_state.py            # PipelineState (再開機能)
│   ├── csv_assembler.py             # CsvAssembler
│   ├── style_template.py            # StyleTemplateManager
│   ├── stage_runners.py             # ステージ実行ロジック
│   ├── exceptions.py                # ドメイン固有例外階層
│   ├── interfaces.py                # Protocol定義
│   ├── models.py                    # PipelineArtifacts等
│   ├── helpers.py                   # ユーティリティ関数
│   ├── adapters/                    # コンテンツアダプター
│   ├── editing/                     # Pre-Export Validator, YMM4Backend
│   ├── platforms/                   # YouTube/TikTokアダプター
│   ├── providers/script/            # IScriptProvider実装 (Gemini, NotebookLM)
│   ├── thumbnails/                  # サムネイル生成 (Template, AI)
│   ├── timeline/                    # タイムラインプランナー
│   ├── utils/                       # Logger, FFmpeg, ToolDetection, Decorators
│   └── visual/                      # SegmentClassifier, Stock/AI/TextSlide, Orchestrator
├── notebook_lm/                     # NotebookLM統合 (7ファイル)
├── slides/                          # スライド分割・Google Slides
├── youtube/                         # メタデータ生成・YouTube投稿
├── gapi/                            # Google OAuth認証
├── server/                          # 運用APIサーバー (FastAPI)
├── video_editor/                    # VideoInfo, ThumbnailInfo
└── web/                             # Streamlit Web UI + Pages

ymm4-plugin/
├── Core/                            # CSV解析, StyleTemplate, Voice, WAV
└── TimelinePlugin/                  # CsvImportDialog

config/
├── settings.py                      # 設定管理
├── style_template.json              # デフォルトスタイルテンプレート
├── style_template_cinematic.json    # シネマティックバリアント
└── style_template_minimal.json      # ミニマルバリアント
```

## 6. 制約事項・リスク

### 6.1 技術的制約

- YMM4 は Windows 環境依存
- Gemini Imagen は RAIフィルタにより一部プロンプトが拒否される
- Pexels/Pixabay の無料プランにはレート制限あり

### 6.2 リスク要因

- **外部API依存**: Gemini/Pexels/Pixabay 停止時はTextSlideGeneratorフォールバック
- **品質リスク**: AI生成画像の品質ばらつき (RAIフィルタ、プロンプト品質)
- **コストリスク**: Gemini Imagen のトークン消費 (現在は無料枠内)

## 7. 今後の拡張計画

### 7.1 短期

- YMM4実機テスト (BGM+画像+字幕統合)
- Geminiクォータリセット後の品質確認

### 7.2 中期

- Docker化 / CI-CD強化 (GitHub Actions有効化)
- バッチ処理 / 多言語対応
- ~~テストカバレッジ 80%+~~ **達成済み**: 84% (全体) / 92% (コア)。残は外部API/Web UI依存

### 7.3 長期

- TikTok / Shorts 連携
- YouTube自動公開パイプライン
