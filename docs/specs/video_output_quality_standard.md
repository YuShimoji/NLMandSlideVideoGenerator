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
- [x] 冒頭15秒にフック (「この動画で分かること」「衝撃的な事実」等) — プロンプトに指示追加済み
- [x] セグメント粒度: 15-25秒/セグメント (旧40-65秒) — 4プリセット + バリデータ更新済み
- [x] 対話テンポ: 1発話50-150文字 (旧200-400文字) — プロンプト指示更新済み
- [x] ソース引用: ナチュラルな言い回し — プロンプトに明示的排除指示追加済み
- [x] キャラクター個性: テンプレート的相槌の排除 — news/educationalプリセットに指示追加済み

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

### Phase 1: NotebookLM統合調査 (完了)

#### 調査結果 (2026-03-21)

**NotebookLM Enterprise API** (Discovery Engine API v1alpha):
- ベースURL: `https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}/`
- 認証: Google Cloud IAM + Bearer token (`gcloud auth print-access-token`)
- 前提: Google Cloud プロジェクト + discoveryengine API有効化 + NotebookLM Enterprise ライセンス

**利用可能なAPI**:
- `notebooks.create` — ノートブック作成
- `sources.batchCreate` — ソース追加 (Google Drive / テキスト / Web URL / YouTube URL)
- `sources.uploadFile` — ファイルアップロード (PDF/DOCX/PPTX/XLSX/音声/画像)
- `audioOverviews.create` — Audio Overview生成 (podcast風音声, 数分かかる, 1ノートブックにつき1つ)
- `audioOverviews.delete` — Audio Overview削除

**制約**:
- Pre-GA (v1alpha): 仕様変更の可能性あり
- Enterprise ライセンスが必要 (無料版NotebookLMにはAPI無し)
- Audio Overview: ノートブック内のソースから生成、言語指定可、フォーカスエリア指定可
- スライド生成API: **公式APIとしては未提供** (Web UIの "Slide Deck" / "Infographics" 機能はAPI非公開)

**非公式ライブラリ**:
- [notebooklm-py](https://github.com/teng-lin/notebooklm-py) — 非公式Python API (Web UIの非公開APIをリバースエンジニアリング)
- [nblm-rs](https://github.com/K-dash/nblm-rs) — Rust/Python SDK for Enterprise API
- [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) — MCP統合

**統合設計への示唆**:
1. **台本生成**: Audio Overview APIでpodcast風台本を生成可能だが、Enterprise ライセンスが必要
2. **スライド生成**: 公式APIなし。notebooklm-pyの非公式APIか、Gemini+αで独自生成が現実的
3. **現実的な統合パス**: Gemini台本生成を改善 (Phase 1.5で実施済み) + NotebookLMは手動補助ツールとして活用
4. **将来**: Enterprise API のGA化またはスライドAPI公開を待つ

### Phase 1.5: 台本品質改善 (Gemini側, 完了)

- [x] セグメント粒度: 4プリセットの avg_segment_seconds を15-25秒に短縮
- [x] segment_density: 各プリセットで3-4倍に増加
- [x] プロンプト改善: 短発話50-150文字、フック必須、自然引用、テンポ改善
- [x] バリデータ (_SEGMENT_TABLE) を新粒度に同期
- [x] テスト更新 + 新規4件追加 (計1262テスト全通過)

### Phase 2: 台本パイプライン移行

- NotebookLMベースの台本生成フローの構築
- 現行Gemini台本生成との共存/段階移行

### Phase 3: ビジュアルパイプライン移行

- NotebookLMスライド生成: 公式APIなし、手動補助または非公式APIの検討 (HUMAN_AUTHORITY)
- 著作権クリア画像検索の実装:
  - **Wikimedia Commons API** (`https://commons.wikimedia.org/w/api.php`): CC/パブリックドメイン画像の検索・ダウンロード
    - `action=query&generator=search&gsrsearch={keyword}&prop=imageinfo` でメタデータ+URL取得
    - ライセンス情報はstructured data or imageinfo extensionで取得可能
    - 無料、レート制限あり (User-Agent必須)
    - pyWikiCommons ライブラリあり
  - 既存 `stock_image_client.py` に3番目のソースとして統合が自然
  - フォールバック: Wikimedia → Pexels → Pixabay → AI生成 → テキストスライド
- PILスライド生成: 即廃止ではなくフォールバックとして維持 (HUMAN_AUTHORITY)

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
