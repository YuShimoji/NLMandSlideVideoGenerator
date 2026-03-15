# 背景充実化設計 (SP-033 Phase 2 詳細)

**最終更新**: 2026-03-16
**ステータス**: 設計策定中
**前提**: SP-033 Phase 1 完了 (アニメーション7種 + YMM4実機テストPASS)

---

## 1. 課題

| 問題 | 影響 |
|------|------|
| テキストスライドが唯一のビジュアルソース | 30分+動画で視覚的に単調 |
| 同一スライドが複数セグメントで共有される | 同じ画像が長時間表示 |
| テキスト主体スライドにはアニメーションを適用できない (STATIC固定) | 動きが少ない |
| ストック画像は用意されているが接続されていない | StockImageClient実装済み、パイプライン未統合 |

---

## 2. 目標

1. セグメントの内容に応じて「テキスト主体」/「ビジュアル可能」を自動分類
2. ビジュアル可能なセグメントにストック画像を自動取得・割当
3. テキスト主体セグメントには従来のスライドPNG + STATIC
4. 30分動画 (~90-120セグメント) で15-30枚のストック画像を混在させる
5. スライドとストック画像を交互配置し、視覚的変化を最大化

---

## 3. セグメント分類 (SegmentClassifier)

### 3.1 分類ルール

| 分類 | 条件 | 画像ソース | アニメーション |
|------|------|-----------|--------------|
| **textual** | データ/数値/リスト/手順/技術用語が多い | スライドPNG | STATIC |
| **visual** | 物語的/描写的/概念説明/導入/まとめ | ストック画像 | サイクル (ken_burns, pan, zoom) |

### 3.2 分類ヒューリスティクス

以下の指標で分類スコアを算出 (0.0~1.0、0.5以上でvisual):

| 指標 | visual傾向 | textual傾向 |
|------|-----------|-------------|
| 文中の数値・記号密度 | 低い | 高い |
| リスト構造 (箇条書き) | なし | あり |
| セグメント位置 | 冒頭・末尾 | 中盤 |
| section名 | "導入", "まとめ", "背景" | "手順", "比較", "データ" |
| key_points の抽象度 | 高い ("AIの可能性") | 低い ("精度92.3%") |
| content長 | 短い (概念的) | 長い (詳細説明) |

### 3.3 Gemini拡張 (将来)

ヒューリスティクスで不十分な場合、Geminiにセグメントを渡して分類+キーワード抽出を依頼可能。
初期実装はヒューリスティクスのみ。

---

## 4. VisualResourceOrchestrator

### 4.1 責務

1. SegmentClassifierでセグメントを分類
2. visual セグメント → StockImageClient で画像検索・ダウンロード
3. textual セグメント → 既存スライドPNGを割当
4. stock取得失敗 → スライドPNGにフォールバック
5. AnimationAssigner で適切なアニメーションを割当
6. VisualResourcePackage として出力

### 4.2 画像割当戦略

```
入力:
  segments = [S1(visual), S2(textual), S3(visual), S4(textual), S5(visual), S6(visual)]
  slides   = [P1, P2, P3]
  stock    = [Stock1(S1用), Stock2(S3用), Stock3(S5用), Stock4(S6用)]

出力:
  S1 → Stock1, ken_burns     (visual → ストック画像 + アニメ)
  S2 → P1,     static        (textual → スライド + STATIC)
  S3 → Stock2, pan_left      (visual → ストック画像 + アニメ)
  S4 → P2,     static        (textual → スライド + STATIC)
  S5 → Stock3, zoom_in       (visual → ストック画像 + アニメ)
  S6 → Stock4, pan_right     (visual → ストック画像 + アニメ)
```

### 4.3 ストック画像の配分

| 動画尺 | セグメント数目安 | ストック画像目標 | テキストスライド |
|--------|----------------|----------------|----------------|
| 10分 | 30-40 | 8-12 | 15-20 |
| 30分 | 90-120 | 20-35 | 30-50 |
| 60分 | 180-240 | 40-70 | 60-100 |

### 4.4 連続同一ソース回避

- ストック画像が3枚以上連続しないよう、必要に応じてスライドを挟む
- テキストスライドが5枚以上連続する場合、中間に「関連イメージ」ストック画像を挿入検討
- 同一ストック画像の再利用は原則不可 (同一画像が連続すると違和感)

### 4.5 キーワード生成

StockImageClient.search_for_segments() のクエリ生成を改善:

1. **key_points 結合**: 先頭2つ + トピック名 → "AI技術 ニューラルネットワーク"
2. **section名活用**: section="導入" → トピック名のみでイメージ検索
3. **英語翻訳**: 日本語key_pointsを英語に変換 (ストック画像サイトは英語検索が高精度)
4. **フォールバック**: クエリ生成失敗 → トピック名のみで汎用検索

---

## 5. データフロー

```
ScriptBundle (segments)
    │
    ▼
SegmentClassifier
    │  classify(segments) → List[SegmentType]
    │  ("visual" | "textual" per segment)
    │
    ▼
VisualResourceOrchestrator
    │
    ├── visual segments
    │   └── StockImageClient.search_for_segments()
    │       └── download → local cache (data/stock_images/)
    │
    ├── textual segments
    │   └── SlideImage mapping (既存ロジック)
    │
    ├── fallback (stock失敗)
    │   └── SlideImage mapping
    │
    └── AnimationAssigner
        ├── visual segments: サイクル割当 (ken_burns/pan/zoom)
        └── textual segments: STATIC
    │
    ▼
VisualResourcePackage
    │  resources[]: image_path, animation_type, source ("slide"|"stock")
    │
    ▼
CsvAssembler.assemble_from_package()  ← 新メソッド
    │
    ▼
timeline.csv (speaker, text, image_path, animation_type)
```

---

## 6. ファイル構成

### 新規

| ファイル | 役割 |
|----------|------|
| `src/core/visual/segment_classifier.py` | セグメント分類 (visual/textual) |
| `src/core/visual/resource_orchestrator.py` | スライド+ストック画像の統合調達 |
| `tests/test_stock_image_client.py` | StockImageClientテスト |
| `tests/test_segment_classifier.py` | SegmentClassifierテスト |
| `tests/test_resource_orchestrator.py` | VisualResourceOrchestratorテスト |

### 変更

| ファイル | 変更内容 |
|----------|----------|
| `src/core/csv_assembler.py` | `assemble_from_package()` メソッド追加 |
| `src/core/visual/models.py` | SegmentType enum追加 |
| `config/settings.py` | (済) STOCK_IMAGE_SETTINGS |
| `docs/visual_resource_pipeline_spec.md` | Phase 2設計セクション更新 |
| `docs/backlog.md` | SP-033 Phase 2 ステータス更新 |

---

## 7. 実装フェーズ

### Phase 2a: 基盤 (今回)
- SegmentClassifier (ヒューリスティクス)
- VisualResourceOrchestrator (スライド+ストック統合)
- StockImageClientテスト
- CsvAssembler拡張

### Phase 2b: 統合 (次回)
- material_pipeline.py UI統合
- research_cli.py pipeline サブコマンド統合
- E2E動作確認

### Phase 2c: 改善 (将来)
- Geminiベース分類
- 英語クエリ自動翻訳
- 画像品質スコアリング
- ストック動画対応

---

## 8. 設計判断

| 判断 | 選択 | 理由 |
|------|------|------|
| 初期分類手法 | ヒューリスティクス | API呼び出しコスト回避、即時実装可能 |
| ストック画像優先度 | Pexels > Pixabay | Pexelsの方が高品質、StockImageClient既実装 |
| フォールバック | スライドPNG | ストック失敗時も動画生成を止めない |
| アニメーション | visual=サイクル, textual=STATIC | Phase 1で確定済みの方針と整合 |
| 画像キャッシュ | MD5ハッシュベース | StockImageClient既実装 |
| 連続同一ソース | 3枚以上連続回避 | 視覚的単調さを防ぐ |
