# HANDOVER

Timestamp: 2026-03-19
Actor: Claude Code (session 15)
Type: Session Handover

## Current Status

47仕様中44 done + 1 partial (SP-035) + 2 draft (SP-045, SP-047)。
テスト 1199 passed / 3 failed (pre-existing) / 3 skipped。

新規テスト 10件 (test_notebooklm_client.py) を追加。
失敗 3件はいずれも既存の API 依存テスト (今回の変更とは無関係)。

| 領域 | 状態 | 備考 |
|------|------|------|
| SP-047 Phase 1 | DONE | notebooklm-py 調査完了。統合方式 P1+A 確定 |
| SP-047 Phase 2 | IN PROGRESS (~40%) | notebooklm_client.py + nlm_script_converter.py 作成済み |
| NotebookLMScriptProvider | UPDATED | AudioGenerator スタブ依存を全廃、新クライアント接続 |
| requirements.txt | UPDATED | notebooklm-py[browser] + python-pptx 追加 |
| DECISION LOG | UPDATED | 3件の設計決定を追記 (P1+A、Study Guide 経路) |
| テスト | 10件追加 (10/10 passed) | 直接関連テスト 66件も全 passed |

## Current Slice

**SP-047 Phase 2: 台本パイプライン移行**

実装済み:
- `src/notebook_lm/notebooklm_client.py`: NLM ラッパー (mock/本番切替、async CM)
- `src/notebook_lm/nlm_script_converter.py`: Study Guide → ScriptInfo 変換 (SP-047 品質基準組込み)
- `src/core/providers/script/notebook_lm_provider.py`: 刷新済み

残作業:
- `notebooklm login` 実認証 + 実 NLM Study Guide 取得確認 (手動)
- Phase 3: スライド PNG 変換 (python-pptx / pdf2image)
- Phase 4: 品質検証 (1本動画を完成させる)

## 設計確定事項 (session 15)

| 決定 | 内容 |
|------|------|
| 統合方式 | P1+A: notebooklm-py で Study Guide + PPTX を取得。YMM4 キャラ声維持 |
| 台本経路 | Study Guide (テキスト) → Gemini 変換 → YMM4 CSV |
| Audio Overview | 使用しない (MP3のみでテキスト取得不可) |
| 制作ペース目標 | 一晩 N 本バッチ (notebooklm-py は並列実行可能) |

## Pre-existing テスト失敗 (要対応)

| テスト | 原因 | 優先度 |
|--------|------|--------|
| test_research_pipeline::test_pipeline_auto_review | SP-044 自動拡張で 3→21 セグメント、テストが 3 を期待 | 中 |
| test_script_alignment::test_llm_alignment_skipped_without_api_key | API Key なしでも "orphaned" が返ることを期待、現在 "supported" | 中 |
| test_segment_classifier::test_classify_with_keywords_fallback | キーワード抽出の期待値不一致 | 低 |

## Git State

- Branch: `master`
- 未コミットの変更:
  - 新規: `src/notebook_lm/notebooklm_client.py`
  - 新規: `src/notebook_lm/nlm_script_converter.py`
  - 新規: `tests/test_notebooklm_client.py`
  - 更新: `src/core/providers/script/notebook_lm_provider.py`
  - 更新: `CLAUDE.md` (DECISION LOG 3件追記)
  - 更新: `docs/specs/video_output_quality_standard.md` (Phase 1 DONE + Phase 2/3 詳細)
  - 更新: `requirements.txt` (notebooklm-py + python-pptx)

## Next Actions

| 優先度 | タスク | 手動/自動 |
|--------|--------|----------|
| 1 | `pip install "notebooklm-py[browser]"` + `notebooklm login` 実行 | 手動 |
| 2 | 実 NLM 接続で Study Guide 取得確認 | 手動 |
| 3 | SP-047 Phase 3: スライド PNG 変換実装 (python-pptx) | 自動 |
| 4 | SP-047 Phase 4: 1本動画を完成させて品質基準確認 | 混在 |
| 5 | pre-existing テスト 3件の修正 | 自動 |

## Primary References

- `src/notebook_lm/notebooklm_client.py` — NLM ラッパー (新規)
- `src/notebook_lm/nlm_script_converter.py` — Study Guide → CSV 変換器 (新規)
- `docs/specs/video_output_quality_standard.md` — SP-047 仕様 (Phase 1 DONE 記録)
- `CLAUDE.md` — DECISION LOG (P1+A 等の確定事項)
- `docs/video_quality_diagnosis.md` — 品質診断結果
