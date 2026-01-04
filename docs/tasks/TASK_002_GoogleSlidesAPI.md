# Task: Google Slides API実装の完成とOAuth認証設定
Status: OPEN
Tier: 2
Branch: main
Owner: Orchestrator → Worker
Created: 2026-01-05T05:36:25Z
Report: 

## Objective
- Google Slides API実装を完成させ、OAuth認証の設定とテストを実施する
- 既存実装の確認と改善を行い、統合テストを実行して検証する
- APIなしワークフローを壊さないことを前提に、段階的に有効化できるようにする

## Context
- バックログ記載: A-3 Google Slides API（優先度: 高、状態: 準備完了・認証待ち）
- 既存実装状況:
  - `src/slides/slide_generator.py` に実装がある
  - `src/slides/google_slides_client.py` にクライアント実装がある
  - `docs/google_api_setup.md` にセットアップガイドがある
  - `tests/api_test_runner.py` に統合テストがある
  - D-16で「Google Slides API 統合の堅牢化（OAuth refresh/利用可否チェック/フォールバックPPTX/VideoComposer PPTX参照修正）」が完了
- 必要な設定: Cloud Console + OAuth
- 推奨アクション: OAuth認証の設定とテスト

## Focus Area
- OAuth認証の設定とテスト
  - `docs/google_api_setup.md` に沿ったOAuth認証の設定
  - `scripts/google_auth_setup.py` の実行と検証
  - 認証状態の確認（`scripts/check_environment.py`）
- Google Slides API実装の確認と改善
  - `src/slides/slide_generator.py` の実装確認
  - `src/slides/google_slides_client.py` の実装確認
  - 既存実装の動作確認と改善点の特定
- 統合テストの実行と検証
  - `tests/api_test_runner.py` の統合テスト実行
  - テスト結果の確認と問題点の特定
- ドキュメントの更新
  - `docs/google_api_setup.md` の確認と必要に応じて更新
  - 動作確認手順の整備

## Forbidden Area
- APIなしワークフローの破壊（CSV + WAV → 動画生成パイプラインは維持）
- 既存のフォールバック戦略の変更（PPTXフォールバックは維持）
- 他のAPI連携（NotebookLM/Gemini API、YouTube API）への影響

## Constraints
- テスト: 主要パスのみ（網羅テストは後続タスクへ分離）
- フォールバック: 新規追加禁止（既存のフォールバック戦略を維持）
- APIキー未設定時は必ずモック・手動経路にフォールバックする方針を維持
- 調査結果はレポートとして `docs/inbox/` に保存

## DoD
- [ ] OAuth認証の設定が完了している（`google_client_secret.json` と `token.json` の確認）
- [ ] Google Slides API実装の動作確認が完了している
- [ ] 統合テストが実行され、結果が記録されている
- [ ] APIキー未設定時のフォールバック動作が確認されている
- [ ] ドキュメント（`docs/google_api_setup.md`）が確認・更新されている
- [ ] docs/inbox/ にレポート（REPORT_...md）が作成されている
- [ ] 本チケットの Report 欄にレポートパスが追記されている

## Notes
- Status は OPEN / IN_PROGRESS / BLOCKED / DONE を想定
- BLOCKED の場合は、事実/根拠/次手（候補）を本文に追記し、Report に docs/inbox/REPORT_...md を必ず設定
- OAuth認証の設定は外部サービス（Google Cloud Console）へのアクセスが必要なため、設定できない場合は停止条件として扱う
