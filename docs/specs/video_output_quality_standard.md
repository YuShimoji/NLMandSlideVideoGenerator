# SP-047: Video Output Quality Standard

ステータス: draft
作成日: 2026-03-19

---

## 概要

パイプラインの出力動画がYouTube公開水準に達していない問題を解決するための品質基準と設計変更仕様。

## 背景

docs/video_quality_diagnosis.md に記載の品質診断結果に基づく。
主要な問題: P1-1 (PILスライド前提が非効率), P1-2 (セグメント粒度粗い), P1-3 (スライドショー的), P2-1〜P2-4 (台本品質)。

## 設計決定 (2026-03-19 HUMAN_AUTHORITY承認済み)

### D1: 台本生成をNotebookLMベースに切替

- 現行: Geminiプロンプト駆動で台本JSONを生成 (gemini_integration.py)
- 新: NotebookLMをベースとした台本生成に移行
- 理由: NotebookLMの台本品質が高い。カスタマイズ性は低いが、ベースラインの品質が現行Geminiプロンプトを大幅に上回る

### D2: テキストスライドはNotebookLMのスライド生成を活用

- 現行: TextSlideGenerator (PIL/Pillow, 708行) で箇条書きスライドをプログラム生成
- 新: NotebookLMのスライド生成機能を活用
- PIL生成は廃止方向

### D3: 画像素材はウェブ上の著作権クリア画像を優先

- 現行: Pexelsストック画像 + Imagen AIフォールバック
- 新: テーマに合ったウェブ上の著作権クリア画像を優先使用
  - 検索対象: Creative Commons, Wikimedia Commons, 政府公開資料, パブリックドメイン
  - ストック画像はフォールバック
- 理由: ストック画像は汎用的すぎてコンテンツとの関連性が弱い

### D4: トランジションは控えめに

- 過剰なトランジション演出は避ける
- 画像素材 + 適切なアニメーション(Ken Burns等) + スライドの組み合わせが基本

## 品質基準 (目標)

### 台本
- [ ] 冒頭15秒にフック (「この動画で分かること」「衝撃的な事実」等)
- [ ] セグメント粒度: 15-30秒/セグメント (現行40-65秒から短縮)
- [ ] 対話テンポ: 1発話50-100文字 (現行200-400文字から短縮)
- [ ] ソース引用: ナチュラルな言い回し (「ソース1」「ソース3」のリテラル引用を排除)
- [ ] キャラクター個性: テンプレート的相槌の排除

### ビジュアル
- [ ] テキストスライド: NotebookLMスライド生成活用
- [ ] 画像素材: テーマに関連した著作権クリア画像 (ストック画像のみに依存しない)
- [ ] 視覚変化: 5-15秒ごとに何らかの変化 (画像切替/アニメーション/テキストオーバーレイ)
- [ ] アニメーション: 全セグメントに動きを付与 (static排除)、ただしトランジション過多にならない

### 動画構成
- [ ] 1セグメント1画像の制約を解除 (複数画像/セグメント可)
- [ ] キャラクタースプライト表示 (YMM4テンプレート側)
- [ ] テキストオーバーレイ (重要ポイントの視覚強調)

## 実装フェーズ

### Phase 1: NotebookLM統合調査 [DONE 2026-03-19]

- [x] NotebookLMのAPIアクセス方法・制約の調査
  - 結論: notebooklm-py (非公式PyPI) を採用。pip install + playwright install chromium
  - 公式Enterprise APIは有料ライセンス必須のため不採用
- [x] スライド生成機能の入出力: PPTX/PDF で取得可能
- [x] 台本取得経路: Audio OverviewはMP3のみ。Study Guide (テキスト) を台本ソースとして使用
- [x] 統合方式確定: P1+A (notebooklm-py + YMM4キャラ維持)
  - Study Guide → Gemini → CSV → YMM4 (音声合成)
  - Slides (PPTX/PDF) → PNG → YMM4 (画像トラック)

### Phase 2: 台本パイプライン移行 [NEXT]

アーキテクチャ:
```
sources (URLs/PDFs)
  → notebooklm_client.create_notebook(sources)
  → notebooklm_client.generate_study_guide()  → Markdown テキスト
  → NlmScriptConverter.convert(study_guide)   → segment CSV
  → CsvAssembler (既存)                       → YMM4 CSV
```

実装タスク:
- [ ] `pip install "notebooklm-py[browser]"` を requirements.txt に追加
- [ ] `src/notebook_lm/notebooklm_client.py` 新設
  - NotebookLMClient クラス: create_notebook / generate_study_guide / generate_slides / cleanup
  - 認証: notebooklm login (初回のみ、セッション永続化)
- [ ] `src/notebook_lm/nlm_script_converter.py` 新設
  - Study Guide (Markdown) → YMM4 CSV 変換
  - 品質基準適用 (SP-047): フック・セグメント粒度 15-30秒・発話50-100文字
  - 内部実装: Gemini を「変換エンジン」として使用
- [ ] `src/notebook_lm/gemini_integration.py` 役割変更
  - 旧: 台本生成 (Geminiプロンプト駆動)
  - 新: NLMテキスト → CSV 変換補助 (NlmScriptConverter から呼び出し)
- [ ] テスト: NotebookLM API はモック化、変換ロジックは実テスト

### Phase 3: ビジュアルパイプライン移行

アーキテクチャ:
```
notebooklm_client.generate_slides()  → PPTX/PDF
  → SlideExtractor.extract_png(pptx) → PNG list
  → 既存 ImageItem 配置パイプライン (SP-026)
```

実装タスク:
- [ ] `src/slides/slide_extractor.py` 新設: PPTX/PDF → PNG (python-pptx or pdf2image)
- [ ] TextSlideGenerator (PIL/Pillow, 708行) を廃止フラグ付きで縮退
  - NLMスライドが利用可能な場合は PIL 生成をスキップ
  - PIL は fallback として残す (NLM失敗時)
- [ ] 著作権クリア画像検索: Wikimedia Commons API 統合 (Brave Search に加えて)

### Phase 4: 品質検証

- 実際に1本の動画を完成させる
- 品質基準チェックリストによる検証
- 必要な調整の特定と実施

## 影響を受ける既存仕様

| ID | 影響 |
|---|---|
| SP-036 | Script Style Presets — NotebookLM移行後にプリセット設計を再考 |
| SP-041 | TextSlide Visual Quality — PIL生成廃止方向。NotebookLMスライドに移行 |
| SP-033 | Visual Resource Pipeline — 画像ソース拡張 (ストック→ウェブ著作権クリア) |
| SP-044 | Segment Duration Control — セグメント粒度目標の変更 (40-65秒→15-30秒) |
| SP-045 | First Publish Checklist — 品質基準の反映が必要 |
