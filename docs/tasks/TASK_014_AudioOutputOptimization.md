# Task: ゆっくりボイス利用経路最適化
Status: DONE
Tier: 2
Branch: master
Owner: Worker-A/B
Created: 2026-02-25T02:20:00+09:00
Report: docs/inbox/REPORT_TASK_014_AudioOutputOptimization.md

> Policy Note (2026-03-08): 現行 SSOT は Path A 単一構造です。Path A は `CSV -> YMM4 -> 音声生成 -> 動画レンダリング` です。Path B（MoviePy backend + TTS統合）は 2026-03-08 に完全削除されました。

## Objective
- ゆっくりボイスを利用できる経路を最優先で安定化する
- 音声の「自然さ」より、YMM4 / SofTalk / AquesTalk 等で `001.wav` を確実に用意できることを優先する
- 汎用スライド動画の標準出力（16:9）に対し、音声素材準備の再現性を高める

## Context
- TASK_008: SofTalk/AquesTalk 連携は実装済みだが、環境依存が大きく安定度が不足
- `docs/ymm4_integration_arch.md` では YMM4 をゆっくり系音声のハブとする方針が整理済み
- 現在の最終出力ターゲットは「16:9 の汎用スライド動画」であり、キャラクター表示は必須ではない
- 背景動画は加点要素であり、本タスクの必須DoDには含めない

## Focus Area
- YMM4 / SofTalk / AquesTalk のどの経路で `audio_dir` を最も安定供給できるかを比較し、優先順を決める
- `001.wav`, `002.wav`, ... の素材準備経路を再現可能にする
- 音声生成から CSV パイプライン投入までの確認手順を明確化する
- 失敗時のフォールバック手順とログの見方を整備する

## Layer分割
- **Layer A（AI完結）**: 音声経路比較、推奨経路の選定、ログ/フォールバック手順整理、ドキュメント更新
- **Layer B（手動実測）**: YMM4 / SofTalk / AquesTalk の実機確認、`audio_dir` 生成成功率確認

## Forbidden Area
- 音声の自然さ改善を主目的にした大規模TTS比較
- OSレベルのオーディオドライバ解析
- キャラクター立ち絵や縦動画対応を前提にしたUI改修

## Constraints
- Windows 環境で再現可能であること
- 既存の WAV 入力仕様（`001.wav` 形式）を維持すること
- 既存 CSV + WAV パイプラインの挙動を壊さないこと

## DoD
- [x] ゆっくりボイス利用経路の優先順位が確定
- [x] 推奨経路で `audio_dir` を再現可能に作成できる
- [x] 代替経路のフォールバック手順が整理されている
- [x] `docs/user_guide_manual_workflow.md` または関連ガイドに反映されている
- [x] 実機で少なくとも1経路の成功証跡がある
- [x] docs/inbox/REPORT_TASK_014_AudioOutputOptimization.md に証跡を保存

## 検証コマンド
```bash
python scripts/test_audio_output.py -device auto -fallback true
```

## ロールバック条件
- 推奨経路でも `001.wav` 形式の出力が安定しない
- 実機依存が大きすぎて再現手順を定義できない
- 既存 CSV + WAV パイプラインの前提を壊す必要がある

## Deliverables
- 音声経路比較メモ
- 推奨経路の手順書
- フォールバック手順
- 実機確認レポート
- ユーザーによる YMM4 実画面の最終確認メモ
