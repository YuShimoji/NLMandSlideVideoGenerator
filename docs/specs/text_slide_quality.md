# TextSlide 視覚品質向上 (SP-041)

**最終更新**: 2026-03-18
**ステータス**: partial (Phase 1-2 完了 / Phase 3 未着手)

---

## 1. 目的

パイプライン出力の約60%を占める TextSlide (テキストスライド自動生成) の視覚品質を向上させ、
YouTube 公開動画としての視覚完成度を高める。

### 1.1 現状 (As-Is)

- 単色背景 + テキスト描画のみ (dark/light/blue の3テーマ)
- セクションタイトル + 話者ラベル + key_points/content のシンプルレイアウト
- 全セグメント同一レイアウト → 視覚的に単調
- TextSlideGenerator (text_slide_generator.py): PIL/Pillow ベースの画像生成

### 1.2 目標 (To-Be)

- 複数レイアウトパターンの自動選択で視覚的多様性を確保
- セグメント内容 (分類/key_points数) に応じたレイアウト最適化
- グラデーション背景で奥行き感を追加
- スタイルプリセット (SP-036) との連携

---

## 2. レイアウトパターン

### 2.1 Standard (現行改良)

- 用途: key_points 1-3件の標準セグメント
- 構成: タイトル + 話者 + バレットリスト
- 改善: グラデーション背景 + アクセントバー拡張

### 2.2 Emphasis (強調)

- 用途: key_points 0件 + content が短い (引用/結論)
- 構成: 大きなフォントで中央配置 + 装飾引用符
- 背景: 中央にフォーカスするビネット効果

### 2.3 TwoColumn (2カラム)

- 用途: key_points 4件以上
- 構成: 左右分割 (左: タイトル+話者、右: バレットリスト)
- 背景: 左右で微妙に異なる色調

### 2.4 Stats (統計/数値)

- 用途: content に数値・パーセンテージが含まれる
- 構成: 大きな数字 + ラベル + コンテキスト文
- 検出: 正規表現で数値パターンを検出

---

## 3. 背景バリエーション

### 3.1 グラデーション背景

現在の単色 `(20, 20, 25)` を、テーマのアクセントカラーを使った
上→下のグラデーションに変更。

```python
# 例: dark テーマのグラデーション
top_color = (20, 20, 30)      # やや明るめ
bottom_color = (10, 10, 18)   # やや暗め
accent_glow = (100, 150, 255, 30)  # アクセントカラーの微弱なグロー
```

### 3.2 テーマ連動

PLACEHOLDER_THEMES の各テーマに `gradient_top`, `gradient_bottom` を追加。
既存の `background` は単色フォールバックとして維持。

---

## 4. セグメント分類連動

SegmentClassifier の分類結果 (visual/textual) を TextSlideGenerator に渡し、
レイアウト選択に活用する。

- visual セグメント → ストック画像取得失敗時のフォールバックとして Emphasis レイアウト
- textual セグメント → Standard または TwoColumn (key_points数で判定)

---

## 5. 実装方針

### Phase 1: グラデーション背景 + Emphasis レイアウト

- `_render()` にグラデーション描画を追加
- content が短い (< 60文字) かつ key_points なし → Emphasis レイアウト
- PLACEHOLDER_THEMES にグラデーション色を追加
- テスト: 各レイアウトの画像生成確認

### Phase 2: TwoColumn + Stats レイアウト

- key_points >= 4 → TwoColumn
- 数値パターン検出 → Stats レイアウト
- レイアウト選択ロジックを `_select_layout()` メソッドに集約

### Phase 3: スタイルプリセット連携

- SP-036 のスタイルプリセット (news/educational/summary) ごとに
  レイアウト優先度やカラースキームを調整
- style_template.json にTextSlide設定セクションを追加

---

## 6. 影響範囲

- `src/core/visual/text_slide_generator.py` — 主要変更
- `config/settings.py` — PLACEHOLDER_THEMES 拡張
- `tests/test_text_slide_generator.py` — テスト追加

---

## 7. 受け入れ条件

- [x] 4種レイアウト (Standard/Emphasis/TwoColumn/Stats) が content/key_points に応じて自動選択される
- [x] グラデーション背景が全テーマ (dark/light/blue/green/warm) で動作する
- [x] 既存テスト全 PASS + 新規テスト追加 (18件 → 50件)
- [ ] スタイルプリセット (SP-036) との連携 (Phase 3)
- [ ] 30分動画の E2E で視覚的多様性が目視確認できる
