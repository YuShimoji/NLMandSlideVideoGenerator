# Task: GitHub Actions CI/CD 本番化
Status: OPEN
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Report: (未作成)

## Objective
- 既存の6つのGitHub Actionsワークフローを本番運用可能な状態にする
- PR自動検証、テスト、リリース自動化を確立する
- ローカルCI（ci.ps1, 48秒）とクラウドCIの二重ゲート体制を構築する

## Context
- `.github/workflows/` に6ワークフロー定義済（未稼働）
  - openspec-validation.yml
  - openspec-component-validation.yml
  - openspec-pr-validation.yml
  - task-validation.yml
  - orchestrator-audit.yml
  - documentation.yml
- ローカルCI: `scripts/ci.ps1` が48秒で完走（目標15分の5.3%）
- テスト: 103 passed, 7 skipped, 4 deselected

## Deliverables

### Layer A（AI完結）

#### A-1: ワークフロー有効化・修正
- [ ] 全6ワークフローのトリガー条件見直し（push/PR/manual）
- [ ] Python環境セットアップステップの統一
  - venv作成、requirements.txt インストール
  - キャッシュ設定（pip, venv）
- [ ] テストステップの統一（pytest markers 使い分け）
- [ ] マトリクスビルド検討（Python 3.11/3.12）

#### A-2: 統合テストワークフロー作成
- [ ] `.github/workflows/ci-main.yml` 新規作成
  - push to master: full test suite
  - PR: fast tests only
  - 環境変数/シークレット設定テンプレート
- [ ] テストカバレッジレポート（pytest-cov → Codecov）
- [ ] テスト結果のPRコメント自動投稿

#### A-3: リリース自動化
- [ ] `.github/workflows/release.yml` 新規作成
  - タグ駆動リリース（v*.*.* 形式）
  - CHANGELOG 自動生成
  - YMM4プラグイン DLL のビルド・アーティファクト添付
- [ ] バージョニング戦略の文書化

#### A-4: ブランチ保護ルール設定スクリプト
- [ ] `scripts/setup_branch_protection.sh` 作成
  - master ブランチへの直接プッシュ禁止
  - PR必須、テストパス必須
  - gh CLI を使用した自動設定

### Layer B（手動検証）

| # | 検証項目 | 手順 | 期待結果 |
|---|---------|------|---------|
| 1 | ワークフロー起動確認 | テストブランチ作成→PR作成 | Actions タブでワークフロー実行確認 |
| 2 | テスト結果確認 | PRにテスト結果コメント確認 | 103+ passed 表示 |
| 3 | シークレット設定 | GitHub Settings → Secrets に API キー設定 | ワークフローからシークレット参照可能 |
| 4 | カバレッジ確認 | Codecov連携確認 | PRにカバレッジバッジ表示 |
| 5 | リリースフロー | `git tag v1.0.0 && git push --tags` | GitHub Releases にアーティファクト添付 |

## DoD (Definition of Done)
- [ ] PR作成時にテスト自動実行
- [ ] テスト失敗時にマージブロック
- [ ] カバレッジレポートがPRに表示
- [ ] タグ駆動リリースが動作
- [ ] ローカルCI（ci.ps1）と整合性のあるテスト構成

## Dependencies
- GitHubリポジトリの管理者権限（ブランチ保護設定）
- GitHub Secrets の設定（API キー）

## Estimated Effort
- Layer A: 4-6時間
- Layer B: 2時間
