# HANDOVER

Timestamp: 2026-03-19
Actor: Claude Code (session 14 REFRESH)
Type: Session Handover

## Current Status

47仕様中44 done + 1 partial (SP-035) + 2 draft (SP-045, SP-047)。テスト 1262 passed / 0 failed。

**重要: 出力品質の設計ギャップが検出された。パイプラインは技術的に正しく動作するが、生成される動画がYouTube公開水準に達していない。**

| 領域 | 状態 | 備考 |
|------|------|------|
| 品質診断 | DONE | docs/video_quality_diagnosis.md — P1(設計レベル)3件 + P2(台本)4件 + P3(視覚)3件 |
| ドリフト分析 | DONE | docs/notebooklm_drift_analysis.md — NLM→Gemini移行の経緯と原因 |
| SP-047 仕様 | DRAFT | docs/specs/video_output_quality_standard.md — 品質基準と設計変更計画 |
| DECISION LOG | UPDATED | CLAUDE.md に6件の設計決定を追記 |
| spec-index | UPDATED | SP-047エントリ追加 (47仕様) |
| テスト | 1262 passed, 0 failed | 変更なし (今回はドキュメント・分析のみ) |

## Current Slice

**SP-047: Video Output Quality Standard**

Phase 1 (NotebookLM統合調査) が次のアクション。

## Key Findings (session 14)

### 1. 出力品質の問題

実際のパイプライン出力 (output_e2e_brave, output_e2e_30min) を検証した結果:

- テキストスライド: PIL/Pillowによる箇条書き。YouTube動画の水準ではない
- セグメント粒度: 43-64秒/セグメント。YouTube解説の標準は3-10秒ごとに視覚変化
- アニメーション: 7セグメント中4つがstatic
- 台本: 長文モノローグ、不自然なソース引用、テンプレート的相槌

### 2. NotebookLM→Geminiドリフト

プロジェクト名 "NLMandSlideVideoGenerator" はNotebookLMベースの設計を意図しているが、2025-11末のGemini代替ワークフロー導入以降、暗黙的にGeminiプロンプト駆動に完全移行。DECISION LOGに移行決定が記録されていなかった。

### 3. 設計転換 (HUMAN_AUTHORITY承認済み)

- 台本: NotebookLMベースに回帰
- スライド: NotebookLMスライド生成を活用 (PIL廃止方向)
- 画像: ウェブ上の著作権クリア画像を優先 (ストックはフォールバック)
- トランジション: 控えめに

## Git State

- Branch: `master`
- 未コミットの変更: 新規3ファイル + 更新2ファイル (docs + CLAUDE.md + spec-index.json)

## Next Actions

| 優先度 | タスク | 手動/自動 |
|--------|--------|----------|
| 1 | SP-047 Phase 1: NotebookLM統合調査 (API/スライド生成の現在の仕様) | 調査 |
| 2 | NotebookLMの台本生成をパイプラインに統合する設計 | 設計 |
| 3 | 著作権クリア画像の自動収集方法の調査・実装 | 自動 |
| 4 | SP-045: 品質基準が確定してから実行 | 手動 |

## Pending Design Decisions

1. **NotebookLMの統合レベル**: 台本+スライド両方をNotebookLMに委譲するか、台本のみか
2. **NotebookLM API**: 2026年3月時点で利用可能なAPI/統合方法は何か
3. **既存コードの扱い**: gemini_integration.py (563行)、TextSlideGenerator (708行) の廃止/縮小範囲
4. **TikTokAdapter/IPublishingQueue**: デッドコード削除 (HUMAN_AUTHORITY、session 13からの持ち越し)

## Primary References

- `docs/video_quality_diagnosis.md` — 品質診断結果
- `docs/notebooklm_drift_analysis.md` — NLM→Geminiドリフト分析
- `docs/specs/video_output_quality_standard.md` — SP-047 品質基準仕様
- `docs/spec-index.json` — 全47仕様の状態一覧
- `docs/backlog.md` — バックログ
- `CLAUDE.md` — プロジェクトコンテキスト + DECISION LOG
