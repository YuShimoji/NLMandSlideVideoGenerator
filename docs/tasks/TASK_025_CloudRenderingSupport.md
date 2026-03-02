# Task: クラウドレンダリング対応
Status: BACKLOG
Tier: 3
Branch: master
Owner: TBD
Created: 2026-03-02T22:00:00+09:00
Report: (未作成)

## Objective
- 動画レンダリング処理をクラウド環境（AWS/GCP/Azure）で実行可能にする
- ローカルマシンのリソース制約を解消し、大規模・高品質レンダリングを可能にする
- IEditingBackend インターフェースの拡張として、クラウドバックエンドを追加する

## Context
- 現在のレンダリング: ローカル MoviePy + FFmpeg（CPU依存、10分動画で5-10分）
- IEditingBackend プロトコル: `src/core/interfaces.py` で定義済
- 既存バックエンド: MoviePyEditingBackend, YMM4EditingBackend
- 想定ユースケース: 長尺動画（30分+）、4K出力、バッチ処理

## Deliverables

### Layer A（AI完結）

#### A-1: クラウドレンダリング設計
- [ ] アーキテクチャ設計書作成（docs/technical/CLOUD_RENDERING_DESIGN.md）
  - コンテナ化戦略（Docker + FFmpeg）
  - ジョブキュー設計（SQS/Cloud Tasks/Redis）
  - アセット転送（S3/GCS presigned URL）
  - 結果通知（Webhook/WebSocket）

#### A-2: IEditingBackend クラウド実装
- [ ] `src/core/editing/cloud_backend.py` 作成
  - IEditingBackend プロトコル準拠
  - アセットアップロード → ジョブ投入 → ポーリング → ダウンロード
  - ローカルフォールバック対応

#### A-3: レンダリングワーカー
- [ ] `docker/render-worker/Dockerfile` 作成
  - Python + MoviePy + FFmpeg
  - REST API で render ジョブ受付
- [ ] `docker/render-worker/worker.py` 作成
  - ジョブキュー消費
  - レンダリング実行
  - 結果アップロード

#### A-4: 設定・インフラ
- [ ] `config/settings.py` にクラウドレンダリング設定追加
  - provider (local/aws/gcp/azure)
  - bucket, queue_url, worker_url
  - timeout, max_retries
- [ ] Terraform/CloudFormation テンプレート（オプション）

### Layer B（手動検証）

| # | 検証項目 | 手順 | 期待結果 |
|---|---------|------|---------|
| 1 | ローカルDocker | `docker build -t render-worker .` → `docker run` | ワーカー起動、ヘルスチェック応答 |
| 2 | ジョブ投入 | REST API でレンダリングジョブ送信 | ジョブID返却、ステータス追跡可能 |
| 3 | レンダリング完了 | サンプルデータでE2E実行 | 動画ファイル生成、ダウンロード可能 |
| 4 | フォールバック | ワーカー停止状態で実行 | ローカルMoviePyにフォールバック |
| 5 | コスト確認 | AWS/GCPでの実行コスト計測 | 10分動画あたりの概算コスト算出 |

## DoD (Definition of Done)
- [ ] IEditingBackend 準拠のクラウドバックエンド完成
- [ ] Docker ワーカーイメージがビルド・実行可能
- [ ] ローカル → クラウド → ローカル のフォールバック動作
- [ ] 設定変更のみでバックエンド切り替え可能

## Dependencies
- TASK_024（パイプラインリファクタリング）完了推奨
- Docker環境
- クラウドアカウント（AWS/GCP/Azure）

## Technical Notes
- MoviePy + FFmpeg はCPU依存のため、GPU対応は将来タスク
- 初期はシンプルなHTTP APIベースのワーカーから始める
- コンテナオーケストレーション（ECS/Cloud Run）は第2フェーズ

## Estimated Effort
- Layer A: 15-20時間
- Layer B: 5-8時間
