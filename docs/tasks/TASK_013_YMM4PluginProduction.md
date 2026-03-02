# Task: YMM4プラグイン本番化
Status: DONE
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-02-25T02:20:00+09:00
Report: docs/inbox/REPORT_TASK_013_YMM4PluginProduction.md

## Objective
- TASK_007 で完了した YMM4 CSVインポート機能を、本番運用可能な品質まで引き上げる
- 大規模CSV、エラー耐性、運用自動化を強化して、再現性のある運用手順を確立する

## Context
- TASK_007: DONE（実機検証完了）
- TASK_012A/B/C: DONE（監査整合と次フェーズ起票完了）
- 本チケットは本番化タスク（性能・信頼性・運用性）を対象とする

## Focus Area
- 大規模CSV（1000行）取り込みの性能改善
- エラー/異常系（欠損ファイル・不正行・エンコーディング）の検出と可視化
- デプロイ/検証の自動化
- 運用ドキュメント整備

## Forbidden Area
- YMM4 本体APIの変更
- 既存CSV/WAVフロー仕様の破壊的変更
- Windows以外の実行環境を前提にした設計変更

## Constraints
- .NET 9互換
- YMM4 v4.33+ 互換
- 既存Pythonテスト（`109 passed`）を壊さない

## Layer Division
- `Layer A`（AI完結）: CSV読み込み改善、エラー収集、ベンチマーク、デプロイスクリプト
- `Layer B`（手動実測）: 実機での1000行インポート、体感性能、運用手順検証

## Current Progress
- [x] CSV読み込み結果モデル追加（`ymm4-plugin/Core/CsvReadResult.cs`）
- [x] WAV再生時間取得ユーティリティ追加（`ymm4-plugin/Core/WavDurationReader.cs`）
- [x] `CsvTimelineReader` のストリーミング読み込み・エラー収集を実装
- [x] Dialog UI/非同期化・進捗表示（CsvImportDialog.xaml 実装済み）
- [x] テストプロジェクト再構成と本番テスト追加（13テスト全通過）
- [x] 自動デプロイスクリプト実装（scripts/deploy_ymm4_plugin.ps1）
- [x] ドキュメント更新と最終レポート（SETUP_GUIDE.md + REPORT）

## DoD
- [x] 1000行CSVインポートが30秒以内で完了
- [x] エラーハンドリング（欠損/形式不正/エンコーディング）を検証済み
- [x] 自動デプロイスクリプトが実行可能
- [x] パフォーマンスベンチマークを実施・記録
- [x] 運用ドキュメント更新

## Verification Commands
```bash
powershell scripts/test_task007_scenariob.ps1 -ProjectRoot . -Configuration Release
dotnet build ymm4-plugin/NLMSlidePlugin.csproj -c Release -p:SkipPluginCopy=true
python -m pytest -q -m "not slow and not integration" --tb=short
```

## Rollback Conditions
- 大規模CSVインポートが60秒超過
- メモリ使用量が1GB超過
- 既存テストが5件以上失敗

## Deliverables
- 本番化済みYMM4プラグイン
- ベンチマーク結果
- 運用/デプロイ手順書
- TASK_013 完了レポート
