# YMM4 最終ワークフロー

**最終更新**: 2026-03-17
**ステータス**: 最新 (SP-026/SP-028/SP-029/SP-030/SP-031/SP-033/SP-034 反映済み)

> Path A (YMM4一本化) が唯一の制作経路。MoviePy/Path Bは2026-03-08に完全削除済み。

---

## 1. ワークフロー概要

### 完全フロー（トピック→MP4）

```
[Python] トピック + URL入力
    ↓
[Python] リサーチ (SourceCollector) → ResearchPackage
    ↓
[Python] 台本生成 (GeminiProvider) → ScriptBundle
    ↓
[Python] 台本レビュー (Gate A, 任意) → adopted/orphaned/conflict分類
    ↓
[Python] ストック画像取得 + AI画像生成 + テキストスライド生成 (SP-033)
    ↓
[Python] CSV合成 (CsvAssembler) → timeline.csv (4列: 話者,テキスト,画像パス,アニメーション種別)
    ↓
[Python] Pre-Export検証 (SP-031, 任意) → 画像存在/形式/統計チェック
    ↓
[YMM4] NLMSlidePlugin CSVインポート + Voice生成 + スタイル自動適用
    ↓
[YMM4] プレビュー確認 → 動画出力 (Ctrl+Shift+E)
    ↓
最終 mp4
```

### 簡易フロー（手動CSV→MP4）

```
[手動] CSV作成 (2〜4列)
    ↓
[YMM4] NLMSlidePlugin CSVインポート
    ↓
[YMM4] Voice生成 → プレビュー → レンダリング → mp4
```

---

## 2. CSV仕様（4列フォーマット）

| 列 | 内容 | 必須 | 例 |
|----|------|------|-----|
| 1 | 話者名 | 必須 | れいむ, まりさ, ナレーター |
| 2 | テロップテキスト | 必須 | セリフ内容 |
| 3 | 画像ファイルパス | 任意 | 絶対パスまたはCSV相対パス |
| 4 | アニメーション種別 | 任意 | ken_burns, zoom_in, pan_left 等 |

```csv
れいむ,今日はAI技術について話しましょう,C:\slides\slide_01.png,ken_burns
まりさ,はい、最近の進化はすごいですね,C:\slides\slide_01.png,pan_left
れいむ,特に生成AIの分野が注目されています,C:\slides\slide_02.png,zoom_in
```

3列目省略時: 画像なし（音声+字幕のみ）
4列目省略時: `ken_burns`（デフォルト）

### アニメーション種別一覧（8種）

| 種別 | 動作 | 推奨用途 |
|------|------|---------|
| `ken_burns` | 緩やかなズームイン (100%→105%) | 写真・イラスト（デフォルト） |
| `zoom_in` | 強めのズームイン (100%→115%) | タイトル・区切り画面 |
| `zoom_out` | ズームアウト (115%→100%) | 全体像の提示 |
| `pan_left` | 左方向パン | 写真・風景 |
| `pan_right` | 右方向パン | 写真・風景 |
| `pan_up` | 上方向パン | 写真・風景 |
| `pan_down` | 下方向パン | 写真・風景 |
| `static` | 静止表示（フェードインのみ） | テキスト主体・データ・図表 |

---

## 3. 標準オペレーション手順 (SOP)

### Step 1: CSV作成

#### 方法A: CLI一気通貫パイプライン（推奨）

```bash
python scripts/research_cli.py pipeline \
  --topic "AI技術の最新動向" \
  --auto-review \
  --auto-images \
  --duration 5 \
  --speaker-map '{"Host1":"れいむ","Host2":"まりさ"}'
```

処理フロー: リサーチ → 台本生成 → レビュー → ストック画像/AI画像取得 → CSV合成

出力: `output_csv/` に `timeline.csv` + `images/` ディレクトリ

#### 方法B: Streamlit Web UI

```bash
streamlit run src/web/web_app.py
```

「素材パイプライン」ページでトピック入力→一気通貫実行。

#### 方法C: 手動CSV作成

テキストエディタで上記4列フォーマットに従いCSVを作成。

### Step 2: Pre-Export検証（任意）

```bash
python scripts/research_cli.py validate --csv output_csv/timeline.csv
```

チェック項目: 画像パス存在、アニメーション種別妥当性、CSV形式、列数・エンコーディング

### Step 3: YMM4でCSVインポート + Voice生成

1. YMM4を起動し、新規プロジェクトを作成
2. メニュー「NLMSlidePlugin」>「CSVタイムラインをインポート」
3. `timeline.csv` を選択
4. オプション設定:
   - 「音声を自動生成（ゆっくりボイス）」チェックボックスON（推奨）
   - 「字幕を追加」チェックボックスON（推奨）
   - BGMファイル選択（任意。`style_template.json` の `bgm` セクションから音量・フェード値を自動読み込み）
5. 「プレビュー」でCSV内容を確認
6. 「インポート」で一括実行

### Step 4: 自動適用される品質要素

インポート時に以下が自動適用される（`config/style_template.json` 駆動）:

| 要素 | 適用内容 | 設定元 |
|------|---------|--------|
| 字幕スタイル | FontSize 48, Bold, Border縁取り, 画面下部中央 | `subtitle` セクション |
| 話者別色分け | 白/黄/シアン/緑/橙/紫の6色サイクル | `speaker_colors` |
| クロスフェード | FadeIn/FadeOut 0.5秒、交互レイヤー | `crossfade` セクション |
| アニメーション | CSV4列目に応じた8種の動き | `animation` セクション |
| 画像フィット | contain方式（アスペクト比維持） | 自動計算 |
| BGM | テンプレートから音量/フェード値を読み込み | `bgm` セクション |
| タイミング | セグメント間0.3秒パディング | `timing` セクション |

### Step 5: 動画出力

1. タイムラインでプレビュー再生 → 音声・字幕・画像の同期を確認
2. 必要に応じてYMM4 GUI上で微調整
3. `ファイル > 動画出力`（Ctrl+Shift+E）でMP4生成

---

## 4. ビジュアルリソースの自動調達（SP-033）

CLI `--auto-images` オプション使用時、以下の3段階フォールバックで画像を自動取得する。

```
1. ストック画像 (Pexels/Pixabay API)
    ↓ 取得失敗
2. AI生成画像 (Gemini Imagen 3.0)
    ↓ 生成失敗
3. テキストスライド自動生成 (TextSlideGenerator)
```

| ソース | 特徴 | APIキー |
|--------|------|---------|
| Pexels | 高品質写真、200req/h | PEXELS_API_KEY |
| Pixabay | フォールバック、5000req/h | PIXABAY_API_KEY |
| Gemini Imagen | AI生成イラスト、日次制限あり | GEMINI_API_KEY |
| テキストスライド | キーワード+テーマカラーの自動生成画像 | 不要 |

セグメント分類（SegmentClassifier）により、visual/textualを自動判定し、textualセグメントには `static` アニメーションを適用。

---

## 5. スタイルテンプレート（SP-031）

`config/style_template.json` で全品質パラメータを一元管理。

| セクション | 制御対象 |
|-----------|---------|
| `video` | 解像度 (1920x1080), FPS (60) |
| `subtitle` | フォントサイズ, 位置, 装飾, 折り返し |
| `speaker_colors` | 話者別色分け (6色) |
| `animation` | Ken Burns/Zoom/Pan の強度 |
| `bgm` | BGM音量, フェードイン/アウト秒数 |
| `crossfade` | トランジション有無と秒数 |
| `timing` | セグメント間パディング, デフォルト表示秒数 |
| `validation` | 最大総尺, ギャップ/オーバーラップ警告閾値 |

バリアント: `style_template_cinematic.json`, `style_template_minimal.json`

テンプレート未検出時はビルトインデフォルト値にフォールバック。

---

## 6. パイプライン再開（SP-034）

中断したパイプラインの途中から再開可能。

```bash
python scripts/research_cli.py pipeline --topic "..." --resume
```

PipelineState がステップ単位の進捗を永続化し、失敗ステップから再実行する。

---

## 7. 音声生成の選択肢

| 手段 | 操作 | 自動化度 | 推奨場面 |
|------|------|----------|----------|
| NLMSlidePlugin Voice生成 | CSVインポート時にチェックボックスON | 半自動 | 大量セグメント |
| YMM4 台本機能 | YMM4 GUIで手動操作 | 手動 | 少量 or 細かい調整 |

Voice生成後、WavDurationReaderが音声実尺を取得し、ImageItem/TextItemのLengthを自動同期する（SP-028）。

---

## 8. エラー時リカバリ

| 事象 | 対処 |
|------|------|
| Voice Speaker未検出 | NLMSlidePluginが正規化マッチング（Kana/NameKana/Reading）で再試行。全失敗時はVoiceなしインポート |
| CSVインポートエラー | ダイアログ内ログタブ + `%LOCALAPPDATA%\NLMSlidePlugin\logs\csv_import_runtime.log` を確認 |
| 画像パス未検出 | Warning表示、該当行は画像なしでインポート続行 |
| 音声とテロップのずれ | YMM4 GUI上で調整、またはCSVのテキスト長を調整して再インポート |
| 動画出力フリーズ | YMM4再起動 → プロジェクト再読み込み → 出力のみ再実行 |
| パイプライン中断 | `--resume` オプションで失敗ステップから再開 |
| Geminiクォータ超過 | フォールバックチェーン (gemini-2.5-flash → gemini-2.0-flash → モック) が自動切替 |
| ストック画像取得失敗 | AI画像 → テキストスライドへ自動フォールバック |

---

## 9. 既知の制約

| 制約 | 詳細 | 対策 |
|------|------|------|
| Animation.From/To 使用禁止 | deprecated + レンダリング破壊 | Values in-place方式のみ使用 |
| PlaybackRate 単位 | ImageItem: 100.0、AudioItem/TextItem: 1.0 | プラグイン側で自動設定 |
| 先頭/末尾の黒フレーム | フェードイン/アウト時に背景がない | 先頭/末尾のFade値を0にするか、背景レイヤーを手動追加 |
| パン系の隙間 | fitZoom × 1.12 で余白確保済み | テンプレートの `pan_zoom_ratio` で調整可能 |
| Gemini Imagen 日次制限 | 無料枠に制限あり | stock → AI → slide の3段階フォールバック |

---

## 10. 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様（CSV形式、Voice生成、ImageItem配置）
- `docs/visual_resource_pipeline_spec.md` — ビジュアルリソースパイプライン（SP-033全Phase）
- `docs/video_quality_pipeline_spec.md` — 動画クオリティ安定化（Phase 0-4）
- `docs/material_pipeline_spec.md` — 素材直結パイプライン（トピック→CSV一気通貫）
- `docs/e2e_verification_guide.md` — E2E手動検証ガイド
- `docs/integration_test_checklist.md` — 統合検証チェックリスト（A-G）
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/workflow_boundary.md` — Python/YMM4責務境界
- `docs/TROUBLESHOOTING.md` — トラブルシューティング v2.0
