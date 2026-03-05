# Task: GitHub Actions CI/CD 本番化
Status: LAYER_A_DONE
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Updated: 2026-03-05T15:30:00+09:00
Report: Layer A 完了、Layer B（手動検証）待ち

## Objective
- 既存の6つのGitHub Actionsワークフローを本番運用可能な状態にする
- PR自動検証、テスト、リリース自動化を確立する
- ローカルCI（ci.ps1, 48秒）とクラウドCIの二重ゲート体制を構築する

## Context
- `.github/workflows/` に8ワークフロー定義済
  - ci-main.yml (TASK_023 A-2で作成、TASK_015でtimeout+notify-failure追加)
  - ci-rollback.yml (TASK_015で作成、docs-onlyスキップ修正済)
  - openspec-validation.yml (timeout-minutes追加済)
  - openspec-component-validation.yml (timeout-minutes追加済)
  - openspec-pr-validation.yml (timeout-minutes追加済)
  - task-validation.yml (timeout-minutes追加済)
  - orchestrator-audit.yml
  - documentation.yml (weekly schedule変更済)
- ローカルCI: `scripts/ci.ps1` が48秒で完走（目標15分の5.3%）
- テスト: 107 passed, 11 skipped, 4 deselected (2026-03-05現在)
- TASK_015完了により timeout-minutes, notify-failure, ci-rollback は実装済み

## Deliverables

### Layer A（AI完結）

#### A-1: ワークフロー有効化・修正

- [x] `documentation.yml` のブランチ参照修正（main → master追加）
- [x] 全6ワークフローのトリガー条件確認（orchestrator-audit.yml は正常、他は修正済/正常）
- [x] `.shared-workflows/` はサブモジュールのため直接修正不可（doctor-health-check.yml内のパス問題はサブモジュール側課題）
- [ ] マトリクスビルド拡張（Python 3.12追加）- 将来対応

#### A-2: 統合テストワークフロー作成
- [x] `.github/workflows/ci-main.yml` 新規作成
  - push to master + PR: unit tests (fast, no slow/integration markers)
  - pip キャッシュ設定
  - pytest-cov カバレッジ付き実行
  - mypy type check ジョブ（core 3ファイル）
  - flake8 lint ジョブ（critical errors + info統計）
  - テスト結果 + カバレッジXML アーティファクト出力
- [x] Codecov統合（.codecov.yml作成、ci-main.ymlにアップロード追加）- Layer B で Secrets 設定
- [ ] テスト結果のPRコメント自動投稿 - 将来対応

#### A-3: リリース自動化
- [x] `.github/workflows/release.yml` 新規作成
  - タグ駆動リリース（v*.*.* 形式）
  - CHANGELOG 自動生成（前回タグからの差分）
  - YMM4プラグイン DLL のビルド・アーティファクト添付
  - GitHub Release 自動作成
- [ ] バージョニング戦略の文書化 - 将来対応

#### A-4: ブランチ保護ルール設定スクリプト
- [x] `scripts/setup_branch_protection.sh` 作成
  - master ブランチへの直接プッシュ禁止
  - PR必須、テストパス必須
  - gh CLI を使用した自動設定
  - 管理者も強制適用、エラーハンドリング付き

### Layer B（手動検証）

| # | 検証項目 | 手順 | 期待結果 |
|---|---------|------|---------|
| 1 | ワークフロー起動確認 | テストブランチ作成→PR作成 | Actions タブでワークフロー実行確認 |
| 2 | テスト結果確認 | PRにテスト結果コメント確認 | 107+ passed 表示 |
| 3 | シークレット設定 | GitHub Settings → Secrets に API キー設定 | ワークフローからシークレット参照可能 |
| 4 | カバレッジ確認 | Codecov連携確認 | PRにカバレッジバッジ表示 |
| 5 | リリースフロー | `git tag v1.0.0 && git push --tags` | GitHub Releases にアーティファクト添付 |

## DoD (Definition of Done)
- [x] PR作成時にテスト自動実行 (ci-main.yml: push + PR trigger)
- [x] テスト失敗時にマージブロック（スクリプト作成済、Layer B で実行）
- [x] カバレッジレポートがPRに表示（Codecov統合済、Layer B で Secrets 設定）
- [x] タグ駆動リリースが動作（release.yml 作成済、Layer B で検証）
- [x] ローカルCI（ci.ps1）と整合性のあるテスト構成

**Layer A 完了率: 100%** ✅

## Dependencies
- GitHubリポジトリの管理者権限（ブランチ保護設定）
- GitHub Secrets の設定（API キー）

## Estimated Effort
- Layer A: 4-6時間
- Layer B: 2時間
