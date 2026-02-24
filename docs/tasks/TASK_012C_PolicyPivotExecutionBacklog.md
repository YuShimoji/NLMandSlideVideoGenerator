# Task: 方針転換後 実行バックログ起票（再開発着手パック）
Status: DONE
Tier: 2
Branch: master
Owner: Worker
Created: 2026-02-24T04:20:00+09:00
Report: docs/inbox/REPORT_TASK_012C_PolicyPivotExecutionBacklog.md

## Objective
- TASK_011 で定義した方針転換ゲートを実行可能な開発バックログへ落とし込む
- 次フェーズの実装着手で統合漏れが出ないよう、DoD とロールバック境界を明文化する

## Context
- TASK_007: DONE（実機検証完了）
- TASK_011: DONE（方針転換ゲート整備完了）
- 残課題は「実装可能な粒度の新規チケット群」への分解

## Focus Area
- 次フェーズ対象のタスク候補抽出（最大 3 件）
- 各タスクの Focus/Forbidden/Constraints/DoD の定義
- Layer A（AI完結）/Layer B（手動実測）分割
- ロールバック条件と再開条件の明記

## Forbidden Area
- このチケット内での本番コード実装
- 既存完了チケットの再解釈による DoD 緩和
- SSOT と矛盾する新運用の追加

## Constraints
- 起票は最大 3 チケットまで
- 優先度は `High/Medium/Low` で付与
- 各チケットに検証コマンドまたは証跡パスを必ず含める

## DoD
- [x] 次フェーズ向けチケットを 1-3 件起票
- [x] 各チケットに Layer A/B 分割と停止条件を記載
- [x] 各チケットにロールバック条件を記載
- [x] 優先順位と委譲順を明記
- [x] `docs/inbox/REPORT_TASK_012C_PolicyPivotExecutionBacklog.md` に起票根拠を保存

## Workerへの委譲メモ
- チケット数は絞る（過剰分割しない）
- 方針は「品質と推進力の両立」を最優先で判断する

## 停止条件
- 前提仕様が未確定でチケット粒度が固定できない
- 依存システムの状態が不明で優先度判定不能
- 既存 SSOT と衝突する方針しか成立しない

## Deliverables
- 次フェーズ実行バックログ（1-3 チケット）
- 優先順位と委譲順の確定表
- `TASK_012C` 実施レポート
