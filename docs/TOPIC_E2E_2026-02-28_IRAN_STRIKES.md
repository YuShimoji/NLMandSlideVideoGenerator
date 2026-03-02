# E2E Topic Brief

Updated: 2026-03-01T00:16:00+09:00
Owner: Orchestrator

## Selected Topic

- Topic: `US and Israel launch strikes on Iran – What has happened so far`
- Seed URL: `http://www.euronews.com/2026/02/28/us-and-israel-launch-strikes-on-iran-what-has-happened-so-far`
- Source check: Euronews article exists and was published on `2026-02-28`

## Execution Route

- Route: `B`
- Reason:
  - 時事ニュースで変動が大きい
  - 単一ソースのまま CSV 化すると誤情報混入リスクが高い
  - `TASK_016` の Research / Alignment workflow を使う題材として適している

## Working Rule

- 単一記事だけでは台本を確定しない
- Seed URL は入口として使うが、追加ソースで照合する
- 出典 URL、取得日時、採用理由を必ず残す
- 速報段階なので断定表現は避ける

## Current Goal

1. この topic で Research Package を作る
2. NLM たたき台台本との差分を取る
3. final CSV を生成する
4. YMM4 で CSV をインポートし、音声生成→動画レンダリング（YMM4 が最終レンダラー）

## Current Output

- Package: `data/research/rp_20260301_000417/package.json`
- AlignmentReport: `data/research/rp_20260301_000417/alignment_report.json`
- Reviewed report: `data/research/rp_20260301_000417/alignment_report_adopted_all.json`
- final CSV: `output_csv/final_script_rp_20260301_000417.csv`
- Handoff dir: `data/input/e2e_iran_20260301/`
- Sources: 3
- Notes:
  - Euronews は直接スクレイプで本文 preview を取れなかったため slug fallback を使用
  - AP / The Guardian は title と preview を取得済み
  - `key_claims` 抽出を実装し、新 package では各 source に claim を保存済み
  - 実台本 `docs/Resources/米イスラエルのイラン空爆とインターネット完全遮断.txt` で Alignment 実行済み
  - 自動照合結果は `supported=0 / orphaned=139 / missing=18`
  - 今回は手動採否相当として全文を `adopted` 扱いにして final CSV まで生成

## Next Concrete Step

### Path A（推奨: YMM4 制作）
1. YMM4 を起動し、NLMSlidePlugin で `data/input/e2e_iran_20260301/timeline.csv` をインポート
2. YMM4 内でゆっくりボイス音声を生成
3. YMM4 で動画をレンダリング → 最終 mp4

### Path B（代替: Batch TTS + Python pipeline）
1. SofTalk/AquesTalk で `audio_dir/001.wav`, `002.wav`, ... を生成
2. `RUN_BATCH_PIPELINE.ps1` を実行
