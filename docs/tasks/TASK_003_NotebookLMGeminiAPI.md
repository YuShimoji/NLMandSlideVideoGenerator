# Task: NotebookLM/Gemini API実装の完成と動作確認
Status: IN_PROGRESS
Tier: 1
Branch: main
Owner: Orchestrator → Worker
Created: 2026-01-11T15-25-22Z
Report: docs/inbox/REPORT_TASK_003_NotebookLMGeminiAPI_2026-01-30.md

## 概要

- NotebookLM/Gemini API 周辺の実装を完成させ、動作確認と証跡（テスト/レポート）を整える。

## 現状

- 状態整理と検証ログは Report に集約している（`docs/inbox/REPORT_TASK_003_NotebookLMGeminiAPI_2026-01-30.md`）。

## 次のアクション

- DoD の未達項目（外部サービス依存の動作確認/手順整理）を、停止条件に従って進めるかを判断する。

## Objective
- NotebookLM/Gemini API実装を完成させ、動作確認とテストを実施する
- 既存実装の確認と改善を行い、統合テストを実行して検証する
- APIなしワークフローを壊さないことを前提に、段階的に有効化できるようにする

## Context
- バックログ記載: A-1 NotebookLM/Gemini API（優先度: 高、状態: 設計済み）
- 既存実装状況:
  - `src/notebook_lm/audio_generator.py` に実装がある（代替ワークフロー: Gemini + TTS統合は実装済み）
  - `src/notebook_lm/gemini_integration.py` にGemini API統合がある
  - `src/core/providers/script/gemini_provider.py` にGeminiScriptProviderがある
  - `src/notebook_lm/transcript_processor.py` にNotebookLM音声アップロード実装がある（TODOコメントあり）
  - `src/notebook_lm/source_collector.py` に検索API実装がある
- バックログのサブタスク:
  - A1-1: NotebookLM API 実装（高）
  - A1-2: アップロード処理実装（高）
  - A1-3: 音声生成リクエスト実装（高）
  - A1-4: 生成状態確認実装（中）
  - A1-5: 状態確認実装（中）
  - A1-6: URL取得実装（中）
- 必要な設定: Gemini API Key
- 推奨アクション: NotebookLM API実装の完成、Gemini API統合の動作確認、APIキー未設定時のフォールバック動作確認

## Focus Area
- NotebookLM API実装の確認と完成
  - `src/notebook_lm/audio_generator.py` の実装確認と完成
  - `src/notebook_lm/transcript_processor.py` のNotebookLM音声アップロード実装の完成
  - `src/notebook_lm/source_collector.py` の検索API実装の確認
- Gemini API統合の動作確認
  - `src/notebook_lm/gemini_integration.py` の実装確認
  - `src/core/providers/script/gemini_provider.py` の実装確認
  - APIキー未設定時のフォールバック動作確認
- 統合テストの実行と検証
  - `tests/api_test_runner.py` の統合テスト実行（該当する場合）
  - テスト結果の確認と問題点の特定
- ドキュメントの更新
  - API設定ガイドの確認と必要に応じて更新
  - 動作確認手順の整備

## Forbidden Area
- 既存のCSV+WAVワークフローの破壊（CSV + WAV → 動画生成パイプラインは維持）
- 既存のGeminiScriptProviderの大幅な変更（既存の動作を壊さない）
- 他のAPI連携（Google Slides API、YouTube API）への影響
- 既存のフォールバック戦略の変更（プレースホルダー実装は維持）

## Constraints
- テスト: 主要パスのみ（網羅テストは後続タスクへ分離）
- フォールバック: 新規追加禁止（既存のフォールバック戦略を維持）
- APIキー未設定時は必ずモック・手動経路にフォールバックする方針を維持
- 調査結果はレポートとして `docs/inbox/` に保存
- NotebookLM APIの実装は、外部サービス（NotebookLM）へのアクセスが必要な場合、設定手順を整備する

## DoD
- [ ] NotebookLM API実装の動作確認が完了している
  - `src/notebook_lm/audio_generator.py` の実装確認と完成
  - `src/notebook_lm/transcript_processor.py` のNotebookLM音声アップロード実装の完成
  - `src/notebook_lm/source_collector.py` の検索API実装の確認
- [ ] Gemini API統合の動作確認が完了している
  - `src/notebook_lm/gemini_integration.py` の実装確認
  - `src/core/providers/script/gemini_provider.py` の実装確認
  - APIキー未設定時のフォールバック動作確認
- [ ] 統合テストが実行され、結果が記録されている
  - テスト結果の確認と問題点の特定
  - 認証ファイル未設定時のスキップ動作確認（期待される動作）
- [ ] APIキー未設定時のフォールバック動作が確認されている
  - モック生成へのフォールバックが実装されていることを確認
  - 既存のCSV+WAVワークフローが維持されていることを確認
- [ ] ドキュメントが確認・更新されている
  - API設定ガイドの確認と必要に応じて更新
  - 動作確認手順の整備
- [ ] docs/inbox/ にレポート（REPORT_...md）が作成されている
- [ ] 本チケットの Report 欄にレポートパスが追記されている

## Notes
- Status は OPEN / IN_PROGRESS / BLOCKED / DONE を想定
- BLOCKED の場合は、事実/根拠/次手（候補）を本文に追記し、Report に docs/inbox/REPORT_...md を必ず設定
- NotebookLM APIの実装は外部サービス（NotebookLM）へのアクセスが必要な場合、設定できない場合は停止条件として扱う
- Gemini API Keyの設定は外部サービス（Google AI Studio）へのアクセスが必要なため、設定できない場合は停止条件として扱う
- Branch 表記（main/master）の整合は `TASK_006_BranchAndPromptSSOTSync` で扱う。
