# Cursor Rules（shared-workflows / v2.x運用）

目的: Cursor が `.cursorrules` を拾わない/弱い環境でも、ルールが適用される確率を上げる。

## 基本ルール

- 返信は日本語。
- 絵文字、装飾表現、冗長な言い回しを使わない。
- チャットで完結させない。成果（差分）はファイル変更として残す。
- マルチステップ作業は中間報告を必ず出す（完了/残り/次の選択肢）。

## 参照先

- 入口: `.shared-workflows/docs/windsurf_workflow/OPEN_HERE.md`（無ければ `docs/windsurf_workflow/OPEN_HERE.md`）
- Orchestrator Driver: `.shared-workflows/prompts/every_time/ORCHESTRATOR_DRIVER.txt`（無ければ `prompts/every_time/ORCHESTRATOR_DRIVER.txt`）

## 中間報告ルール（長大作業の安定化）

- ツール呼び出し10回ごと、またはファイル編集5回ごとに中間報告を出す。
- 中間報告には「次のメッセージの選択肢（1-3件）」を必ず含める。


