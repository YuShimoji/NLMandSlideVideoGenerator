# **DEPRECATED - Future task, not current TASK_024**

The current TASK_024 is `TASK_024_PipelineRefactoring.md` (DONE).
This file describes a future YMM4 template expansion task and remains for planning reference only.

---

# Task: YMM4テンプレートの表現力拡張と最適化

Status: INBOX
Tier: 3
Branch: master
Owner: Worker
Created: 2026-03-03

## Objective

- YMM4上の汎用スライド動画テンプレートに対し、背景動画の対応や演出の微調整といった「表現力」の拡張と最適化を行う。

## Context

- 一気通貫のパイプラインは開通したが、出力される動画のクオリティや表現の幅（背景など）を少しリッチにする余地がある。
- スピード重視（B分類）の改善として、テンプレート設定ファイルを使い回しやすく整理する。

## Focus Area

- **1. YMM4テンプレート構成の研究**: 既存の `.ymmp` テンプレートまたはプラグイン生成時の設定における、背景動画レイヤーや基本演出の追加検討。
- **2. 設定ファイル化**: 背景等のパラメータをPython層のCSV出力時や、YMM4プラグイン側で読み込めるような仕組みの最適化。
- **3. パフォーマンスと互換性**: 表現を増やしつつも生成時間が極端に延びないようにする。

## Layer分割

- **Layer A（AI完結）**: テンプレート生成ロジックの調整、設定ファイルの読み込み処理追加、プラグイン側のプロパティ追加（必要な場合）。
- **Layer B（実測/手動）**: YMM4 GUIにてデザインの崩れがないかの確認、背景動画の動作テスト。

## Constraints & Forbidden

- 過度な演出（過激なアニメーションや複雑なエフェクト）の追加は避ける。シンプルな「16:9 汎用スライド」の範疇に収める。
- プラグインの根幹を壊すような大規模リファクタリングは禁止。

## DoD

- [ ] 背景動画や追加のレイヤーをオプションで設定できる仕組みが実装されている。
- [ ] 実機にてエラーなく読み込まれ、正常に動画がレンダリングされることを確認している。
- [ ] `docs/inbox/REPORT_TASK_024_YMM4TemplateExpansion.md` に結果を記録している。
