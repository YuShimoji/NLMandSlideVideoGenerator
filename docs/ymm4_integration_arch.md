# YMM4 連携アーキテクチャ（現行サマリ）

最終更新: 2026-03-17

> この文書は **現行運用（Path A 単一）** の要点のみを記載します。
> 旧Path B（MoviePy + Pythonレンダリング）と `run_csv_pipeline.py` は 2026-03-08 に完全削除済みです。
> 実装・方針の一次情報は `docs/PROJECT_ALIGNMENT_SSOT.md` を参照してください。

---

## 1. 現行アーキテクチャ

### 全体フロー

```
[Web調査/台本生成] → [CsvAssembler] → [Pre-Export検証] → [YMM4 CSVインポート] → [音声生成] → [動画出力(mp4)]
     Python CLI/UI         Python          Python         NLMSlidePlugin (C#)    YMM4内蔵      YMM4
```

### Python側 (前工程)

1. **素材収集**: Web調査 → Gemini台本生成 → 台本整形 (`scripts/research_cli.py`)
2. **ビジュアルリソース取得**: SegmentClassifier → StockImageClient (Pexels/Pixabay) → AIImageProvider (Gemini Imagen) → スライドフォールバック
3. **CSV生成**: CsvAssembler が台本 + 画像パス + アニメーション種別 を4列CSVに統合
4. **品質検証**: Pre-Export Validator が画像存在・アニメーション種別・行数を検証

### C#側 (NLMSlidePlugin)

1. **CSVインポート**: CsvImportDialog が4列CSV (speaker, text, image_path, animation_type) を読み込み
2. **タイムライン構築**: AudioItem (音声) + TextItem (字幕) + ImageItem (背景画像) を自動配置
3. **スタイル適用**: style_template.json から字幕/アニメーション/クロスフェード/タイミング設定を統一読み込み
4. **音声生成**: VoiceSpeakerDiscovery でYMM4内蔵ボイスを自動割当
5. **レンダリング**: YMM4がfinal rendererとしてmp4を出力

### 共有設定

`config/style_template.json` を Python (StyleTemplateManager) と C# (StyleTemplateLoader) の両方が読み込み、字幕・アニメーション・タイミング・色設定を統一する。

---

## 2. 主要コンポーネント

### Python側

| モジュール | 場所 | 責務 |
|---|---|---|
| ResearchCLI | `scripts/research_cli.py` | collect→script→align→review→pipeline 一気通貫CLI |
| CsvAssembler | `src/core/csv_assembler.py` | 台本+画像+アニメーション→4列CSV |
| SegmentClassifier | `src/core/visual/segment_classifier.py` | visual/textualセグメント分類 (ヒューリスティック+Gemini) |
| StockImageClient | `src/core/visual/stock_image_client.py` | Pexels/Pixabay画像検索+ダウンロード |
| AIImageProvider | `src/core/visual/ai_image_provider.py` | Gemini Imagen 3.0によるAI画像生成 |
| VisualResourceOrchestrator | `src/core/visual/resource_orchestrator.py` | 全ビジュアルリソース統合 (stock→AI→slideフォールバック) |
| AnimationAssigner | `src/core/visual/animation_assigner.py` | 8種アニメーション自動割当 |
| StyleTemplateManager | `src/core/style_template.py` | style_template.json読み込み・検証・管理 |
| Pre-Export Validator | `src/core/editing/pre_export_validator.py` | CSVバリデーション (画像存在・種別・行数) |
| PipelineState | `src/core/pipeline_state.py` | パイプラインステップ再開 (SP-034) |

### C#側 (NLMSlidePlugin)

| モジュール | 場所 | 責務 |
|---|---|---|
| CsvTimelineReader | `ymm4-plugin/Core/CsvTimelineReader.cs` | 4列CSV解析 |
| StyleTemplateLoader | `ymm4-plugin/Core/StyleTemplateLoader.cs` | style_template.json統一読み込み |
| CsvImportDialog | `ymm4-plugin/TimelinePlugin/CsvImportDialog.xaml.cs` | CSVインポートUI + タイムライン構築 |
| VoiceSpeakerDiscovery | `ymm4-plugin/Core/VoiceSpeakerDiscovery.cs` | YMM4ボイス自動割当 |
| WavDurationReader | `ymm4-plugin/Core/WavDurationReader.cs` | WAV実尺読み取り→タイムライン同期 |

---

## 3. 実行導線

### CLI (推奨)

```bash
# 一気通貫パイプライン
python scripts/research_cli.py pipeline "トピック名" --auto-images --duration 30

# 個別ステップ
python scripts/research_cli.py collect "トピック名"
python scripts/research_cli.py script output/トピック名/
python scripts/research_cli.py align output/トピック名/
python scripts/research_cli.py review output/トピック名/
```

### Web UI

```powershell
streamlit run src/web/web_app.py
# 「素材パイプライン」で一気通貫実行
# 「CSV Pipeline」でCSV個別生成
```

### YMM4インポート

1. YMM4を起動し、NLMSlidePlugin の CSVインポートダイアログを開く
2. 生成されたCSVファイルを選択
3. 話者-ボイスマッピングを確認し、インポート実行

---

## 4. CSV形式 (4列)

```csv
speaker,text,image_path,animation_type
れいむ,AIとは何か,C:\images\pexels_abc.jpg,pan_left
まりさ,機械学習の基礎,C:\images\ai_xyz.png,zoom_in
れいむ,倫理的課題,C:\slides\slide_001.png,static
```

| 列 | 内容 | 必須 |
|---|---|---|
| speaker | 話者名 | Yes |
| text | セリフ | Yes |
| image_path | 背景画像パス | No (空欄可) |
| animation_type | ken_burns/zoom_in/zoom_out/pan_left/pan_right/pan_up/static | No (空欄→ken_burns) |

---

## 5. 関連仕様

- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/ymm4_export_spec.md` — YMM4エクスポート詳細仕様
- `docs/ymm4_final_workflow.md` — 制作ワークフロー手順書
- `docs/visual_resource_pipeline_spec.md` — ビジュアルリソースパイプライン仕様
- `docs/video_quality_pipeline_spec.md` — 品質パイプライン仕様
- `config/style_template.json` — スタイルテンプレート (Python/C#共有)

---

## 6. レガシー参照の扱い

以下は現行運用には使用しない。

- `run_csv_pipeline.py` (削除済み)
- `csv_pipeline_runner` (削除済み)
- Path B（MoviePy backend）前提の記述 (削除済み)
- 外部TTS連携コード (削除済み)

レガシー資料は `docs/archive/` に集約済み。