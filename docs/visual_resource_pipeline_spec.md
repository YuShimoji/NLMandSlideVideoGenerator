# ビジュアルリソースパイプライン仕様 (SP-033)

**最終更新**: 2026-03-15
**ステータス**: Phase 1 実装中

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

| メソッド | 対象プロパティ | 備考 |
|----------|----------------|------|
| `ApplyKenBurnsZoom` | Zoom | 既存 (100% → 105%) |
| `ApplyZoomIn` | Zoom | 新規 (100% → 115%) |
| `ApplyZoomOut` | Zoom | 新規 (115% → 100%) |
| `ApplyPanLeft` | X | 新規 (+panOffset → 0) |
| `ApplyPanRight` | X | 新規 (-panOffset → 0) |
| `ApplyPanUp` | Y | 新規 (+panOffset → 0) |
| `ApplyImageFade` | Opacity | 既存（全種別で使用） |

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

## 6. Phase 1 残作業 (2026-03-15時点)

### 6.1 状況

- Python側 (AnimationAssigner, CsvAssembler 4列出力): **完了・テスト済み**
- C# CsvTimelineReader (4列パース + 相対パス解決): **完了・テスト済み**
- YMM4プラグイン アニメーション適用: **画像表示は確認済み、アニメーション効果は未確認**

### 6.2 発見事項: YMM4 API アプローチ

リフレクション経由の AnimationValue 操作に問題がある:
- `ApplyImageFade`: Opacity の Values[0]=0% を設定後、Values[1]=100% のキーフレーム追加が失敗し、画像が透明になる
- `ApplyKenBurnsZoom`: Zoom の AnimationValue 設定は成功するが、実際の視覚効果が確認できていない

**代替アプローチを発見**: `imageItem.Zoom.From = fitZoom` でプロパティに直接アクセスできる。
`Animation.From` は YMM4 では「旧形式」(CS0618警告) だが動作する。

### 6.3 残タスク

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| 1 | Direct API テスト | pending | `Zoom.From/To` で画像ズームが確認できるかYMM4で検証 |
| 2 | アニメーション7種実装 | pending | 方針確定後。Direct API (`.From/.To`) or リフレクション |
| 3 | Opacity 方針確定 | pending | `EnsureOpacity100` で十分か、`Opacity.From` 直接設定に切替か |
| 4 | FadeIn/FadeOut 確認 | pending | crossfadeFrames がYMM4で正常に動作するか検証 |
| 5 | 診断ログ削除 | pending | 動作確認後に不要な WriteRuntimeLog を整理 |
| 6 | コミット整理 | pending | 未コミット差分 (CsvImportDialog + Ymm4TimelineImporter + InspectYmm4) |

### 6.4 推奨進め方

1. **Step 1**: `Zoom.From = fitZoom` のみで画像表示 + ズーム効果を確認 (現在のコード状態)
2. **Step 2**: 確認できたら `Zoom.To = fitZoom * 1.05` を追加し、ズームアニメーションを検証
3. **Step 3**: 成功すれば全7種を Direct API 方式に移行。`ApplyKenBurnsZoom` 等のリフレクション版は廃止
4. **Step 4**: `X.From/To`, `Y.From/To` でパンアニメーション実装
5. **Step 5**: `Opacity.From = 100.0` でフェード不要を確定するか、`Opacity.From=0/To=100` でフェード復活
6. **Step 6**: 診断ログ整理、コミット

---

## 7. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-15 | 初版作成。Phase 1-3の段階的設計を定義 |
| 2026-03-15 | Phase 1 残作業・発見事項を追記。Direct API アプローチ発見 |
