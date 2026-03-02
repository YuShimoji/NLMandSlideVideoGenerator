# Task: Web資料収集とNLM台本調整ワークフロー設計
Status: DONE
Tier: 2
Branch: master
Owner: Worker-A
Created: 2026-02-28T16:05:00+09:00
Report: docs/inbox/REPORT_TASK_016_SourceResearchAndScriptAlignment.md

## Objective
- Web から適切な資料を自動収集し、動画制作に使える素材パッケージを構成するワークフローを設計する
- NLM のたたき台ラジオスクリプトと収集資料の差分を比較し、修正候補と採否を管理できるようにする
- 動画生成パイプラインとは分離し、資料整備と根拠管理に責務を限定する

## Context
- 現行の主フローは `CSV + WAV -> 汎用スライド動画` であり、資料収集と台本調整は手前工程として分離したい
- `docs/system_architecture.md` / `docs/system_specification.md` には入力オーケストレーションや Script Provider の抽象が既にある
- NotebookLM / Gemini 由来の叩き台は使えるが、Web 資料の引用根拠や差分調整の運用が未整備

## Focus Area
- 資料収集の入力条件定義: トピック、参考 URL、除外条件、優先ソース種別
- 収集結果の保存形式定義: URL、タイトル、要約、根拠抜粋、利用メモ、採否
- NLM たたき台台本との差分比較方式: 主張、事実、補足、削除候補
- 人手レビューを含む最終確定フロー: どこまで自動、どこから手動か

## Layer分割
- **Layer A（AI完結）**: ワークフロー設計、入出力スキーマ、プロンプトチェーン、差分整理ルール、保存形式定義、差分分析実装、Phase 3 UI実装
- **Layer B（実測/自動化）**: 実トピックでの資料評価、採否判断、台本レビュー、引用妥当性確認、Phase 3 UI確認（Playwright優先。スモーク自動確認済み、手動は最小限）

## Forbidden Area
- いきなり本番用の大規模クローラ実装に踏み込むこと
- 動画レンダリングや YMM4 実装と責務を混ぜること
- 出典不明の要約だけで台本を確定させること

## Constraints
- 出典 URL と採用理由を必ず残せる設計にすること
- NotebookLM / Gemini のどちらを使っても差分調整に入れる抽象にすること
- 既存の CSV + WAV 主フローをブロックしないこと

## DoD
- [x] 資料収集ワークフローのステップ定義がある
- [x] 収集結果の保存スキーマがある
- [x] NLM たたき台との比較/修正フローが定義されている
- [x] 手動レビュー点が明示されている
- [x] 次実装フェーズに切れる単位へ分解されている
- [x] docs/inbox/REPORT_TASK_016_SourceResearchAndScriptAlignment.md に証跡を保存

## 検証コマンド
```bash
python -m pytest -q -m "not slow and not integration" --tb=short
```

## ロールバック条件
- 資料収集と動画生成の責務境界が曖昧なままになる
- 出典管理ができない設計になる
- 手動レビュー前提を外して誤情報混入リスクが高まる

## Deliverables
- ワークフロー設計メモ
- 入出力スキーマ案
- 差分比較ルール
- 次フェーズの実装タスク分解
- Phase 1 基盤実装（データモデル、検索API、CLI、永続化）
- Phase 2 実装（claims抽出、差分分析、AlignmentReport生成、CLI保存）
- Phase 3 Layer A 実装（レビューUI、採否反映、最終CSV出力）
- Phase 3 Layer B 自動確認（Playwright smoke, fixture, smoke script）
