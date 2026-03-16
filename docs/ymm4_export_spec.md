# YMM4 エクスポート仕様

**最終更新**: 2026-03-17
**ステータス**: 全主要機能実装済み (SP-024/026/027/028/029/030/031/033)

---

## 1. 概要

本ドキュメントは、NLMandSlideVideoGenerator における YukkuriMovieMaker4 (YMM4) エクスポート機能の仕様を定義します。

### 1.1 目的

- CSV タイムライン / 通常パイプラインから、YMM4 で編集可能なプロジェクトを出力
- ユーザーが YMM4 GUI で微調整を行い、高品質な動画を書き出すワークフローを支援

### 1.2 現在の実装状態

| 機能 | 状態 | 備考 |
|------|------|------|
| YMM4 NLMSlidePlugin (CSV Import) | ✅ 実装済み | CsvImportDialog + Ymm4TimelineImporter |
| YMM4 Voice自動生成 UI接続 | ✅ 実装済み | VoiceSpeakerDiscovery (SP-024) |
| ImageItem自動配置 | ✅ 実装済み | CSV 3列目画像パス → ImageItem (SP-026) |
| WAV実尺タイムライン同期 | ✅ 実装済み | WavDurationReader (SP-028) |
| 7種アニメーション | ✅ 実装済み | ken_burns/zoom_in/zoom_out/pan_left/pan_right/pan_up/static (SP-033) |
| クロスフェードトランジション | ✅ 実装済み | FadeIn/FadeOut 0.5秒、交互レイヤー (SP-030) |
| 字幕テンプレート | ✅ 実装済み | ApplySubtitleStyle: 話者色6色+Border+CenterBottom (SP-030) |
| スタイルテンプレート | ✅ 実装済み | style_template.json Python/C#共有 (SP-031) |
| Pre-Export Validation | ✅ 実装済み | ValidateImportItems: 連続同一画像検出+統計 (SP-031) |
| BGMテンプレート自動配置 | ✅ 実装済み | style_template.json bgmセクション (SP-031) |
| ビジュアルリソースパイプライン | ✅ 実装済み | StockImage + AIImage + TextSlide + Orchestrator (SP-033) |
| YMM4 プロジェクトディレクトリ生成 | ✅ 実装済み | Python側 YMM4EditingBackend |
| timeline_plan.json / slides_payload.json | ✅ 実装済み | CSV タイムライン連携 |
| テンプレート .y4mmp 複製 | ✅ 実装済み | |
| AutoHotkey スクリプト生成 | ⚠️ PoC | プレースホルダー操作のみ |
| 動画出力 (MoviePy) | ❌ 削除済み | 2026-03-08 削除 |

---

## 2. アーキテクチャと設計意図

### 2.1 設計上のワークフロー（理想形）

**注**: MoviePy フォールバックは 2026-03-08 に削除されました。現在は YMM4 が唯一のレンダリング手段です。

```
┌─────────────────┐
│ ScriptBundle    │
│ AudioInfo       │──▶ TimelinePlanner ──▶ TimelinePlan
│ YMM4 Template   │
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ YMM4EditingBackend                      │
│  1. テンプレート .y4mmp 複製            │
│  2. YMM4 API でタイムライン挿入         │  # 主に .NET プラグインAPI を想定
│  3. YMM4 API で書き出し                 │
│     └─ 失敗時: AutoHotkey でGUI操作     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ VideoInfo       │
│ YMM4 Project    │
│ TimelinePlan    │
└─────────────────┘
```

### 2.2 現状の実装ワークフロー（Path A 一本化後）

```
[Research CLI / Web UI]
         │
         ▼
┌──────────────────────────────────────────┐
│ Stage 1: 素材収集                        │
│ collect → script → align → review        │
│ → ScriptBundle                           │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Stage 2: ビジュアル+CSV生成              │
│ SegmentClassifier → StockImageClient     │
│ → AIImageProvider → Orchestrator         │
│ → CsvAssembler → Pre-Export Validator    │
│ → 4列CSV (speaker,text,image,animation) │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Stage 3: YMM4 NLMSlidePlugin             │
│ CsvImportDialog でCSVインポート          │
│ → AudioItem + TextItem + ImageItem 自動配置│
│ → StyleTemplate適用 (字幕/アニメ/BGM)    │
│ → VoiceSpeakerDiscovery で音声生成       │
│ → YMM4 レンダリング → mp4               │
└──────────────────────────────────────────┘
```

> Python側 YMM4EditingBackend による timeline_plan.json / slides_payload.json 出力も利用可能だが、
> 主要ワークフローは上記の Research CLI → 4列CSV → NLMSlidePlugin CSVインポート。

### 2.3 設計と実装のギャップ（2026-03-17 更新）

| 設計項目 | 設計意図 | 現状 | ギャップ |
|----------|----------|------|----------|
| YMM4 API 連携 | API 経由でタイムライン挿入 | .NET Plugin で実装済み | なし |
| 書き出し方式 | YMM4 で音声生成+レンダリング | YMM4 手動実行 | 書き出し自動化は未着手 |
| AutoHotkey | GUI 操作で書き出し | PoC（プレースホルダー） | 中 |
| スタイルテンプレート | Python/C#統一スタイル管理 | style_template.json共有 | なし |
| ビジュアルリソース | 画像素材自動取得 | StockImage+AIImage+TextSlide | なし |
| アニメーション | 7種自動割当 | AnimationAssigner+ApplyAnimationDirect | pan_down未実装 |
| Pre-Export検証 | インポート前品質チェック | ValidateImportItems拡張済み | なし |

---

## 3. 出力ファイル構造

### 3.1 プロジェクトディレクトリ

```
data/ymm4/ymm4_project_YYYYMMDD_HHMMSS/
├── project.y4mmp              # YMM4 プロジェクトファイル
├── timeline_plan.json         # タイムライン計画
├── slides_payload.json        # スライド情報（CSV モード時）
├── render_metadata.json       # レンダリング結果メタデータ
├── RUN_AHK_INSTRUCTIONS.txt   # 手動実行手順
├── ymm4_automation.ahk        # 生成された AutoHotkey スクリプト
└── text/
    └── timeline.csv           # 元の CSV（コピー）
```

> 音声ファイル(WAV)はPython側では生成・コピーしない。音声合成はYMM4内部で実行される。

### 3.2 timeline_plan.json

```json
{
  "timeline_plan": {
    "segments": [
      {
        "id": 1,
        "start_time": 0.0,
        "end_time": 5.0,
        "slide_id": 1,
        "effects": []
      }
    ],
    "total_duration": 120.0
  },
  "audio": {
    "file_path": "/path/to/audio.wav",
    "duration": 120.0,
    "language": "ja"
  },
  "transcript": {
    "title": "動画タイトル",
    "segments": [
      {
        "id": 1,
        "start_time": 0.0,
        "end_time": 5.0,
        "text": "こんにちは",
        "speaker": "Speaker1"
      }
    ]
  }
}
```

### 3.3 slides_payload.json（CSV タイムラインモード専用）

```json
{
  "meta": {
    "source_csv": "/path/to/timeline.csv",
    "generated_at": "2025-11-30T12:00:00",
    "auto_split": true,
    "video_resolution": [1920, 1080],
    "total_segments": 10
  },
  "segments": [
    {
      "segment_id": 1,
      "speaker": "Speaker1",
      "start_time": 0.0,
      "end_time": 5.0,
      "text": "こんにちは、本日は...",
      "audio_file": null,  // 音声はYMM4内部で生成（旧仕様ではWAVパスが入った）
      "subslides": [
        {
          "slide_id": 1,
          "order": 0,
          "count": 2,
          "title": "こんにちは、本日は...",
          "text": "こんにちは、",
          "duration": 2.5,
          "is_continued": false
        },
        {
          "slide_id": 2,
          "order": 1,
          "count": 2,
          "title": "こんにちは、本日は...（続き 2/2）",
          "text": "本日は...",
          "duration": 2.5,
          "is_continued": true
        }
      ]
    }
  ]
}
```

### 3.4 export_outputs（PipelineArtifacts 内）

```python
artifacts.editing_outputs = {
    "ymm4": {
        "project_dir": "/path/to/ymm4_project_YYYYMMDD_HHMMSS",
        "project_file": "/path/to/project.y4mmp",
        "timeline_plan": "/path/to/timeline_plan.json",
        "slides_payload": "/path/to/slides_payload.json",
        "template_diff": "/path/to/template_diff_applied.json"
    }
}
```

---

## 4. 使用方法

### 4.1 Research CLI（推奨ワークフロー）

```bash
# 一気通貫パイプライン: トピック → 4列CSV
source venv/Scripts/activate
python scripts/research_cli.py pipeline "テスト動画" --auto-images --duration 10

# 個別ステップ実行
python scripts/research_cli.py collect "テスト動画"
python scripts/research_cli.py script "テスト動画"
python scripts/research_cli.py align "テスト動画"
python scripts/research_cli.py review "テスト動画"

# 途中再開 (SP-034)
python scripts/research_cli.py pipeline "テスト動画" --resume
```

### 4.2 Web UI 経由

```bash
streamlit run src/web/web_app.py
# ブラウザで「素材パイプライン」ページから実行
```

### 4.3 YMM4 CSVインポート（Stage 3）

1. YMM4 を起動し、NLMSlidePlugin がロードされていることを確認
2. プラグインの「CSVインポート」ボタンから生成された 4列CSV を選択
3. BGMファイルを選択（オプション）
4. 「音声を自動生成」チェックボックスがONであることを確認
5. 「インポート」を実行 → AudioItem + TextItem + ImageItem が自動配置
6. YMM4 で書き出し → mp4

---

## 5. 設定

### 5.1 config/settings.py

```python
YMM4_SETTINGS = {
    # YMM4 テンプレートファイルパス
    "project_template": "templates/ymm4/base_project.y4mmp",
    
    # AutoHotkey スクリプトパス
    "auto_hotkey_script": "templates/scripts/ymm4_export.ahk",
    
    # YMM4 ワークスペースディレクトリ
    "workspace_dir": "data/ymm4",
}

PIPELINE_COMPONENTS = {
    # YMM4 バックエンドを使用する場合
    "editing_backend": "ymm4",
}
```

### 5.2 環境変数

```bash
# YMM4 テンプレート差分適用（JSON形式）
export YMM4_TEMPLATE_DIFF='{"subtitle_style": "bold_glow"}'
```

---

## 6. AutoHotkey 連携

### 6.1 現状 ✅ 実用化完了

- `scripts/generate_ymm4_ahk.py` が `slides_payload.json` / `timeline_plan.json` から AutoHotkey スクリプトを生成
- 生成されたスクリプトは `ymm4_automation.ahk` として出力
- **以下の機能が実装済み:**
  - YMM4 ウィンドウ検出・起動待ち（タイムアウト付き）
  - エラーハンドリング・リトライロジック
  - 詳細ログ出力（デバッグモード）
  - 音声ファイルインポート操作
  - 動画エクスポートダイアログ操作

### 6.2 使用方法

```bash
# スクリプト生成
python scripts/generate_ymm4_ahk.py /path/to/ymm4_project

# オプション付き生成
python scripts/generate_ymm4_ahk.py /path/to/ymm4_project \
  --debug \
  --timeout 60 \
  --delay 300 \
  --retries 5

# 生成後に即座に実行
python scripts/generate_ymm4_ahk.py /path/to/ymm4_project --run

# 生成されたスクリプトを手動実行
AutoHotkey.exe "data/ymm4/ymm4_project_XXXXXX/ymm4_automation.ahk"
```

### 6.3 設定オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--debug` | true | デバッグモード（ログ出力・ツールチップ表示） |
| `--ymm4-exe` | `C:\Program Files\YMM4\YMM4.exe` | YMM4実行ファイルパス |
| `--timeout` | 30 | ウィンドウ待機タイムアウト秒 |
| `--delay` | 200 | 操作間遅延ミリ秒 |
| `--retries` | 3 | 最大リトライ回数 |
| `--run` | false | 生成後に即座に実行 |

### 6.4 生成されるスクリプトの機能

- **ユーティリティ関数**: `Log()`, `ShowError()`, `WaitForWindow()`, `ActivateWindow()`, `SafeSend()`, `SafeClick()`, `RetryOperation()`
- **YMM4操作関数**: `LaunchYMM4()`, `WaitForYMM4Ready()`, `ImportAudioFile()`, `ExportVideo()`, `WaitForExportComplete()`
- **ログ出力**: `ymm4_automation.log` にタイムスタンプ付きで全操作を記録

### 6.5 実装状況

| 機能 | 状態 | 備考 |
|------|------|------|
| YMM4 ウィンドウ検出 | ✅ 実装済み | `YukkuriMovieMaker` / `YMM4` 両対応 |
| 起動待ち安定化 | ✅ 実装済み | タイムアウト・フォールバック付き |
| エラーハンドリング | ✅ 実装済み | リトライ・致命エラー対応 |
| ログ・デバッグ | ✅ 実装済み | ファイル出力・ツールチップ |
| 音声インポート | ✅ 実装済み | Ctrl+Shift+I ダイアログ操作 |
| 書き出し操作 | ✅ 実装済み | Ctrl+Shift+E ダイアログ操作 |
| タイムライン座標 | ⚠️ 環境依存 | F6キーでフォーカス移動 |

---

## 7. 書き出しフォールバック戦略

### 7.1 概要

`ExportFallbackManager` クラスが複数の編集バックエンドを優先順位付きで管理し、失敗時に自動的にフォールバックする。

```
優先順位: YMM4 .NET Plugin API（実装済み） → YMM4 AutoHotkey（PoC）
```

**注**: MoviePy/FFmpeg フォールバックは 2026-03-08 に削除されました。

### 7.2 使用方法

```python
from src.core.editing import ExportFallbackManager, BackendType

# マネージャー初期化（自動検出有効）
manager = ExportFallbackManager(auto_detect=True)

# レンダリング実行
result = await manager.render(
    timeline_plan=plan,
    audio=audio_info,
    slides=slides_package,
    transcript=transcript_info,
    quality="1080p"
)

if result.success:
    print(f"成功: {result.used_backend.value}")
    print(f"出力: {result.video_info.file_path}")
else:
    print(f"失敗: {result.errors}")
```

### 7.3 バックエンド設定

```python
from src.core.editing import BackendConfig, BackendType

# カスタム設定
configs = [
    BackendConfig(
        backend_type=BackendType.YMM4_AHK,
        enabled=True,
        priority=1,
        timeout_seconds=300.0,
        retry_count=2,
    ),
    # MoviePy backend は 2026-03-08 に削除済み
]

manager = ExportFallbackManager(configs=configs)
```

### 7.4 フォールバック動作

| 状況 | 動作 |
|------|------|
| バックエンド成功 | 結果を返却、処理終了 |
| タイムアウト | エラー記録、次バックエンドへ |
| 例外発生 | リトライ後、次バックエンドへ |
| 全バックエンド失敗 | エラー一覧と共に失敗結果を返却 |

### 7.5 実装ファイル

- `src/core/editing/export_fallback_manager.py`
- `tests/test_export_fallback_manager.py`

---

## 8. テスト

### 8.1 関連テストファイル

- `tests/test_csv_pipeline_mode.py`:
  - `test_run_csv_timeline_ymm4_export_payload`: slides_payload / export_outputs の検証
- `tests/test_export_fallback_manager.py`:
  - フォールバック戦略の動作検証（10テストケース）

### 8.2 テスト実行

```bash
python -m pytest tests/test_csv_pipeline_mode.py -v
```

---

## 9. 今後のロードマップ

### 9.1 完了済み

- [x] AutoHotkey 連携実用化 (C3-4)
- [x] フォールバック戦略 (C3-3)
- [x] CSV 4列目アニメーション指定 (SP-033 Phase 1)
- [x] ストック画像自動取得 (SP-033 Phase 2)
- [x] AI画像生成 Gemini Imagen (SP-033 Phase 3)
- [x] テキストスライド自動生成 (SP-033 Phase 3b)
- [x] スタイルテンプレート統一 (SP-031)
- [x] BGMテンプレート自動配置 (SP-031)
- [x] Pre-Export Validation (SP-031)
- [x] パイプラインステップ再開 (SP-034)

### 9.2 短期（品質向上）

- [ ] pan_down アニメーション追加（C# 3行 + Python validation 1行）
- [ ] 実コンテンツでの品質確認（Geminiクォータリセット後）
- [ ] BGMテンプレート + ストック画像CSV + 字幕テンプレートの YMM4 実機テスト

### 9.3 中長期

- [ ] YMM4 書き出し自動化（API or AutoHotkey改善）
- [ ] Docker化 / CI-CD強化
- [ ] バッチ処理 / 多言語対応

---

## 10. 関連ドキュメント

- `docs/spec_transcript_io.md`: Transcript/Script I/O 仕様
- `docs/system_specification.md`: システム仕様書
- `docs/system_architecture.md`: システムアーキテクチャ
- `docs/ymm4_integration_arch.md`: YMM4 連携アーキテクチャ設計（全体フローと責務分担）
- `docs/visual_resource_pipeline_spec.md`: ビジュアルリソースパイプライン仕様
- `docs/video_quality_pipeline_spec.md`: 動画品質パイプライン仕様

---

## 11. YMM4 Voice自動生成（実装完了）

### 11.1 概要

CSVインポート時にYMM4内蔵の音声エンジンで自動的にボイスを生成する機能。

**Plan**: 本セクション (旧plan file: `.claude/plans/unified-imagining-feather.md` は削除済み)

### 11.2 アーキテクチャ

```
CsvImportDialog (WPF)
  ├─ VoiceSpeakerDiscovery (new)
  │   └─ 3-layer IVoiceSpeaker enumeration:
  │       1. AppDomain.GetAssemblies() scan
  │       2. MainWindow DataContext reflection
  │       3. Empty list + error log
  │
  ├─ CsvVoiceResolver (existing)
  │   ├─ FindSpeaker(speakerName, availableSpeakers)
  │   ├─ GenerateVoiceForItemAsync(item, speaker, outputDir)
  │   └─ GenerateVoicesForTimelineAsync(items, speakers, outputDir, progress)
  │
  └─ Ymm4TimelineImporter (existing)
      └─ AddToTimelineWithVoiceAsync(items, timeline, speakers, voiceOutputDir)
```

### 11.3 実装状況

| コンポーネント | 状態 | 備考 |
|---|---|---|
| CsvVoiceResolver.GenerateVoicesForTimelineAsync | ✅ 実装済み | バックエンドロジック完成 |
| Ymm4TimelineImporter.AddToTimelineWithVoiceAsync | ✅ 実装済み | Timeline統合完成 |
| VoiceSpeakerDiscovery | ✅ 実装済み (2026-03-11) | 3層リフレクションフォールバック |
| CsvImportDialog UI拡張 | ✅ 実装済み (2026-03-11) | 「音声を自動生成」チェックボックス（デフォルトON） |
| ImportWithVoiceGenerationAsync | ✅ 実装済み (2026-03-11) | Dialog内の統合イベントハンドラ |

### 11.4 YMM4「台本」機能との関係

YMM4自体に台本読み込み+音声生成機能が内蔵されている。
NLMSlidePluginのVoice自動生成は、CSVインポートと音声生成を一括で行う利便性を提供するが、
YMM4の台本機能で同等のことが手動で実現可能。

| 手段 | 操作 | 自動化度 |
|------|------|----------|
| YMM4 台本機能（内蔵） | YMM4 GUIで台本読み込み→音声生成 | 手動 |
| NLMSlidePlugin Voice生成 | CSVインポート時にチェックボックスONで一括生成 | 半自動 |

現時点ではどちらの手段でもE2E達成可能。プラグインの価値は一括処理の効率化にある。

### 11.5 旧ブロッカー（解決済み）

YMM4 SDK に IVoiceSpeaker 一覧を取得する公式 API が存在しない。

**解決策**: VoiceSpeakerDiscovery による3層リフレクションフォールバック（実装済み）

---

## 12. スライド画像配置（SP-026: 基本実装完了）

### 12.1 実装状況

CSV 3列目に画像ファイルパス（絶対パス）を指定すると、YMM4 ImageItemとしてタイムラインに自動配置される。

**CSVフォーマット**: `話者,テキスト,画像パス（省略可）`

3列目は省略可能（後方互換）。画像ファイルが存在しない場合はWarningを記録しスキップ。

**レイヤー配置**:
- Layer N: AudioItem（音声）
- Layer N+1: TextItem（字幕）
- Layer N+2: ImageItem（スライド画像）

**変更ファイル**:
- `Core/CsvTimelineReader.cs` — CsvTimelineItemにImageFilePathプロパティ追加、ParseLineで3列目読み取り
- `TimelinePlugin/Ymm4TimelineImporter.cs` — AddToTimelineでImageItem配置、AddToTimelineResultにImageItemsフィールド追加
- `TimelinePlugin/CsvImportDialog.xaml.cs` — 両インポートメソッドでImageItem配置

### 12.2 ImageItem API仕様（YMM4 DLL逆引き）

```json
{
  "$type": "YukkuriMovieMaker.Project.Items.ImageItem, YukkuriMovieMaker",
  "FilePath": "C:\\path\\to\\image.png",
  "Frame": 0,
  "Layer": 2,
  "Length": 300,
  "PlaybackRate": 100.0,
  "X": { "Values": [{"Value": 0.0}], ... },
  "Y": { "Values": [{"Value": 0.0}], ... },
  "Opacity": { "Values": [{"Value": 100.0}], ... },
  "Zoom": { "Values": [{"Value": 100.0}], ... }
}
```

PlaybackRateはImageItemでは100.0（AudioItem/TextItemの1.0とは異なる）。

### 12.3 視覚的要件（ユーザー定義）

- 画面全体を埋める絵と説明
- 何らかの動きが画面内にあること（簡単な図のアニメーション、位置交換など）
- 視聴者が受け容れやすい表現

### 12.4 全画面フィット（実装済み）

- ImageItem生成時に画像の実サイズとタイムライン解像度（VideoInfo.Width/Height）を比較
- アスペクト比保持でcontainフィット（画面内に収まる最大サイズ）
- Zoom値をReflection経由でAnimationValue.Values[0].Valueに設定
- 画像読み込み失敗時はZoom=100.0（デフォルト）にフォールバック

### 12.5 7種アニメーション（実装済み・実機確認済み 2026-03-16）

CSV 4列目で指定されたアニメーション種別を `ApplyAnimationDirect()` で ImageItem に適用。

| 種別 | 動作 | style_template.jsonキー |
|------|------|------------------------|
| `ken_burns` | ズームイン (fitZoom → fitZoom * ratio) | `animation.ken_burns_zoom_ratio` |
| `zoom_in` | ズームイン (fitZoom → fitZoom * ratio) | `animation.zoom_in_ratio` |
| `zoom_out` | ズームアウト (fitZoom * ratio → fitZoom) | `animation.zoom_out_ratio` |
| `pan_left` | 左パン (X: +offset → -offset) | `animation.pan_zoom_ratio`, `pan_offset_ratio` |
| `pan_right` | 右パン (X: -offset → +offset) | 同上 |
| `pan_up` | 上パン (Y: +offset → -offset) | 同上 |
| `static` | 静止画 (Zoomのみ、キーフレーム1つ) | — |

**実装方式**:
- `ApplyZoomDirect()`: Values in-place 変更 (AnimationValue は参照型)
- 2値キーフレーム: ImmutableList.Add + リフレクション setter で Values プロパティに代入
- AnimationType を「直線移動」に設定
- 全3インポートパス（VoiceItem一括/AudioItem/CSV batch）に適用済み

**Python側** (`AnimationAssigner`): 6種を自動サイクル割当。staticは手動指定時のみ。

**注意**: `Animation.From` / `Animation.To` は deprecated (CS0618) かつレンダリングを破壊するため使用禁止。

**未実装**: `pan_down` (C# 3行 + Python validation 1行で追加可能)

### 12.6 WAV実尺同期（実装済み）

- `GetWavDurationSeconds()` でWAVファイルヘッダーからバイトレート/データサイズを読み取り実尺を計算
- AudioFilePathが存在する行では、CSV上のDurationではなくWAV実尺でImageItem/TextItemのLengthを決定
- 全3インポートパスに適用済み

### 12.7 字幕スタイル（実装済み）

- `ApplySubtitleStyle()`: TextItemのY位置を画面下部（videoHeight*0.35オフセット）に固定、フォントサイズ48
- 全3インポートパスに適用済み

### 12.8 クロスフェードトランジション（実装済み・実機確認済み 2026-03-16）

VoiceItem一括インポートパスで画像間のクロスフェードを実装。

- **FadeIn/FadeOut**: `ImageItem.FadeIn = 0.5` / `ImageItem.FadeOut = 0.5` (秒単位)
- **交互レイヤー**: 偶数画像はLayer N+1、奇数画像はLayer N+2に配置し、重なりを許可
- **時間延長**: 各画像の開始を `crossfadeFrames` 分前倒し、終了を同量延長

```
画像A: |----FadeIn======FadeOut----|
画像B:                   |----FadeIn======FadeOut----|
レイヤー:  N+1                    N+2
```

#### 運用上の注意

- FadeIn/FadeOut の単位は**秒**。フレーム数で指定すると30秒など極端に長いフェードになる
- 先頭・末尾の画像はフェード区間に前後の画像がないため黒背景が見える
- フェード+ズーム同時適用時、テキストが二重に見えることがある → テキスト主体スライドには `static` を使用

### 12.9 品質チェック（実装済み）

- `ValidateImportItems()`: インポート前にCSVアイテムを検証
  - ファイル存在確認（音声/画像）
  - Duration有効性チェック
  - 空行検出（テキストもオーディオもない行）
  - ギャップ検出（>1秒）/ オーバーラップ検出（<-0.1秒）
  - 総尺チェック（>1時間で警告）
- 警告はランタイムログに出力、インポートは続行

### 12.10 ImageItem コンストラクタ制約（実機確認済み 2026-03-16）

ImageItemの生成には必ずファイルパス付きコンストラクタを使用すること。

```csharp
// 正: 画像が正常にレンダリングされる
var item = new ImageItem(filePath);

// 誤: 画像が読み込まれない（プレビュー黒表示）
var item = new ImageItem { FilePath = filePath };
```

### 12.11 字幕テンプレート (SP-030: 実装完了 2026-03-17)

`ApplySubtitleStyle()` で TextItem に以下のスタイルを一括適用:

| プロパティ | 値 | 備考 |
|-----------|-----|------|
| FontSize | 48 | Values in-place (Animation型) |
| Y | videoHeight * 0.35 | 画面下部。Values in-place |
| BasePoint | CenterBottom | 字幕の標準アンカー |
| Bold | true | 視認性向上 |
| Style | Border | 黒アウトライン |
| StyleColor | #000000 | アウトライン色 |
| MaxWidth | videoWidth * 0.9 | 端のクリッピング防止 |
| WordWrap | Character | 日本語テキスト対応 |
| FontColor | 話者別 | GetSpeakerColor() で自動割当 |
| PlaybackRate | 100.0 | TextItemのデフォルトは100 (旧コードは1.0でバグ) |

**話者別色分け** (`GetSpeakerColor`):
- インポートセッション内で出現順に6色サイクルを割当
- 色: 白 → 黄 → シアン → 緑 → 橙 → ラベンダー
- `ResetSpeakerColors()` をインポート開始時に呼び出し

**InspectYmm4 による API 調査結果** (TextItem):
- `Font` (string, get/set, default: "メイリオ")
- `FontColor` (`System.Windows.Media.Color`, get/set)
- `Style` enum: Normal=0, Shadow=1, ShadowLight=2, Border=3, BorderLight=4, SharpBorder=5, SharpBorderLight=6
- `BasePoint` enum: LeftTop=0, CenterTop=1, ..., CenterBottom=7, ...
- `WordWrap` enum: NoWrap=1, WholeWord=3, Character=4

### 12.12 スタイルテンプレート (SP-031: 実装完了 2026-03-17)

`config/style_template.json` でPython・C#双方の動画スタイルを統一管理する。

**テンプレート構成**:
| セクション | 内容 |
|---|---|
| `video` | 解像度 (width/height) + FPS |
| `subtitle` | フォントサイズ・位置・Bold・Border・WordWrap等 |
| `speaker_colors` | 話者別色の配列 (6色サイクル) |
| `animation` | Ken Burns/Zoom/Pan各種倍率 |
| `crossfade` | 有効/無効 + クロスフェード秒数 |
| `timing` | パディング秒・デフォルト長 |
| `validation` | ギャップ/オーバーラップ/総尺の閾値 |

**読み込み順序** (C# `StyleTemplateLoader.Load`):
1. CSVと同一ディレクトリの `style_template.json`
2. 明示configディレクトリ
3. CSVから上位5階層の `config/style_template.json`
4. ビルトインデフォルト

**品質チェック項目** (`ValidateImportItems`):
- ファイル存在確認 (audio/image)
- Duration妥当性 (0以下は警告)
- 空行検出 (テキスト+音声なし)
- ギャップ検出 (template閾値超過)
- オーバーラップ検出 (template閾値超過)
- 総尺超過チェック
- 連続同一画像検出
- 音声/画像なしのテキストのみインポート検出

### 12.13 未実装（後続スライス）

- `pan_down` アニメーション（C# 3行 + Python 1行で追加可能）
- slides_payload.jsonとの統合（現在はCSV 3列目方式のみ）
- YMM4 書き出し自動化（AutoHotkey改善 or API）

---

## 13. 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-11-30 | 初版作成（現状実装ベース） |
| 2025-11-30 | AutoHotkey連携セクション更新（C3-4完了） |
| 2025-12-01 | フォールバック戦略セクション追加（C3-3完了） |
| 2026-03-09 | Path A一本化反映、Voice自動生成plan追加 |
| 2026-03-14 | セクション10実装状況更新(全完了)、セクション11スライド配置ギャップ追加、MoviePyレガシー参照修正 |
| 2026-03-14 | SP-026: ImageItem自動配置実装。セクション11をギャップ→実装完了に更新。CSV 3列目方式 |
| 2026-03-14 | 全画面フィット実装。Zoom値をcontain計算+Reflection設定。セクション11.4追加 |
| 2026-03-14 | SP-028/029/030/031実装: Ken Burns(5%ズーム)、WAV実尺同期、字幕スタイル、画像フェード、品質チェック |
| 2026-03-16 | SP-033実機テスト反映: クロスフェード+Zoom実装確認。From/To禁止、Values in-place方式に統一。運用ガイドライン追加 |
| 2026-03-17 | SP-030字幕テンプレート完結: ApplySubtitleStyleリファクタ(リフレクション→直接プロパティ)、話者別色分け、PlaybackRate=100修正、Border/Bold/CenterBottom/MaxWidth/WordWrap追加 |
| 2026-03-17 | SP-031スタイルテンプレート+品質チェック: style_template.json v1.1 (video/crossfadeセクション追加)、ValidateImportItems拡張(連続同一画像検出・統計サマリー) |
| 2026-03-17 | SP-004全面更新: 実装状態表拡充(17項目)、ワークフロー図をStage1-3構成に更新、7種アニメーション表追加、ロードマップ完了項目反映、未実装リスト更新(画像自動取得・BGM→完了)、セクション番号重複修正 |
