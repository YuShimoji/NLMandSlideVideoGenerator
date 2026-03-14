# YMM4 エクスポート仕様

**最終更新**: 2026-03-14
**ステータス**: Voice自動生成完了 / ImageItem自動配置実装済み（SP-026）/ アニメーション未実装

---

## 1. 概要

本ドキュメントは、NLMandSlideVideoGenerator における YukkuriMovieMaker4 (YMM4) エクスポート機能の仕様を定義します。

### 1.1 目的

- CSV タイムライン / 通常パイプラインから、YMM4 で編集可能なプロジェクトを出力
- ユーザーが YMM4 GUI で微調整を行い、高品質な動画を書き出すワークフローを支援

### 1.2 現在の実装状態

| 機能 | 状態 | 備考 |
|------|------|------|
| YMM4 プロジェクトディレクトリ生成 | ✅ 実装済み | |
| timeline_plan.json 出力 | ✅ 実装済み | |
| slides_payload.json 出力 | ✅ 実装済み | CSV タイムライン連携 |
| テンプレート .y4mmp 複製 | ✅ 実装済み | |
| 音声アセットコピー | ✅ 実装済み | |
| AutoHotkey スクリプト生成 | ⚠️ PoC | プレースホルダー操作のみ |
| YMM4 NLMSlidePlugin (CSV Import) | ✅ 実装済み | CsvImportDialog + Ymm4TimelineImporter |
| YMM4 Voice自動生成 UI接続 | ✅ 実装済み | VoiceSpeakerDiscovery + CsvImportDialog拡張 (SP-024) |
| YMM4 ImageItem自動配置 | ✅ 実装済み | CSV 3列目に画像パス指定 → ImageItemとしてタイムライン配置 (SP-026) |
| 動画出力 | ❌ 削除済み | MoviePy backend 削除済み (2026-03-08) |

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
┌─────────────────┐
│ timeline_plan   │
│ audio           │──▶ YMM4EditingBackend
│ slides          │
│ transcript      │
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 1. プロジェクトディレクトリ作成         │
│ 2. テンプレート .y4mmp 複製             │
│ 3. timeline_plan.json 出力              │
│ 4. slides_payload.json 出力             │
│ 5. CSV ソースコピー                      │
│ 6. AutoHotkey スクリプト生成 (PoC)      │
│ 7. render_metadata.json 出力            │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ YMM4 Project    │ ← ユーザーがYMM4で開き、音声生成+レンダリング
│ export_outputs  │
└─────────────────┘
```

### 2.3 設計と実装のギャップ（2026-03-10 更新）

| 設計項目 | 設計意図 | 現状 | ギャップ |
|----------|----------|------|----------|
| YMM4 API 連携 | API 経由でタイムライン挿入 | .NET Plugin で実装済み | なし |
| 書き出し方式 | YMM4 で音声生成+レンダリング | YMM4 手動実行 | 自動化は今後の課題 |
| AutoHotkey | GUI 操作で書き出し | PoC（プレースホルダー） | 中 |
| テンプレート差分 | 差分適用でカスタマイズ | プロトタイプのみ | 中 |
| アセット管理 | timeline_plan/slides_payload 出力 | 実装済み | なし |

**注**: MoviePy フォールバックは 2026-03-08 に削除されました。

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

### 4.1 CLI 経由

```bash
# CSV タイムラインモードで YMM4 エクスポート
streamlit run src/web/web_app.py
# ブラウザで「CSV Pipeline」ページを選択し、CSV/音声素材を入力して実行

# 通常モードで YMM4 バックエンド使用
# (config/settings.py で EDITING_BACKEND=ymm4 を設定)
python run_modular_demo.py --topic "テスト動画"
```

### 4.2 API 経由

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/csv \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "data/timeline.csv",
    "export_ymm4": true
  }'
```

### 4.3 手動 YMM4 編集

1. 出力された `project.y4mmp` を YMM4 で開く
2. NLMSlidePlugin で `text/timeline.csv` をインポートしてタイムラインを構築
3. YMM4 内蔵の音声エンジンでボイスを生成
4. YMM4 で書き出し

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

### 9.1 短期（安定化）✅ 完了

- [x] AutoHotkey 連携の実用化 (C3-4)
- [x] フォールバック戦略の完成 (C3-3)
- [x] テンプレート差分適用の整理 (C3-5)

### 9.2 中期（API連携）

- [ ] YMM4 API / プラグインAPI (https://ymm-api-docs.vercel.app/) 調査
- [ ] API/プラグイン クライアント実装
- [ ] タイムライン挿入機能

### 9.3 長期（完全自動化）

- [ ] API 経由での書き出し
- [ ] RSS連携による自動記事選定

---

## 10. 関連ドキュメント

- `docs/spec_transcript_io.md`: Transcript/Script I/O 仕様
- `docs/system_specification.md`: システム仕様書
- `docs/system_architecture.md`: システムアーキテクチャ
- `docs/ymm4_integration_arch.md`: YMM4 連携アーキテクチャ設計（全体フローと責務分担）

---

## 10. YMM4 Voice自動生成（Plan承認済）

### 10.1 概要

CSVインポート時にYMM4内蔵の音声エンジンで自動的にボイスを生成する機能。

**Plan**: 本セクション (旧plan file: `.claude/plans/unified-imagining-feather.md` は削除済み)

### 10.2 アーキテクチャ

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

### 10.3 実装状況

| コンポーネント | 状態 | 備考 |
|---|---|---|
| CsvVoiceResolver.GenerateVoicesForTimelineAsync | ✅ 実装済み | バックエンドロジック完成 |
| Ymm4TimelineImporter.AddToTimelineWithVoiceAsync | ✅ 実装済み | Timeline統合完成 |
| VoiceSpeakerDiscovery | ✅ 実装済み (2026-03-11) | 3層リフレクションフォールバック |
| CsvImportDialog UI拡張 | ✅ 実装済み (2026-03-11) | 「音声を自動生成」チェックボックス（デフォルトON） |
| ImportWithVoiceGenerationAsync | ✅ 実装済み (2026-03-11) | Dialog内の統合イベントハンドラ |

### 10.4 YMM4「台本」機能との関係

YMM4自体に台本読み込み+音声生成機能が内蔵されている。
NLMSlidePluginのVoice自動生成は、CSVインポートと音声生成を一括で行う利便性を提供するが、
YMM4の台本機能で同等のことが手動で実現可能。

| 手段 | 操作 | 自動化度 |
|------|------|----------|
| YMM4 台本機能（内蔵） | YMM4 GUIで台本読み込み→音声生成 | 手動 |
| NLMSlidePlugin Voice生成 | CSVインポート時にチェックボックスONで一括生成 | 半自動 |

現時点ではどちらの手段でもE2E達成可能。プラグインの価値は一括処理の効率化にある。

### 10.5 旧ブロッカー（解決済み）

YMM4 SDK に IVoiceSpeaker 一覧を取得する公式 API が存在しない。

**解決策**: VoiceSpeakerDiscovery による3層リフレクションフォールバック（実装済み）

---

## 11. スライド画像配置（SP-026: 基本実装完了）

### 11.1 実装状況

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

### 11.2 ImageItem API仕様（YMM4 DLL逆引き）

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

### 11.3 視覚的要件（ユーザー定義）

- 画面全体を埋める絵と説明
- 何らかの動きが画面内にあること（簡単な図のアニメーション、位置交換など）
- 視聴者が受け容れやすい表現

### 11.4 未実装（後続スライス）

- 画像の位置・サイズ調整（全画面フィット）
- アニメーション（パン・ズーム等）
- 画像素材の自動取得
- slides_payload.jsonとの統合（現在はCSV 3列目方式のみ）

---

## 12. 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-11-30 | 初版作成（現状実装ベース） |
| 2025-11-30 | AutoHotkey連携セクション更新（C3-4完了） |
| 2025-12-01 | フォールバック戦略セクション追加（C3-3完了） |
| 2026-03-09 | Path A一本化反映、Voice自動生成plan追加 |
| 2026-03-14 | セクション10実装状況更新(全完了)、セクション11スライド配置ギャップ追加、MoviePyレガシー参照修正 |
| 2026-03-14 | SP-026: ImageItem自動配置実装。セクション11をギャップ→実装完了に更新。CSV 3列目方式 |
