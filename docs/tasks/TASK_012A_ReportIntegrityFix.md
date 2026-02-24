# Task: レポート整合修正（監査警告解消）
Status: DONE
Tier: 1
Branch: master
Owner: Worker
Created: 2026-02-24T04:20:00+09:00
Report: docs/inbox/REPORT_TASK_012A_ReportIntegrityFix.md

## Objective
- `orchestrator-audit` / `report-validator` で残るレポート不整合を解消し、監査ノイズを 0 に近づける
- 後続タスクの品質判定を安定化させるため、報告文面と参照整合を先に固定する

## Context
- 現在フェーズは `P6`
- 直近監査で以下が検出済み
  - `REPORT_TASK_007_ScenarioB_2026-02-23.md`: warning
  - `REPORT_TASK_011_PolicyPivotGatePreparation.md`: validation error
- 実装本体（TASK_007/TASK_011）は完了済みのため、対象はドキュメント整合に限定する

## Focus Area
- `docs/inbox/REPORT_TASK_007_ScenarioB_2026-02-23.md` の警告原因除去
- `docs/inbox/REPORT_TASK_011_PolicyPivotGatePreparation.md` のエラー原因除去
- `docs/tasks/TASK_011_PolicyPivotGatePreparation.md` との参照整合確認
- 監査コマンド再実行と結果記録

## Forbidden Area
- 本番コードの挙動変更
- TASK_007/TASK_011 の DoD 緩和
- 破壊的 Git 操作（履歴改変、強制リセット）

## Constraints
- 変更対象は `docs/` 配下に限定する
- 修正理由を Report に明記する
- `report-validator` と `orchestrator-audit` の結果を証跡として残す

## DoD
- [x] `REPORT_TASK_007_ScenarioB_2026-02-23.md` の validator warning を解消
- [x] `REPORT_TASK_011_PolicyPivotGatePreparation.md` の validator error を解消
- [x] `node .shared-workflows/scripts/report-validator.js <対象レポート>` の結果が OK
- [x] `node .shared-workflows/scripts/orchestrator-audit.js --format text` の警告が改善
- [x] 実行コマンドと結果を `docs/inbox/REPORT_TASK_012A_ReportIntegrityFix.md` に保存

## Workerへの委譲メモ
- 文言修正の前後差分を短く説明する
- 文字化け要因がある場合は UTF-8 正規化の有無を明記する

## 停止条件
- 既存運用ルールと矛盾する修正が必要
- validator が環境依存で再現不能
- 追加の仕様判断が 3 件以上必要

## Deliverables
- 修正済みレポート 2 件
- `TASK_012A` 実施レポート
- 監査再実行ログ
