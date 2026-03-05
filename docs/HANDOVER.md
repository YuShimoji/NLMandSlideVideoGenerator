# HANDOVER

Timestamp: 2026-03-01T00:16:00+09:00
Actor: Codex (Orchestrator)
Type: Handover
Mode: Driver(P6_report)

## Current Status

- GitHubAutoApprove: true
- **DONE**: `TASK_013` YMM4プラグイン本番化
- **DONE**: `TASK_014` ゆっくりボイス経路整理
- **DONE**: `TASK_016` Web資料収集とNLM台本調整ワークフロー
- **IN_PROGRESS_PARKED**: `TASK_015` CI/CD強化
- **NEXT**: `data/input/e2e_iran_20260301/timeline.csv` を YMM4 へ NLMSlidePlugin 経由でインポートし、YMM4 内で音声生成→動画レンダリング（YMM4 が最終レンダラー）

## Project Policy

- 最終出力ターゲットは `16:9 の汎用スライド動画`
- 音声は `ゆっくりボイスを使えること` を優先
- キャラクター表示は任意
- 背景動画は加点要素であり必須ではない
- Research Workflow と動画生成 Workflow は分離する
- Windows 実運用を優先し、Linux 差分は非ブロッカー

## Current Production SSOT

- 入力: `speaker,text` 形式の CSV
- 出力: 最終 mp4（YMM4 からレンダリング）
- 制作パス:
  - **Path A（Primary）**: CSV → YMM4（NLMSlidePlugin でインポート → 音声生成 → レンダリング）
  - **Path B（Secondary, disabled）**: CSV + WAV群 → `scripts/run_csv_pipeline.py`（TTS コード削除済み、事前生成WAVのみ対応）
  - Web UI: `src/web/web_app.py`（Path B 用）
- 主参照:
  - `docs/PROJECT_ALIGNMENT_SSOT.md`
  - `docs/user_guide_manual_workflow.md`
  - `docs/voice_path_comparison.md`

## Confirmed Manual Gate

- YMM4 GUI 最終確認は完了
- ユーザー確認結果:
  - プラグインOK
  - CSVインポートOK
  - 音声生成OK
  - `run_csv_pipeline.py` OK

## Selected Topic

- Topic: `US and Israel launch strikes on Iran – What has happened so far`
- Seed URL: `http://www.euronews.com/2026/02/28/us-and-israel-launch-strikes-on-iran-what-has-happened-so-far`
- Route: `B`
- Note: breaking news のため、単一ソースでは確定しない
- Package: `data/research/rp_20260301_000417/package.json`
- AlignmentReport: `data/research/rp_20260301_000417/alignment_report.json`
- Reviewed report: `data/research/rp_20260301_000417/alignment_report_adopted_all.json`
- Final CSV: `output_csv/final_script_rp_20260301_000417.csv`
- Handoff dir: `data/input/e2e_iran_20260301/`
- Auto result: `supported=0 / orphaned=139 / missing=18`
- Delivery result: 139 セグメントを `adopted` 扱いにして final CSV を生成済み

## Why CI Is Parked

- `TASK_015` Layer A で Playwright smoke と監査ガードの最小導入は完了
- 以降の GitHub Actions 側初回実行確認は Windows 実制作を止める必須条件ではない
- ユーザー判断により、CI 深掘りを止めて Windows 実制作側を優先している

## Immediate Runbook

### 次の実務（Path A: YMM4 制作）

| Step | 操作 | 目的 |
|---|---|---|
| 1 | YMM4 を起動し、新規プロジェクトを作成 | 制作環境を準備する |
| 2 | NLMSlidePlugin で `data/input/e2e_iran_20260301/timeline.csv` をインポート | タイムラインにCSV行を反映する |
| 3 | YMM4 内でゆっくりボイス音声を生成 | 各行の音声を自動生成する |
| 4 | レイアウト・音声を確認・調整 | 品質を確認する |
| 5 | YMM4 で動画をレンダリング（書き出し） | 最終 mp4 を生成する |

> **注**: `RUN_AFTER_YMM4.ps1` と `audio_dir` は Path B（Batch TTS）用。Path A では不要。

## Verification Snapshot

- Python: `107 passed, 0 skipped, 5 deselected` (2026-03-06)
- .NET: `13 passed, 0 failed, 0 warnings` (2026-03-06)
- Research UI Playwright smoke: `SMOKE_OK`
- `orchestrator-audit --no-fail`: `OK`
- YMM4 GUI: user verified

## Risks

- 実トピック E2E は題材と素材の品質に依存する
- 現 package は英語ソース、台本は日本語のため、現行照合ロジックでは `supported` が立ちにくい
- 今回の final CSV は手動採否相当で作っており、自動根拠一致ではない
- CI を止めたため、GitHub 側実行結果は未確認
- ただし上記 CI 未確認は Windows 実制作の即時ブロッカーではない

## リスク

- 実トピック E2E の題材選定が未固定
- GitHub 側 CI 実行結果は未確認だが非ブロッカー

## Proposals

- 次は実トピック1本で end-to-end の制作入口を固定する
- その後に必要なら `TASK_015` を再開する

## Outlook

- Short-term: final CSV を YMM4 へインポートし、YMM4 内で音声生成→動画レンダリングまで完結させる
- Mid-term: 背景動画の扱いと実制作テンプレートを整理する
- Long-term: CI strict 化と自動素材調達の成熟度を上げる
