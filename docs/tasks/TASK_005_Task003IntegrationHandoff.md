# Task: TASK_003（NotebookLM/Gemini）実装の統合回収と状態同期
Status: IN_PROGRESS
Tier: 1
Branch: master
Owner: Orchestrator → Worker
Created: 2026-01-30T16:00:00Z
Report: docs/inbox/REPORT_TASK_003_NotebookLMGeminiAPI_2026-01-30.md

## 概要

- 作業ツリーに残る `TASK_003` 関連差分を棚卸しし、統合漏れを防ぐためにチケット状態とレポート紐付けを同期する。

## 現状

- `TASK_003` の Report は上記レポートへ紐付け済み。
- commit/push 方針は本チケットの `Commit/Push` セクションで未確定（選択肢を提示済み）。

## 次のアクション

- `Commit/Push` の選択肢を確定し、必要な場合は `TASK_004`（Session Gate 修復）へ進む。

## Objective
- 作業ツリー上のTASK_003関連変更の所在と意図を整理し、統合漏れを防ぐ
- `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` の Status/Report/DoD 根拠を実態に合わせて更新する（未完なら BLOCKED/IN_PROGRESS）

## Context
- 現在の作業ツリーに NotebookLM 関連の変更が存在:
  - `src/notebook_lm/audio_generator.py`
  - `src/notebook_lm/source_collector.py`
  - `src/notebook_lm/transcript_processor.py`
  - `tests/api_test_runner.py`
  - `tests/smoke_test_notebook_lm.py`（新規）
- 追加ファイル:
  - `docs/inbox/WORKER_PROMPT_TASK_003_NotebookLMGeminiAPI.md`
  - `docs/inbox/REPORT_ORCH_2026-01-30T23-05-00Z.md`

## Focus Area
- 変更点の目的を整理し、以下のいずれかの形で統合:
  - (A) TASK_003 として完了可能なら: DoD を満たす証跡（テスト/ログ/レポート）を整え、チケットを DONE
  - (B) 完了不可なら: 事実とブロッカーを明記し、チケットを BLOCKED/IN_PROGRESS
- `python -m pytest -q -m "not slow and not integration" --durations=20` は現状 pass（102 passed）であることを根拠に残す

## Forbidden Area
- 既存のCSV+WAVワークフローの破壊
- GeminiScriptProvider の大幅変更

## Constraints
- 外部サービス（NotebookLM/Gemini）アクセスが必要な検証は、手順のドキュメント化ができない限り無理に実行しない

## DoD
- [x] 変更の意図/影響範囲が `docs/inbox/REPORT_TASK_003_*.md` または相当レポートに記録されている
- [x] `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` の Status と Report が実態に一致
- [ ] commit/push の要否が明確（GitHubAutoApprove=true）

## Commit/Push

- 現状の作業ツリーには `src/notebook_lm/*` とテスト関連の未コミット差分が残っている。
- 取り扱い方針は次のいずれかで確定する必要がある（`GitHubAutoApprove: true` のため push まで可能だが、実装差分を含むため判断を明確化する）。
  - 選択肢1: 変更を採用して commit/push（次: `TASK_004` で session-end-check OK を目指す）
  - 選択肢2: 変更を採用するが commit のみ（push はレビュー後）
  - 選択肢3: 変更は未確定として stash/破棄し、`TASK_003` を BLOCKED にして調査へ戻す

## Notes
- 調査フェーズになった場合は、禁止事項に従い「DONEにしない」
