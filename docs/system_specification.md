# システム仕様書

最終更新: 2026-03-17

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
|-------|--------|----------------|
| Stage 1: 素材用意 | Web調査・台本生成 | Research CLI, Gemini Script Provider |
| Stage 2: ビジュアル+CSV | 画像取得・分類・CSV組立・検証 | SegmentClassifier, StockImageClient, AIImageProvider, Orchestrator, CsvAssembler, Pre-Export Validator |
| Stage 3: YMM4レンダリング | CSVインポート・音声合成・動画出力 | CsvImportDialog, StyleTemplateLoader, VoiceSpeakerDiscovery |
| Stage 4: 投稿配信 | メタデータ・サムネイル・投稿 | MetadataGenerator, ThumbnailGenerator, YouTubeUploader |

### 1.5 現行実装状態 (2026-03-17)
- **Stage 1**: Research CLI一気通貫 (collect→script→align→review→pipeline) 実装済み
- **Stage 2**: VisualResourceOrchestrator (stock→AI→slideフォールバック) + Pre-Export Validation 実装済み。301テストPASS
- **Stage 3**: NLMSlidePlugin CSVインポート + style_template.json統一テンプレート + 7種アニメーション実機テストPASS
- **Stage 4**: メタデータ・サムネイル・字幕 (SRT/ASS/VTT) 生成実装済み

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
  - AIImageProvider: Gemini Imagen 3.0でAI画像生成 (stock失敗時フォールバック)
  - VisualResourceOrchestrator: 全リソース統合+連続多様性制御
  - AnimationAssigner: 7種アニメーション自動割当
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

### 2.2 品質管理機能
- **Pre-Export Validation**: 画像存在確認、アニメーション種別検証、行数チェック
- **ValidateImportItems (C#)**: 連続同一画像検出、gap/overlap検出、合計時間チェック、統計サマリー
- **スタイルテンプレート**: 3プリセット (default/cinematic/minimal) + バリアント生成

### 2.3 エラーハンドリング
- **API**: 指数バックオフリトライ (1s→2s→4s)、429/5xx自動リトライ、401/403即時失敗
- **フォールバック連鎖**: Pexels→Pixabay→Gemini Imagen→スライド→空欄
- **パイプライン再開**: PipelineState永続化 + CLI `--resume` (SP-034)

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
- Python 301テスト (pytest)、C# dotnet build によるコンパイル検証
- ドキュメントは `docs/` に集約、`docs/spec-index.json` でインデックス管理

## 4. システム構成

### 4.1 データフロー
```
[トピック入力] → [Web調査] → [Gemini台本生成] → [ScriptBundle]
                                                      ↓
[SegmentClassifier] → [Pexels/Pixabay] → [Gemini Imagen] → [VisualResourcePackage]
                                                                     ↓
[CsvAssembler] → [Pre-Export Validation] → [4列CSV]
                                                ↓
[YMM4 CSVインポート] → [StyleTemplate適用] → [音声合成] → [mp4]
                                                              ↓
[メタデータ生成] → [サムネイル生成] → [YouTube投稿]
```

### 4.2 外部システム連携

| API | 用途 | レート制限 |
|---|---|---|
| Gemini 2.0 Flash | 台本生成/分類/キーワード抽出/翻訳 | 15 req/min (free) |
| Gemini Imagen 3.0 | AI画像生成 | — |
| Pexels | ストック写真検索 | 200 req/hour (free) |
| Pixabay | ストック写真検索 (フォールバック) | 5000 req/hour (free) |
| YouTube Data API | 動画投稿 | 10,000 units/day |

## 5. 技術仕様

### 5.1 開発環境
- **言語**: Python 3.10+ (前工程) / C# .NET (NLMSlidePlugin)
- **エントリポイント**: CLI (`scripts/research_cli.py`), Web UI (`streamlit run src/web/web_app.py`)
- **テンプレート管理**: `config/style_template*.json`
- **venv**: `venv/` (Windows, `source venv/Scripts/activate`)

### 5.2 主要ライブラリ

```python
# AI/API
google-genai             # Gemini SDK (旧google-generativeai から移行済み)
requests                 # Pexels/Pixabay API

# 画像・音声
Pillow                   # サムネイル生成
pydub                    # 音声処理

# Web UI
streamlit                # Web UI

# テスト
pytest                   # 301テストPASS
```

### 5.3 ディレクトリ構成

```
src/
├── core/
│   ├── csv_assembler.py           # CsvAssembler
│   ├── style_template.py          # StyleTemplateManager
│   ├── pipeline_state.py          # PipelineState (再開機能)
│   ├── editing/
│   │   ├── pre_export_validator.py # Pre-Export Validator
│   │   └── ymm4_backend.py        # YMM4EditingBackend
│   ├── visual/
│   │   ├── segment_classifier.py  # SegmentClassifier
│   │   ├── stock_image_client.py  # StockImageClient
│   │   ├── ai_image_provider.py   # AIImageProvider
│   │   ├── resource_orchestrator.py # VisualResourceOrchestrator
│   │   ├── animation_assigner.py  # AnimationAssigner
│   │   └── models.py              # AnimationType, SegmentType, VisualResource
│   └── providers/
│       └── script/                # IScriptProvider実装
├── web/
│   └── web_app.py                 # Streamlit Web UI
└── video_editor/
    └── models.py                  # VideoInfo, ThumbnailInfo

ymm4-plugin/
├── Core/
│   ├── CsvTimelineReader.cs       # CSV解析
│   ├── StyleTemplateLoader.cs     # style_template.json読み込み
│   ├── VoiceSpeakerDiscovery.cs   # YMM4ボイス自動検出
│   └── WavDurationReader.cs       # WAV実尺読み取り
└── TimelinePlugin/
    └── CsvImportDialog.xaml.cs    # CSVインポートUI

config/
├── settings.py                    # 設定管理
├── style_template.json            # デフォルトスタイルテンプレート
├── style_template_cinematic.json  # シネマティックバリアント
└── style_template_minimal.json    # ミニマルバリアント
```

## 6. 制約事項・リスク

### 6.1 技術的制約
- YMM4 は Windows 環境依存
- Gemini Imagen は RAIフィルタにより一部プロンプトが拒否される
- Pexels/Pixabay の無料プランにはレート制限あり

### 6.2 リスク要因
- **外部API依存**: Gemini/Pexels/Pixabay 停止時はスライドフォールバック
- **品質リスク**: AI生成画像の品質ばらつき (RAIフィルタ、プロンプト品質)
- **コストリスク**: Gemini Imagen のトークン消費 (現在は無料枠内)

## 7. 今後の拡張計画

### 7.1 短期
- BGMテンプレート自動配置 (SP-031残件)
- ドキュメント整備 (本ドキュメント含む)

### 7.2 中期
- Docker化 / CI-CD強化
- バッチ処理 / 多言語対応

### 7.3 長期
- Web ダッシュボード化
- TikTok / Shorts 連携
