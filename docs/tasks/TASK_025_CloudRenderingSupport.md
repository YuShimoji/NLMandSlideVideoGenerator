# Task: クラウドレンダリング対応
Status: BACKLOG (要再検討)
Tier: 3
Branch: master
Owner: TBD
Created: 2026-03-02T22:00:00+09:00
Report: (未作成)

> **注記 (2026-03-10)**: このタスクは MoviePy バックエンドを前提に計画されていましたが、
> 2026-03-08 に MoviePy は削除され、現在は YMM4 のみがレンダリングを担当しています。
> クラウドレンダリングを実装する場合は、YMM4 をクラウド環境で動作させる方式に再設計が必要です。
> このタスクは現在の仕様に合わせて見直しが必要です。

## Objective
- 動画レンダリング処理をクラウド環境（AWS/GCP/Azure）で実行可能にする
- ローカルマシンのリソース制約を解消し、大規模・高品質レンダリングを可能にする
- IEditingBackend インターフェースの拡張として、クラウドバックエンドを追加する

## Context
- **現在のレンダリング**: YMM4（Windows GUI依存、ローカル実行のみ）
- **削除済み**: MoviePy バックエンド（2026-03-08 削除）
- IEditingBackend プロトコル: `src/core/interfaces.py` で定義済
- 既存バックエンド: YMM4EditingBackend のみ
- 想定ユースケース: 長尺動画（30分+）、4K出力、バッチ処理
- **課題**: YMM4 は Windows デスクトップアプリのため、クラウド実行には仮想 Windows 環境が必要

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
  - **要再設計**: YMM4 を Windows コンテナで実行する方式、または代替レンダリングエンジンを検討
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
| 4 | フォールバック | ワーカー停止状態で実行 | ローカル YMM4 にフォールバック |
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
- YMM4 は Windows GUI アプリのため、クラウド実行には以下の選択肢がある:
  1. Windows Server コンテナ + RDP/仮想デスクトップ環境
  2. 代替レンダリングエンジン（FFmpeg 直接、または他のライブラリ）への切り替え
  3. YMM4 の CLI モードまたは API モードの調査（存在する場合）
- GPU 対応は将来タスク
- 初期はシンプルな HTTP API ベースのワーカーから始める
- コンテナオーケストレーション（ECS/Cloud Run）は第2フェーズ

## Estimated Effort
- Layer A: 15-20時間
- Layer B: 5-8時間
