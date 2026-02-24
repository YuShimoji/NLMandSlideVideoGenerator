# Task: Report参照整合ガード導入（pre-commit/CI）
Status: DONE
Tier: 1
Branch: master
Owner: Worker
Created: 2026-02-24T04:20:00+09:00
Report: docs/inbox/REPORT_TASK_012B_ReportLinkGuard.md

## Objective
- `docs/tasks/*` の `Report:` 参照切れを自動検知し、再発を防止する
- レポート整合のチェックを手作業依存から CI/pre-commit へ移行する

## Context
- 過去監査で `Report:` 参照不整合が断続的に発生
- `scripts/check_task_reports.js` は存在するが常時ゲートとして未固定
- P6 での品質維持には、ルール化された自動検証が必要

## Focus Area
- `scripts/check_task_reports.js` の運用ルール確定
- pre-commit または GitHub Actions のいずれかに検証を常設
- 失敗時メッセージを人間が修正しやすい内容へ整備
- README か運用ドキュメントに実行方法を追記

## Forbidden Area
- 本チケット内での本番機能仕様変更
- 既存タスク定義の意味変更
- `docs/tasks/` の履歴を壊す一括削除

## Constraints
- 既存 CI フローと競合しないこと
- ローカル実行コストは軽量であること
- 導入後に最低 1 回は実行ログを提示すること

## DoD
- [x] `Report:` 参照不整合を検知できる自動チェックが有効化される
- [x] pre-commit または CI のどちらかで失敗時に非 0 終了となる
- [x] 正常系/異常系の検証結果を report に添付
- [x] 実行手順をドキュメントに反映
- [x] `docs/inbox/REPORT_TASK_012B_ReportLinkGuard.md` に証跡を保存

## Workerへの委譲メモ
- 推奨案 1 と代替案 1 を短く比較して採択理由を明記する
- 既存開発速度を落とさない設計を優先する

## 停止条件
- CI 権限不足で設定反映不可
- pre-commit 運用ルールが未合意で導入判断不可
- ツール不在によりチェック自体を実行できない

## Deliverables
- 自動検証の設定変更一式
- 運用ドキュメント更新
- `TASK_012B` 実施レポート
