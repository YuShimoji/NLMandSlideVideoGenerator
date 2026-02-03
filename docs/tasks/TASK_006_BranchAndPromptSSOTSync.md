# Task: Branch/Prompt/SSOT の整合性修正（main vs master など）
Status: DONE
Tier: 2
Branch: master
Owner: Orchestrator → Worker
Created: 2026-01-30T16:00:00Z
Report: docs/inbox/REPORT_TASK_006_BranchPromptSSOTSync_2026-02-03.md 

## Objective
- チケット/WORKER_PROMPT/HANDOVER/MISSION_LOG に記載されたブランチ名や前提の不整合を解消し、運用ミスを防ぐ

## Context
- `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` は Branch: main
- `docs/HANDOVER.md` では ブランチ: master（origin/master がデフォルト）
- `docs/inbox/WORKER_PROMPT_TASK_003_NotebookLMGeminiAPI.md` は Branch: master と記載
- リポジトリ上は `master...origin/master` が確認できている

## Focus Area
- SSOT（HANDOVER）を優先し、ブランチ表記を統一
- `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` の Branch 修正（必要なら他タスクも）
- Worker Prompt の前提（Branch/Current Phase/Report Target）を SSOT に合わせて修正

## Forbidden Area
- 実装の追加（このタスクは整合性修正のみ）

## DoD
- [x] `docs/HANDOVER.md` / `docs/tasks/*.md` / `docs/inbox/WORKER_PROMPT_*.md` のブランチ表記が矛盾しない
- [x] 修正の根拠がレポートに記載されている
