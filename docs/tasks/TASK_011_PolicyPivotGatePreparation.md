# Task: 方針転換ゲート整備
Status: DONE
Tier: 1
Branch: master
Owner: Worker
Created: 2026-02-22T23:14:02+09:00
Completed: 2026-02-23T04:53:53+09:00
Report: docs/inbox/REPORT_TASK_011_PolicyPivotGatePreparation.md

## Objective
- 区切り時点で予定されている大幅な方針変更に備え、移行境界・判定基準・ロールバック条件を事前に固定する
- 実装着手前に「何を維持し、何を変更可能にするか」を明文化し、統合漏れを防止する

## Context
- 現在の主タスクは `TASK_007_YMM4PluginIntegration`（IN_PROGRESS）
- 近いタイミングで方針変更（設計/優先順位/実行順）を入れる予定
- Orchestrator は品質と推進力の両立を維持するため、変更境界を先に定義する必要がある

## Focus Area
- フェーズ境界の定義
  - P4→P5→P6 の進行条件と停止条件を再定義
  - 変更の投入ポイント（Checkpoint）を1箇所に限定
- 3段階検証基準の設計
  - 判定尺度を `★★★/★★☆/★☆☆` で統一
  - フェーズ判定とタスク判定に同一スキーマを適用
- 移行安全策の整備
  - ロールバック条件
  - 互換性維持項目（既存SSOT/既存DoD/監査要件）
  - 監査ログ更新手順（MISSION_LOG/HANDOVER/AI_CONTEXT）

## Forbidden Area
- 本チケット内での本番コード挙動変更
- `TASK_007` のDoDを暗黙に緩和すること
- SSOT（presentation/EVERY_SESSION）と矛盾する運用追加

## Constraints
- 変更境界は 1 checkpoint に集約すること
- 仮定は最大2件まで。3件以上必要なら停止して Orchestrator にエスカレーション
- 判定基準は定性的記述のみでなく、実行コマンド/成果物パスで検証可能にする

## DoD
- [x] フェーズ検証表（P4/P5/P6）を `★★★/★★☆/★☆☆` で定義
- [x] タスク検証表（最低 TASK_007/TASK_011）を `★★★/★★☆/★☆☆` で定義
- [x] 方針変更前後の境界定義（固定項目/可変項目/保留項目）を文書化
- [x] ロールバック条件と再開条件を明文化
- [x] 監査更新手順（`MISSION_LOG.md` / `docs/HANDOVER.md` / `AI_CONTEXT.md`）を明記
- [x] レポートを `docs/inbox/REPORT_TASK_011_PolicyPivotGatePreparation.md` に保存

## Workerへの委譲メモ
- 調査・分析・原因究明は必要に応じて実施し、判断理由をレポートに残す
- 変更案は「推奨案1 + 代替案2」まで提示し、トレードオフを短く比較する

## 停止条件
- Forbidden Area に触れないと完遂できない
- 仕様の仮定が3つ以上必要
- 依存追加/破壊的Git操作が必要

## Deliverables
- 方針転換ゲート定義ドキュメント（本タスクReport内）
- 3段階検証表（フェーズ/タスク）
- 実運用に適用可能な次アクション候補（1-3）
