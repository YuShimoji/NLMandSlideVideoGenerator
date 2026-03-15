# ビジュアルリソースパイプライン仕様 (SP-033)

**最終更新**: 2026-03-16
**ステータス**: Phase 1 完了。Phase 2a 実装中 (SegmentClassifier + ResourceOrchestrator + StockImageClient)。Phase 3 未着手

---

## 1. 目的

動画の視覚的多様性を高め、長尺動画でも視聴者を飽きさせないビジュアルリソース調達・配置パイプラインを構築する。

### 1.1 現状（As-Is）

- スライド画像（Google Slides → PNG）が唯一のビジュアルソース
- 全画像に同一のKen Burns 5%ズーム + フェードインを適用
- 長尺動画では画面が単調になりやすい
- 人物・図解・挿絵などの台本連動素材を調達する仕組みがない

### 1.2 目標（To-Be）

```
ScriptBundle（台本セグメント群）
    ↓
VisualResourceProvider（複数ソース対応）
    ├── SlideImageProvider（既存: Google Slides PNG）
    ├── StockImageProvider（Phase 2: Pexels/Pixabay API）
    └── AIImageProvider（Phase 3: Gemini Imagen等）
    ↓
AnimationAssigner（自動アニメーション割当）
    ↓
CsvAssembler（拡張: 4列目にアニメーション種別）
    ↓
timeline.csv (speaker,text,image_path,animation_type)
    ↓
YMM4 NLMSlidePlugin（拡張: アニメーション種別に応じた配置）
```

### 1.3 NotebookLM連携との分離

- ScriptBundleの出力形式は変更しない
- VisualResourceProviderはScriptBundleのテキスト・キーワードを入力として独立動作
- 分離境界: ScriptBundle → (分離点) → VisualResourceProvider → CsvAssembler

---

## 2. 段階的実装計画

### Phase 1: YMM4アニメーション拡張（即効性）

**目標**: 追加素材なしで視覚的多様性を向上

| 項目 | 内容 |
|------|------|
| 実装対象 | AnimationAssigner (Python) + YMM4プラグインのアニメーションバリエーション |
| 入力 | 既存のスライドPNG群 |
| 処理 | セグメント位置・内容に基づいてアニメーション種別を自動割当 |
| 出力 | CSV 4列目にアニメーション種別を記載 |
| CSV後方互換 | 4列目省略時は `ken_burns`（現行動作と同一） |

### Phase 2: ストック素材自動調達

**目標**: 無料APIで台本トピックに合った実写素材を自動取得

| 項目 | 内容 |
|------|------|
| 実装対象 | StockImageProvider (Pexels/Pixabay API) |
| 入力 | ScriptBundle → キーワード抽出 |
| 処理 | API検索 → 画像/動画DL → ライセンス確認 |
| 出力 | VisualResourcePackage (画像パス + メタデータ) |

### Phase 3: AI生成イラスト

**目標**: 台本セグメントごとにユニークなイラスト・図解を自動生成

| 項目 | 内容 |
|------|------|
| 実装対象 | AIImageProvider (Gemini Imagen / Stable Diffusion API) |
| 入力 | ScriptBundle → 画像プロンプト生成 |
| 処理 | AIイラスト生成 → 品質チェック → PNG保存 |
| 出力 | VisualResourcePackage |

---

## 3. Phase 1 詳細設計

### 3.1 アニメーション種別

| 種別 | 動作 | YMM4実装 |
|------|------|----------|
| `ken_burns` | 緩やかなズームイン (100% → 105%) | 現行実装と同一 |
| `zoom_in` | 強めのズームイン (100% → 115%) | Zoom AnimationValue |
| `zoom_out` | ズームアウト (115% → 100%) | Zoom AnimationValue |
| `pan_left` | 左方向パン | X AnimationValue (+offset → 0) |
| `pan_right` | 右方向パン | X AnimationValue (-offset → 0) |
| `pan_up` | 上方向パン | Y AnimationValue (+offset → 0) |
| `static` | 静止表示（フェードインのみ） | Zoom固定、Opacity fade |

### 3.2 AnimationAssigner ルール

セグメント列に対して、以下のルールでアニメーションを自動割当する。

1. **連続回避**: 同一アニメーションを2回連続で使用しない
2. **サイクル方式**: `ken_burns` → `pan_left` → `zoom_in` → `pan_right` → `zoom_out` → `pan_up` の順で循環
3. **同一画像対応**: 同じ画像パスが連続する場合、異なるアニメーションを適用して変化を出す
4. **静止画優先**: 画像なしセグメントには `static` を割当

### 3.3 CSVフォーマット拡張

```
# 現行 (3列)
れいむ,こんにちは,C:\slides\slide_01.png

# 拡張 (4列、後方互換)
れいむ,こんにちは,C:\slides\slide_01.png,pan_left
まりさ,それはね,C:\slides\slide_01.png,zoom_in
れいむ,なるほど,C:\slides\slide_02.png,ken_burns
```

4列目省略時のデフォルト: `ken_burns`

### 3.4 YMM4プラグイン拡張

`CsvTimelineItem` に `AnimationType` プロパティを追加。
`CsvTimelineReader` が4列目をパース。
`Ymm4TimelineImporter` / `CsvImportDialog` がアニメーション種別に応じたメソッドを呼び分ける。

| メソッド | 対象プロパティ | 状態 | 備考 |
|----------|----------------|------|------|
| `ApplyAnimationDirect` | (ディスパッチャ) | 実装済み | CSV 4列目animationType文字列で全7種をswitch分岐 |
| `ApplyZoomDirect` | Zoom | 実装済み | Values in-place方式。ken_burns (100→105%), zoom_in, zoom_out に対応 |
| `ApplyPositionDirect` | X / Y | 実装済み | Values in-place方式。pan_left, pan_right, pan_up に対応 |
| (FadeIn/FadeOut) | Opacity | 実装済み | ImageItem.FadeIn/FadeOut プロパティ (秒指定) で制御 |

**注意**: `Animation.From` / `Animation.To` は deprecated であり、実機テストでレンダリング破壊が確認されたため**使用禁止**。全アニメーションは `Values` (ImmutableList<AnimationValue>) の in-place 変更で実装すること。

pan のオフセット量は画像幅の5%を基準とする（Ken Burns zoom量と視覚的に同程度）。

---

## 4. データモデル

### Python側 (`src/core/visual/models.py`)

```python
class AnimationType(Enum):
    KEN_BURNS = "ken_burns"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    STATIC = "static"

@dataclass
class VisualResource:
    image_path: Path
    animation_type: AnimationType
    source: str  # "slide", "stock", "ai", "manual"
    metadata: Dict[str, Any]

@dataclass
class VisualResourcePackage:
    resources: List[VisualResource]
    source_provider: str
```

### C#側 (`CsvTimelineItem`)

```csharp
public string AnimationType { get; set; } = "ken_burns";
```

---

## 5. ファイル構成

### 新規ファイル

| ファイル | 役割 |
|----------|------|
| `src/core/visual/__init__.py` | モジュール初期化 |
| `src/core/visual/models.py` | AnimationType, VisualResource, VisualResourcePackage |
| `src/core/visual/animation_assigner.py` | 自動アニメーション割当ロジック |
| `tests/test_animation_assigner.py` | AnimationAssignerテスト |
| `tests/test_csv_assembler_animation.py` | CsvAssembler拡張テスト |

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/core/csv_assembler.py` | 4列目（animation_type）出力対応 |
| `ymm4-plugin/Core/CsvTimelineItem.cs` | AnimationType プロパティ追加 |
| `ymm4-plugin/Core/CsvTimelineReader.cs` | 4列目パース |
| `ymm4-plugin/TimelinePlugin/Ymm4TimelineImporter.cs` | アニメーション種別による分岐 |
| `ymm4-plugin/TimelinePlugin/CsvImportDialog.xaml.cs` | Pan/Zoom variant メソッド追加 |
| `docs/spec_csv_input_format.md` | 4列目仕様追記 |

---

## 6. Phase 1 残作業 (2026-03-16更新)

### 6.1 状況

- Python側 (AnimationAssigner, CsvAssembler 4列出力): **完了・テスト済み**
- C# CsvTimelineReader (4列パース + 相対パス解決): **完了・テスト済み**
- YMM4プラグイン: **Phase 1完了。ApplyAnimationDirect (全7種ディスパッチ) + ApplyZoomDirect + ApplyPositionDirect 実装+実機テストPASS**

### 6.2 Values in-place 方式 (実機テスト確定: 2026-03-16)

#### 経緯

1. 旧リフレクション版 (`ApplyImageFade`, `ApplyKenBurnsZoom` 等) — ImageItemの内部状態を破壊し画像が黒表示
2. Direct API (`Animation.From/To`) — CS0618 deprecated、かつ実機テストでも画像レンダリングを破壊
3. **Values in-place 方式** (`ApplyZoomDirect`) — 実機テストで正常動作を確認。現行唯一の安定手法

#### 現行実装: `ApplyZoomDirect`

```csharp
// AnimationValue は参照型 → Values[0].Value を直接変更可能
imageItem.Zoom.Values[0].Value = startZoom;

// 2値キーフレーム: ImmutableList.Add + リフレクション setter
var val1 = new AnimationValue { Value = endZoom };
var newValues = zoomValues.Add(val1);
var valuesProp = imageItem.Zoom.GetType().GetProperty("Values");
valuesProp?.SetValue(imageItem.Zoom, newValues);
imageItem.Zoom.AnimationType = AnimationType.直線移動;
```

#### 重要な制約

- `new ImageItem(path)` コンストラクタ必須。`new ImageItem { FilePath = path }` はレンダリングされない
- `Animation.From` / `Animation.To` は使用禁止（レンダリング破壊）
- `PlaybackRate = 100.0` (ImageItem固有。AudioItem/TextItemは1.0)
- `FadeIn` / `FadeOut` プロパティの単位は**秒**（フレーム数ではない）

#### InspectYmm4 による API 調査結果

- `Animation` 型: `From`(set/deprecated), `To`(set/deprecated), `AnimationType`(get/set), `Values`(ImmutableList<AnimationValue>)
- `AnimationValue`: 参照型、`.Value` プロパティで値を直接変更可能
- `AnimationType` enum: `なし`=0, `直線移動`=1, `加減速移動`=103, 各種イージング
- ImageItem デフォルト: `Opacity.Values[0].Value = 100` (不透明度100%), `Zoom.Values[0].Value = 100`

### 6.3 クロスフェード・アニメーション運用ガイドライン (実機テスト確定: 2026-03-16)

#### FadeIn/FadeOut

| 項目 | 値 | 備考 |
|------|-----|------|
| FadeIn/FadeOut | 0.5秒 | `crossfadeSeconds = 0.5` |
| 交互レイヤー | Layer N+1 / N+2 | 偶数=+1, 奇数=+2 で重なりを許可 |
| 画像開始位置 | `frame - crossfadeFrames` | 前画像と重ねてクロスフェード |
| 画像終了位置 | `frame + length + crossfadeFrames` | 次画像と重ねてクロスフェード |

#### 黒背景問題

画像がない区間、またはフェードイン/アウトで重なった画像の合計不透明度が100%未満になる区間では黒背景が表示される。対策:

- 先頭画像: FadeIn区間で前に画像がないため黒が見える → 先頭画像のみ `FadeIn = 0` にするか、背景レイヤーを別途配置
- 末尾画像: 同様に `FadeOut = 0` にするか、背景レイヤーで対処
- 中間: 交互レイヤーで前後画像が重なるため、0.5秒のクロスフェードでは実用上問題なし

#### ズームアニメーション

| 項目 | 値 | 備考 |
|------|-----|------|
| Ken Burns | 100% → 105% | 緩やかなズームイン。デフォルト |
| 補間 | 直線移動 | `AnimationType.直線移動` |
| 説明スライド | **使用禁止** | テキストが動くため視認性が低下する |

**運用ルール**:
- ズーム量は控えめにすること（5%程度）。強いズームは不要
- テキスト主体のスライド（説明・図解・一覧表など）には `static` を使用し、ズーム/パンを適用しない
- フェードとズームが同時に発生すると文字が二重に見えることがある。テキスト主体スライドでは特に注意

#### アニメーション種別選択の原則

| スライド種別 | 推奨アニメーション | 理由 |
|-------------|-------------------|------|
| 写真・イラスト（テキスト少） | ken_burns / zoom_in / pan_* | 動きで視覚的関心を維持 |
| テキスト主体（説明・図解） | static | 文字の可読性を優先 |
| データ・グラフ・表 | static | 情報読み取りを優先 |
| タイトル・区切り画面 | zoom_in (控えめ) | 印象付けとして微量のズームは許容 |

### 6.4 既知の制約と対策 (実装完了: 2026-03-17)

#### 字幕レイヤー順序

字幕（TextItem）はImageItemより大きいレイヤー番号に配置しないと背景画像の背後に隠れる。

- **現象**: 字幕が画像の背後に表示される
- **原因**: TextItemのLayer <= ImageItemのLayer
- **対策**: TextItemのレイヤーを `baseLayer + 10` に設定（**実装済み**）。ImageItemは baseLayer+1 / +2 (交互)

#### パン系アニメーションのフィット制約

パン系アニメーション（pan_left, pan_right, pan_up）は、パンオフセット分だけ画像を大きく表示しないと端に隙間が出る。

- **現象**: パン開始時に画像端と画面端の間に隙間（黒帯）
- **原因**: fitZoom (画面ぴったり) でパンすると、シフト方向の反対側が露出
- **対策**: `fitZoom * 1.12` でズーム（**実装済み**）。パン5%に対して余白6%確保
- **計算式**: `zoom >= fitZoom * (1 + 2 * panRatio)` — 両側にpanRatio分の余白が必要

### 6.5 残タスク

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| 1 | YMM4実機テスト (Zoom + FadeIn/FadeOut) | done | Values in-place方式でZoom + FadeIn/FadeOut 正常動作確認 |
| 2 | パンアニメーション (X/Y) 実装 | done | ApplyPositionDirect: Values in-place方式でX/Y実装済み |
| 3 | アニメーション種別ディスパッチ接続 | done | ApplyAnimationDirect: CSV 4列目→全7種switch分岐+全3インポートパスに接続 |
| 4 | 説明スライド判定ロジック | done | SegmentClassifierとして実装。visual/textual分類でアニメーション自動選択 |
| 5 | コミット | done | Direct API移行+リフレクション全廃+テスト修正 (dcfcba9) |
| 6 | コード品質改善 | done | 重複例外ハンドラ統合、デッドコード除去、CLAUDE.md文字化け修正 |

---

## 7. Phase 2 詳細設計

### 7.1 概要

Phase 2 はセグメント分類に基づくストック画像の自動調達と、スライドとの混合配置を実現する。
詳細設計: `docs/background_enrichment_design.md`

### 7.2 新規モジュール

| モジュール | ファイル | 状態 |
|-----------|----------|------|
| SegmentClassifier | `src/core/visual/segment_classifier.py` | done |
| VisualResourceOrchestrator | `src/core/visual/resource_orchestrator.py` | done |
| StockImageClient | `src/core/visual/stock_image_client.py` | done |
| CsvAssembler.assemble_from_package() | `src/core/csv_assembler.py` | done |

### 7.3 テスト

| テストファイル | テスト数 | 状態 |
|---------------|---------|------|
| `tests/test_segment_classifier.py` | 15 | PASS |
| `tests/test_stock_image_client.py` | 17 | PASS |
| `tests/test_resource_orchestrator.py` | 8 | PASS |
| `tests/test_csv_assembler.py` (既存) | 17 | PASS |

### 7.4 Phase 2 残タスク

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| 1 | SegmentClassifier | done | ヒューリスティクスベース分類、visual_ratio_target調整 |
| 2 | VisualResourceOrchestrator | done | スライド+ストック統合、フォールバック、連続回避 |
| 3 | StockImageClient | done | Pexels/Pixabay API、キャッシュ、クレジット生成 |
| 4 | CsvAssembler拡張 | done | assemble_from_package() メソッド追加 |
| 5 | material_pipeline.py UI統合 | pending | Streamlit UIからOrchestrator呼び出し |
| 6 | research_cli.py pipeline統合 | pending | CLI pipelineサブコマンドにOrchestrator統合 |
| 7 | E2E動作確認 | pending | APIキー設定+実際のストック画像取得テスト |
| 8 | Geminiベースキーワード抽出 | future | Phase 2c |
| 9 | 英語クエリ自動翻訳 | future | Phase 2c |

---

## 8. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-15 | 初版作成。Phase 1-3の段階的設計を定義 |
| 2026-03-15 | Phase 1 残作業・発見事項を追記。Direct API アプローチ発見 |
| 2026-03-16 | Direct API全面移行: リフレクション版廃止、7種アニメ+EnsureOpacity100をDirect API化 |
| 2026-03-16 | コード品質改善: 重複例外ハンドラ統合(6ファイル)、デッドコード除去、CLAUDE.md文字化け修正 |
| 2026-03-16 | 実機テスト結果反映: From/To→Values in-place方式に全面修正。クロスフェード/ズーム運用ガイドライン追加 |
| 2026-03-17 | ステータス更新: Phase 1 Zoom+FadeIn/FadeOut実機テストPASS。SP-027 Baseline E2E完了 |
| 2026-03-16 | Phase 2a実装: SegmentClassifier + VisualResourceOrchestrator + StockImageClient + CsvAssembler拡張。テスト78件PASS |
