# REPORT: TASK_015 CI/CD統合と監査自動化強化

Ticket: docs/tasks/TASK_015_CiCdIntegration.md
Status: PARTIALLY_COMPLETED
Completed: 2026-02-28T20:13:40+09:00
Actor: Codex (Orchestrator)
MCP_CONNECTIVITY: AVAILABLE
Verification Mode: AUTO_VERIFIED
Pending Items: orchestrator-audit warning 収束、CI 実行時間の GitHub 実測、ロールバック/通知系

## 概要

`TASK_015` の Layer A を縦切りで着手した。
今回は `TASK_016` で追加した Research UI Playwright スモークを GitHub Actions に組み込み、UI 回帰確認を手動依存から外すための最小 CI スライスを追加した。
Linux 対応は要件ではなく、CI runner 実装都合で一時的に混入した副次対応だったため、Windows 優先方針へ戻した。

## 現状

- 追加済み:
  - `.github/workflows/research-ui-smoke.yml`
  - `.github/workflows/orchestrator-audit.yml` の guard 強化
  - `scripts/validate_operational_reports.js`
  - `config/operational_report_targets.json`
  - OS依存の少ない Playwright テスト起動修正
  - Windows runner 失敗時の diagnostics 採取
- 自動確認済み:
  - `tests/test_research_ui_playwright.py`
  - `tests/test_alignment_export.py`
  - `tests/test_script_alignment.py`
  - `scripts/smoke_research_ui_playwright.py`
- 未完了:
  - GitHub Actions 上での初回実行結果確認
  - rollback / notification 系の実装

## Summary

CI/CD 強化の最初の縦切りとして、Research UI の Playwright スモークを GitHub Actions へ追加した。

- `research-ui-smoke` workflow を追加
  - `push` / `pull_request` / `workflow_dispatch` 対応
  - 関連パスのみに限定して実行
  - Windows runner (`windows-latest`)
  - Python 3.11
  - `pip install -r requirements.txt`
  - `python -m playwright install chromium`
  - `pytest` で Research UI smoke + 関連契約テストを実行
  - 生成された `output_csv/final_script_rp_playwright_smoke.csv` を artifact 化
  - `logs/research_ui_smoke/**` の stdout/stderr/screenshot/html を artifact 化
- Playwright テストの OS 依存を弱める修正
  - `sys.executable` を使用
  - `PYTHONPATH` を `os.pathsep` ベースで構築
  - 失敗時に screenshot / page html / streamlit stdout / stderr を保存
- `orchestrator-audit.yml` を guard 強化
  - `check_task_reports.js` を追加
  - `validate_operational_reports.js` を追加
  - HANDOVER と task report の構造検証を CI で実行
- `validate_operational_reports.js` は `config/operational_report_targets.json` を参照し、current SSOT の report のみに対象を限定
- legacy な report warning を減らすため、`TASK_013/014/016` の report metadata と section を監査仕様へ整形

## DoD 照合

| DoD 項目 | 状態 | 証跡 |
|---|---|---|
| orchestrator-audit warningが0件になる | PASS | `node .shared-workflows/scripts/orchestrator-audit.js --no-fail` → warning/anomaly なし |
| CIパイプラインが15分以内に完了 | NOT_YET | GitHub 実測待ち |
| 監査自動化スクリプトが動作 | PASS | `scripts/validate_operational_reports.js`, `scripts/check_task_reports.js`, `orchestrator-audit.yml` |
| ロールバック自動化が機能 | NOT_YET | 未着手 |
| 通知システムが動作 | NOT_YET | 未着手 |
| Report に証跡を保存 | PASS | 本レポート |

## 成果物

- `.github/workflows/research-ui-smoke.yml`
- `.github/workflows/orchestrator-audit.yml`
- `tests/test_research_ui_playwright.py`
- `scripts/smoke_research_ui_playwright.py`
- `scripts/validate_operational_reports.js`
- `config/operational_report_targets.json`

## Verification

- `PYTHONPATH=.;src python -m pytest -q tests/test_research_ui_playwright.py tests/test_alignment_export.py tests/test_script_alignment.py --tb=short`
  - 結果: `6 passed`
- `PYTHONPATH=.;src python scripts/smoke_research_ui_playwright.py`
  - 結果: `SMOKE_OK output_csv/final_script_rp_playwright_smoke.csv`
- `node scripts/validate_operational_reports.js`
  - 結果: `VALIDATION_OK (5 files)`
- `node scripts/check_task_reports.js`
  - 結果: `VALIDATION_OK`
- `node .shared-workflows/scripts/orchestrator-audit.js --no-fail`
  - 結果: `OK`
- `node .shared-workflows/scripts/report-validator.js docs/reports/REPORT_TASK_015_CiCdIntegration_LayerA_2026-02-28.md REPORT_CONFIG.yml .`
  - 結果: `OK`

## Remaining Scope

- GitHub Actions 上で `research-ui-smoke` の初回実行結果を確認
- GitHub Actions 上で guard workflow の初回実行結果を確認
- rollback / notification 系の実装判断

## 次のアクション

1. GitHub Actions 上で `research-ui-smoke` と `orchestrator-audit` の初回実行結果を確認する
2. Windows 実運用に不要な Linux 差分は追わず、必要最小限の CI 安定化に留める
3. YMM4 GUI の外部確認は別件として最後に回収する
## Decision

- 2026-02-28T21:05:00+09:00 時点で、CI 深掘りはユーザー判断により一旦停止した。
- 本レポートの Remaining Scope は未完ではあるが、Windows 実制作の即時ブロッカーではない。
- `TASK_015` は Layer A 完了後の `IN_PROGRESS_PARKED` 相当として扱い、再開は Windows 実制作側を閉じた後でよい。
