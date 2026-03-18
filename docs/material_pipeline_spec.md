# 素材直結パイプライン仕様 (SP-032)

**最終更新**: 2026-03-15
**ステータス**: Phase A/B/C/D完了

---

## 1. 目的

「CSV手動作成 + ファイル手動配置」を排除し、トピック入力から YMM4 インポート可能状態までを一気通貫で実行するパイプラインを構築する。

### 1.1 現状（As-Is）

```
[手動] トピック定義
  ↓
[自動] SourceCollector: Web資料収集 (Brave Search API)
  ↓
[手動/自動] 台本生成 (GeminiProvider or NotebookLMProvider)
  ↓
[自動] SlideGenerator: Google Slides → PNG化
  ↓
  ★ 断絶1: PNG群のパスがCSVに自動で入らない ★
  ↓
[手動] CSV作成（話者, テキスト, 画像パス）
  ↓
[自動] YMM4EditingBackend: プロジェクト生成 + CSVコピー
  ↓
  ★ 断絶2: YMM4 GUIでCSVインポートを手動実行 ★
  ↓
[半自動] NLMSlidePlugin: タイムライン配置 + Voice生成
  ↓
[手動] YMM4 レンダリング → mp4
```

### 1.2 目標（To-Be）

```
[手動] トピック入力 + 資料URL指定
  ↓
[自動] Step 1: リサーチ (SourceCollector)
  ↓
[自動] Step 2: 台本生成 (GeminiProvider, 資料注入)
  ↓
[品質G] Gate A: 台本レビュー (Streamlit UI, 任意スキップ)
  ↓
[自動] Step 3: スライド生成 (SlideGenerator → PNG群)
  ↓
[品質G] Gate B: スライドレビュー (将来: Gemini Vision評価)
  ↓
[自動] Step 4: CSV自動合成 (PNG + 台本 → 話者,テキスト,画像パス)
  ↓
[自動] Step 5: YMM4プロジェクト生成 (CSV埋め込み済み)
  ↓
[手動] YMM4起動 → NLMSlidePlugin → インポート → Voice生成 → レンダリング
```

---

## 2. 全ステップ仕様

### Step 1: リサーチ（資料収集）

| 項目 | 内容 |
|------|------|
| 実行主体 | SourceCollector (src/notebook_lm/source_collector.py) |
| 入力 | トピック文字列, シードURL群, 検索クエリ群 |
| 処理 | Brave Search API → HTML解析 → 信頼度/関連度スコアリング |
| 出力 | ResearchPackage (JSON) |
| 自動/手動 | **自動** |
| 品質保証 | relevance_score + reliability_score でソート。低スコア除外 |
| 既存実装 | **実装済み** |

**情報源の信頼性について:**
- SourceCollectorはWeb検索結果を取得し、ドメイン信頼度とキーワード関連度でスコアリングする
- Gemini APIのモデル内部知識だけに依存しない設計（外部資料を明示的に注入）
- 信頼度の低い情報源は自動除外（threshold設定可能）

### Step 2: 台本生成

| 項目 | 内容 |
|------|------|
| 実行主体 | GeminiProvider or NotebookLMProvider |
| 入力 | ResearchPackage, トピック |
| 処理 | AI台本生成 → セグメント構造化 |
| 出力 | ScriptBundle (JSON: segments[].speaker, .content, .key_points) |
| 自動/手動 | **自動**（プロバイダ選択は手動） |
| 既存実装 | **実装済み** |

**2つの経路:**

| 経路 | 情報源 | 特徴 |
|------|--------|------|
| GeminiProvider | SourceCollectorの資料をプロンプトに注入 | 高速、カスタマイズ自由 |
| NotebookLMProvider | ユーザーがNotebookLMに手動で資料投入 | 資料忠実度が高い、手動ステップあり |

### Gate A: 台本レビュー（品質ゲート）

| 項目 | 内容 |
|------|------|
| 実行主体 | ScriptAlignmentAnalyzer (src/notebook_lm/script_alignment.py) |
| 処理 | 台本の各セグメントを資料と照合 → supported/orphaned/conflict分類 |
| UI | Streamlit研究ページ (src/web/ui/pages/research.py) |
| 自動/手動 | **半自動**: 分析は自動、orphaned/conflict判定は手動レビュー |
| スキップ | 可能（品質ゲートは任意） |
| 既存実装 | **実装済み** |

### Step 3: スライド生成

| 項目 | 内容 |
|------|------|
| 実行主体 | SlideGenerator (src/slides/slide_generator.py) |
| 入力 | TranscriptInfo（台本から変換） |
| 処理 | ContentSplitter → Google Slides API → プレゼンテーション作成 → PNG化 |
| 出力 | SlidesPackage (PNG群 + メタデータ) |
| 自動/手動 | **自動** |
| 既存実装 | **実装済み** |

**PNG化の詳細:**
- Google Slides APIでプレゼンテーション作成
- Drive API経由でPPTXダウンロード
- 各スライドをPNG画像として保存: `data/slides/slide_0001.png`, `slide_0002.png`, ...

### Gate B: スライドレビュー（品質ゲート）

| 項目 | 内容 |
|------|------|
| 現状 | **未実装** |
| 将来設計 | Gemini Vision APIでスライド画像を評価 → 可読性/情報量/デザインスコア |
| 初期実装 | 無検閲（スキップ）。人手レビューの場合はStreamlit UIでPNG一覧表示 |

### Step 4: CSV自動合成 ★実装済み★

| 項目 | 内容 |
|------|------|
| 実行主体 | CsvAssembler (`src/core/csv_assembler.py`) |
| 入力 | ScriptBundle (台本セグメント群) + SlidesPackage (PNG群) |
| 処理 | セグメントとスライドを1:Nマッチング → CSV 3列形式で出力 |
| 出力 | timeline.csv (話者,テキスト,画像絶対パス) |
| 自動/手動 | **自動** |
| 既存実装 | **実装済み** (a764e7e) + SP-033アニメーション拡張 |

**マッチング戦略:**

```
入力:
  segments = [S1, S2, S3, S4, S5, S6]  (6セグメント)
  slides   = [P1, P2, P3]              (3スライド)

戦略: 均等分割 (round-robin)
  S1 → P1, S2 → P1    (スライド1が2セグメント分表示)
  S3 → P2, S4 → P2    (スライド2が2セグメント分表示)
  S5 → P3, S6 → P3    (スライド3が2セグメント分表示)

出力CSV:
  Speaker1,テキスト1,C:\data\slides\slide_0001.png
  Speaker2,テキスト2,C:\data\slides\slide_0001.png  ← 同じスライド
  Speaker1,テキスト3,C:\data\slides\slide_0002.png
  Speaker2,テキスト4,C:\data\slides\slide_0002.png
  Speaker1,テキスト5,C:\data\slides\slide_0003.png
  Speaker2,テキスト6,C:\data\slides\slide_0003.png
```

**Edge cases:**
- セグメント0件 → エラー
- スライド0件 → 画像パス空欄でCSV生成（後方互換）
- セグメント < スライド → 1:1マッチ、余剰スライドは無視

### Step 5: YMM4プロジェクト生成 ★実装済み★

| 項目 | 内容 |
|------|------|
| 実行主体 | YMM4EditingBackend (`src/core/editing/ymm4_backend.py`) |
| 拡張内容 | Step 4で生成したCSVを `text/timeline.csv` に自動配置 |
| 変更箇所 | CsvAssembler.from_script_bundle() 呼び出しを統合済み |
| 既存実装 | **実装済み** (a764e7e) |

**ユーザー操作（Step 5完了後）:**
1. YMM4起動
2. 生成された `project.y4mmp` を開く
3. NLMSlidePlugin → CSV Timeline Import
4. `text/timeline.csv` を選択 → インポート
5. Voice生成（自動） → 微調整 → レンダリング

---

## 3. データフロー図

```
トピック + URL
    │
    ▼
SourceCollector ─→ ResearchPackage (JSON)
    │
    ▼
GeminiProvider ◄─ ResearchPackage
    │
    ▼
ScriptBundle (JSON)
    │
    ├─→ [Gate A] ScriptAlignmentAnalyzer (任意)
    │
    ▼
SlideGenerator ─→ SlidesPackage (PNG群)
    │
    ├─→ [Gate B] スライドレビュー (将来)
    │
    ▼
CsvAssembler ◄── ScriptBundle + SlidesPackage
    │
    ▼
timeline.csv (話者,テキスト,画像パス)
    │
    ▼
YMM4EditingBackend ─→ ymm4_project_YYYYMMDD/
    │                    ├── project.y4mmp
    │                    ├── text/timeline.csv
    │                    ├── timeline_plan.json
    │                    └── slides_payload.json
    │
    ▼
[手動] YMM4 → NLMSlidePlugin → インポート → Voice → レンダリング → mp4
```

---

## 4. 実装計画

### Phase A: CsvAssembler実装 ★完了★

`src/core/csv_assembler.py` 実装済み (a764e7e)。SP-033 アニメーション自動割当も統合済み。

- `assemble()`: セグメント群 + PNG群 → CSV 4列形式 (話者, テキスト, 画像パス, アニメーション種別)
- `from_script_bundle()`: ScriptBundle辞書 + スライドディレクトリから一括生成
- テスト: `tests/test_csv_assembler.py`

### Phase B: YMM4EditingBackend拡張 ★完了★

`ymm4_backend.py` に CsvAssembler.from_script_bundle() 呼び出しを統合済み。

### Phase C: CLI pipeline統合 ★完了★

`scripts/research_cli.py pipeline` サブコマンドで一気通貫実行が可能。

```
python scripts/research_cli.py pipeline \
  --topic "トピック" \
  --auto-review \
  --slides-dir path/to/slides \
  --speaker-map '{"Host1":"れいむ","Host2":"まりさ"}'
```

実行フロー: collect → script gen (GeminiProvider) → align → review → CsvAssembler

- テスト: `tests/test_research_pipeline.py` (3件)

### Phase D: Streamlit UIワンクリック統合 (完了)

専用ページ `src/web/ui/pages/material_pipeline.py` として実装。

- トピック入力 → collect → script gen → align → review → CsvAssembler の一気通貫UI
- パラメータ: トピック、シードURL、最大ソース数、自動レビュー切替
- 詳細オプション: スライドPNGディレクトリ、話者マッピングJSON
- 結果表示: CSVプレビュー、ダウンロード、生成物一覧
- サイドバー: `📦 素材パイプライン` メニューからアクセス

---

## 5. 品質ゲート設計（将来拡張）

### Gate A: 台本品質（実装済み）

- ScriptAlignmentAnalyzer: supported/orphaned/conflict 分類
- Streamlit UIでインタラクティブレビュー
- ゲート通過条件: orphaned率 < 30%, conflict = 0 (推奨)

### Gate B: スライド品質（将来）

- Gemini Vision APIによる自動評価
- 評価軸: 可読性、情報密度、デザイン一貫性
- リライトループ: 低品質スライドを自動再生成

### Gate C: タイムライン品質（Phase 4で実装予定）

- SP-031: Pre-Export Validation
- レイヤー重複、無音区間、画像ファイル存在確認

---

## 6. 話者マッピング

CSV内の話者名はYMM4のボイス名と一致する必要がある。

| 台本上の話者 | YMM4ボイス名 | 備考 |
|------------|-------------|------|
| Host1 / Speaker1 | れいむ (YukkuriVoice) | デフォルトマッピング |
| Host2 / Speaker2 | まりさ (YukkuriVoice) | デフォルトマッピング |
| ナレーター | れいむ (YukkuriVoice) | デフォルトフォールバック |

マッピングはCsvAssembler実行時にオプション指定。
NLMSlidePluginのVoiceSpeakerDiscoveryと連携。

---

## 7. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-14 | 初版作成。全ステップの自動/手動/品質ゲートを定義 |
| 2026-03-15 | Phase A/B完了反映。研究ワークフロー Phase 1-4 完了。CLI review コマンド追加 |
| 2026-03-15 | Phase C完了: CLI pipeline サブコマンド (collect→script→align→review→CsvAssembler一気通貫) |
