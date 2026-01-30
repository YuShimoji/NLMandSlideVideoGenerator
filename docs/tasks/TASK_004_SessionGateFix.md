# Task: Session Gate 修復（git clean + Orchestrator Report テンプレ準拠）
Status: OPEN
Tier: 1
Branch: master
Owner: Orchestrator → Worker
Created: 2026-01-30T16:00:00Z
Report: 

## Objective
- session-end-check の NOT OK を解消し、セッション完了条件を満たせる状態に戻す
- 最新の Orchestrator Report をテンプレ準拠（ユーザー返信テンプレ含む）で作成し直す

## Context
- 現状 `git status -sb` が汚れている（M/?? が残っている）
- `node .shared-workflows/scripts/session-end-check.js --project-root . --no-fetch` が NOT OK
  - 作業ツリーがクリーンではない
  - 最新 Orchestrator Report にユーザー返信テンプレ（完了判定 + 選択肢1-3）がない
- `docs/inbox/REPORT_ORCH_2026-01-30T23-05-00Z.md` は report-validator 上はOKだが、運用SSOTの要件（ユーザー返信テンプレ）を満たしていない

## Focus Area
- `git status -sb` をクリーンにする（不要ファイルの整理/差分の扱いを決める）
- `.shared-workflows/templates/ORCHESTRATOR_REPORT_TEMPLATE.md` に準拠した `docs/inbox/REPORT_ORCH_<ISO8601>.md` を新規作成
- `node .shared-workflows/scripts/report-validator.js <report> REPORT_CONFIG.yml .` を実行し、結果をレポートへ追記（必要なら `--append-to-report`）
- `node .shared-workflows/scripts/session-end-check.js --project-root . --no-fetch` を再実行し、Result: OK を確認

## Forbidden Area
- 既存のCSV+WAV主フローの挙動変更
- 外部サービス設定（APIキー/OAuth）を必須にする変更

## Constraints
- 破壊的操作（reset/clean 等）を行う場合は、実行前に根拠と影響範囲をレポートへ明記

## DoD
- [ ] `node .shared-workflows/scripts/session-end-check.js --project-root . --no-fetch` が Result: OK
- [ ] `docs/inbox/REPORT_ORCH_<ISO8601>.md` がテンプレ準拠（ユーザー返信テンプレ含む）
- [ ] `docs/inbox/REPORT_...md` に検証コマンド結果が記載されている
- [ ] 変更がある場合は commit 済み（push要否も明記）

## Notes
- 作業内容の判断が必要な場合は、選択肢（採用理由/リスク）を3案提示して停止すること
