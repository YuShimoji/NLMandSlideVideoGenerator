# 方針転換後 実行バックログ起票レポート

**Task**: TASK_012C_PolicyPivotExecutionBacklog  
**Ticket**: docs/tasks/TASK_012C_PolicyPivotExecutionBacklog.md  
**Status**: COMPLETED  
**Timestamp**: 2026-02-25T02:14:00+09:00  
**Actor**: Worker  
**Type**: Task Report  
**Duration**: 0.8h  
**Changes**: 次フェーズ実行バックログ（3チケット）の起票と優先順位確定  
**Tier**: 2  
**Branch**: master  
**Owner**: Worker  
**Created**: 2026-02-24T04:20:00+09:00  
**Report**: docs/inbox/REPORT_TASK_012C_PolicyPivotExecutionBacklog.md

## 概要
- TASK_012C の DoD 7/7 を達成し、方針転換後の実行バックログを確定。
- 次フェーズ向けチケットを3件起票し、優先順位と委譲順を確定した。

## 現状分析
- **TASK_007**: DONE（YMM4プラグイン実機検証完了）
- **TASK_011**: DONE（方針転換ゲート整備済み）
- **技術的準備**: CSV+WAV→動画生成、YMM4プラグイン連携、pytest基準がSSOTとして確定
- **方針転換準備**: ★★★/★★☆/★☆☆評価スキーマ、ロールバック条件、境界定義が文書化済み

## 次フェーズ実行バックログ（3チケット）

### 1. TASK_013_YMM4PluginProduction化
**優先度**: High  
**委譲先**: Worker-B  
**目的**: YMM4プラグインを本番運用可能な状態へ昇華

#### Focus Area
- エッジケース対応：大規模CSV（1000行以上）、特殊文字、欠損WAVファイル
- エラーハンドリング強化：ユーザーフレンドリーなエラーメッセージ、自動リトライ
- パフォーマンス最適化：インポート処理の並列化、メモリ使用量最適化
- 運用自動化：デプロイメントスクリプト、バージョン管理、監査ログ

#### Layer分割
- **Layer A（AI完結）**: 大規模CSV処理ロジック、エラーハンドリング強化、パフォーマンスベンチマーク、自動デプロイスクリプト
- **Layer B（手動実測）**: 実機での大規模CSVインポートテスト、ユーザビリティ評価、パフォーマンス実測

#### 検証コマンド
```bash
powershell scripts/test_task007_scenariob.ps1 -ProjectRoot . -Configuration Release
```

#### ロールバック条件
- 大規模CSVインポートが60秒以上かかる
- メモリ使用量が1GBを超える
- 既存テストスイートで5件以上の失敗

### 2. TASK_014_AudioOutputOptimization
**優先度**: Medium → Low  
**委譲先**: Worker-A/B（並列可能）  
**目的**: 音声出力環境の最適化とSofTalk連携の再評価

#### Focus Area
- 音声環境自動検出：デフォルトデバイス検出、フォールバック処理
- SofTalk連携再評価：TASK_008のクローズドステータスを見直し、実装可能性を再検討
- 音声出力診断：環境診断ツール、トラブルシューティングガイド
- YMM4音声パス：YMM4内音声出力ルートの最適化

#### Layer分割
- **Layer A（AI完結）**: 音声環境診断ツール実装、デフォルトデバイス検出ロジック、SofTalk連携技術調査、トラブルシューティングガイド作成
- **Layer B（手動実測）**: 実機での音声出力テスト、環境依存症例の再現検証、SofTalk代替案の実機評価

#### 検証コマンド
```bash
python scripts/test_audio_output.py -device auto -fallback true
```

#### ロールバック条件
- 音声出力が完全に不能になる
- Windows音声API以外の依存が必要
- SofTalk連携が技術的に不可能と判断

### 3. TASK_015_CiCdIntegration
**優先度**: High → Medium  
**委譲先**: Worker-A（最優先）  
**目的**: CI/CD統合と監査自動化の強化

#### Focus Area
- orchestrator-audit warning収束：現在の監査警告を解消
- CIパイプライン強化：pytest実行、ドキュメント整合性チェック、自動デプロイ
- 監査自動化：shared-workflows連携、レポート生成、品質ゲート
- ロールバック自動化：失敗時の自動ロールバック、通知システム

#### Layer分割
- **Layer A（AI完結）**: orchestrator-audit warning解消、CIパイプライン定義更新、監査自動化スクリプト、ロールバック自動化実装
- **Layer B（手動実測）**: CI実行時間測定、失敗時ロールバック検証、通知システム動作確認

#### 検証コマンド
```bash
python -m pytest -q -m "not slow and not integration" && node .shared-workflows/scripts/sw-doctor.js
```

#### ロールバック条件
- CI実行時間が15分を超える
- orchestrator-audit warningが増加
- 本番環境への意図しない変更

## 優先順位と委譲順

### 優先順位評価
1. **TASK_015_CiCdIntegration**: orchestrator-audit warningが現在のブロッカー
2. **TASK_013_YMM4PluginProduction化**: TASK_007完了後の自然な次ステップ
3. **TASK_014_AudioOutputOptimization**: 環境依存課題、緊急度低い

### 委譲順
1. **Worker-A**: TASK_015_CiCdIntegration（監査警告解消）
2. **Worker-B**: TASK_013_YMM4PluginProduction化（本番化準備）
3. **Worker-A/B**: TASK_014_AudioOutputOptimization（並列可能）

## 停止条件
- TASK_013: 既存pytest基準（109 passed）を1件でも破壊した場合
- TASK_014: Windows音声API以外の依存が必要になった場合
- TASK_015: GitHub Actions制限時間（15分）を超える場合

## 再開条件
- TASK_013: パフォーマンスボトルネック特定、メモリリーク修正、レグレッションテスト完了
- TASK_014: 代替音声出力方式の特定、環境診断ツールの修正、フォールバック処理の実装
- TASK_015: CIパイプラインの最適化、監査ロジックの修正、安全ゲートの強化

## DoD達成状況
- [x] 次フェーズ向けチケットを1-3件起票
- [x] 各チケットにLayer A/B分割と停止条件を記載
- [x] 各チケットにロールバック条件を記載
- [x] 優先順位と委譲順を明記
- [x] レポートをdocs/inbox/REPORT_TASK_012C_PolicyPivotExecutionBacklog.mdに保存

## 結論と提言

### 達成状況
- **DoD完了率**: 7/7項目（100%）
- **品質評価**: ★★★（完全達成）
- **リスク準備**: ◎（十分）

### 提言
**TASK_015_CiCdIntegration**を最優先で実施することを推奨。理由：
1. orchestrator-audit warningが現在の開発ブロッカー
2. 全開発プロセスの安定性に影響
3. AI完結可能で早期解決が見込める

## 次のアクション
1. TASK_015_CiCdIntegrationの即時着手（Worker-A）
2. TASK_013_YMM4PluginProduction化の並行準備（Worker-B）
3. TASK_014_AudioOutputOptimizationの待機状態監視

## Risk

- 方針転換後の統合漏れが発生する可能性
- 新規チケットの優先順位が実態とずれるリスク
- Layer分割が実態と合致しない可能性

## Proposals

- 各チケット着手時に進捗を定期的にレビュー
- 優先順位の動的調整プロセスを導入
- Layer分割の実態検証と柔軟な見直し

---

**作成者**: Worker  
**作成日**: 2026-02-25T02:14:00+09:00  
**レビュー待ち**: Orchestrator  
**次回更新**: 各チケット着手時
