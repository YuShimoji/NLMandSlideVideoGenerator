# Task: プロジェクト状態確認と環境診断
Status: OPEN
Tier: 1
Branch: main
Owner: Orchestrator → Worker
Created: 2026-01-05T01:14:04Z
Report: 

## Objective
- プロジェクトの現在の状態を確認し、環境診断を実施する
- shared-workflows 統合後の整合性を確認する
- 次の開発タスクの優先順位を決定するための情報を収集する

## Context
- shared-workflows submodule の導入が完了
- Phase 6（変更をコミット）まで完了
- プロジェクトの主要機能は実装済み（CSV + WAV → 動画生成パイプライン）
- バックログに進行中のフェーズが存在（フェーズA: NotebookLM/Slides実装・整備）

## Focus Area
- プロジェクトの現在の状態確認
  - テストスイートの実行結果確認
  - 主要機能の動作確認
  - 依存関係の整合性確認
- 環境診断
  - `sw-doctor.js` の実行と結果分析
  - 既存のドキュメント構造の確認
  - バックログと実装状況の整合性確認
- 次のタスクの優先順位決定
  - `docs/backlog.md` の確認
  - 未完了タスクの整理
  - 優先度の高いタスクの特定

## Forbidden Area
- 既存コードの大幅な変更
- 新機能の実装
- テストスイートの変更（確認のみ）

## Constraints
- テスト: 主要パスのみ（網羅テストは後続タスクへ分離）
- フォールバック: 新規追加禁止
- 調査結果はレポートとして `docs/inbox/` に保存

## DoD
- [ ] プロジェクトの現在の状態が確認されている
- [ ] 環境診断（sw-doctor）が実行され、結果が記録されている
- [ ] テストスイートの実行結果が確認されている
- [ ] バックログと実装状況の整合性が確認されている
- [ ] 次の開発タスクの優先順位が提案されている
- [ ] docs/inbox/ にレポート（REPORT_...md）が作成されている
- [ ] 本チケットの Report 欄にレポートパスが追記されている

## Notes
- Status は OPEN / IN_PROGRESS / BLOCKED / DONE を想定
- BLOCKED の場合は、事実/根拠/次手（候補）を本文に追記し、Report に docs/inbox/REPORT_...md を必ず設定
