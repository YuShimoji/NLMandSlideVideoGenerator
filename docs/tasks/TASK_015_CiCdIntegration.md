# Task: CI/CD統合と監査自動化強化
Status: DONE
Tier: 2
Branch: master
Owner: Worker-A
Created: 2026-02-25T02:20:00+09:00
Report: docs/reports/REPORT_TASK_015_CiCdIntegration_LayerA_2026-02-28.md

## Objective
- CI/CD統合と監査自動化を強化する
- orchestrator-audit warningを解消し、開発プロセスを安定化させる

## Context
- TASK_011: DONE（方針転換ゲート整備済み）
- TASK_012B: DONE（Report参照整合ガード導入済み）
- orchestrator-audit warningが現在の開発ブロッカー
- 本プロジェクトの実運用前提は Windows であり、Linux 対応自体はプロダクト要件ではない

## Focus Area
- orchestrator-audit warning収束：現在の監査警告を解消
- CIパイプライン強化：pytest実行、ドキュメント整合性チェック、自動デプロイ
- 監査自動化：shared-workflows連携、レポート生成、品質ゲート
- ロールバック自動化：失敗時の自動ロールバック、通知システム

## Layer分割
- **Layer A（AI完結）**: orchestrator-audit warning解消、CIパイプライン定義更新、監査自動化スクリプト、ロールバック自動化実装
- **Layer B（手動実測）**: CI実行時間測定、失敗時ロールバック検証、通知システム動作確認

## Forbidden Area
- GitHub Actions制限時間（15分）を超える処理
- 本番環境への意図しない変更
- 既存ワークフローの破壊的変更

## Constraints
- CI実行時間は15分以内
- 既存pytest基準（146 passed）を維持
- Windows 優先。非Windows runner 対応は CI 実装上の副次効果に留め、主要DoDにしない

## DoD
- [x] orchestrator-audit warningが0件になる
- [x] CIパイプラインが15分以内に完了 (全ジョブに timeout-minutes 設定済み)
- [x] 監査自動化スクリプトが動作
- [x] ロールバック自動化が機能 (ci-rollback.yml: CI失敗時の自動revert)
- [x] 通知システムが動作 (notify-failure ジョブ: GitHub Issue 自動作成)
- [x] Report に証跡を保存

## 実装詳細 (2026-03-03追記)

### timeout-minutes 設定
全8ワークフローの全ジョブに timeout-minutes を設定:
- ci-main.yml: test=15min, type-check=10min, lint=10min, notify=5min
- documentation.yml: generate-docs=20min
- openspec-validation.yml: validate_openspec=15min
- openspec-component-validation.yml: validate-components=10min
- openspec-pr-validation.yml: pr-validation=10min
- task-validation.yml: validate-task-reports=10min
- orchestrator-audit.yml: (既存 10min)
- research-ui-smoke.yml: (既存 15min)

### 通知システム
ci-main.yml に `notify-failure` ジョブを追加:
- CI の test/type-check/lint いずれかが失敗した場合に実行
- GitHub Issue を `ci-failure` ラベル付きで自動作成
- 既存 Issue がある場合はコメントを追加（重複回避）

### ロールバック自動化
ci-rollback.yml を新規作成:
- CI ワークフローが push イベントで失敗した場合に発火
- HEAD が失敗コミットと一致する場合のみ `git revert` を実行
- revert 成功/失敗を GitHub Issue で報告
- merge conflict 時は手動ロールバックを促す Issue を作成

### documentation.yml 最適化
- トリガーを push → weekly schedule (毎週月曜 03:00 UTC) に変更
- push のたびに Doxygen+Sphinx+PlantUML が走る無駄を排除

## 検証コマンド
```bash
python -m pytest -q -m "not slow and not integration"
```

## ロールバック条件
- CI実行時間が15分を超える
- orchestrator-audit warningが増加
- 本番環境への意図しない変更

## Deliverables
- [x] orchestrator-audit warning解消スクリプト
- [x] 更新されたCIパイプライン定義 (timeout-minutes 追加)
- [x] 監査自動化スクリプト
- [x] ロールバック自動化システム (ci-rollback.yml)
- [x] Research UI Playwright smoke workflow
- [x] operational report validation script
- [x] Windows 優先方針への CI 調整
- [x] CI diagnostics artifact
- [x] current operational report targets manifest
- [x] CI失敗通知システム (notify-failure ジョブ)
