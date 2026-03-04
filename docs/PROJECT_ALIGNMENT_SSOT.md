# PROJECT ALIGNMENT SSOT

Updated: 2026-03-04T01:00:00+09:00
Owner: Orchestrator
Audience: All Agents

## Purpose

この文書は、プロジェクトの方針、最終出力、最終ワークフロー、優先順位を固定するための全Agent向けSSOTです。

参照優先順:
1. この文書
2. `docs/WORKFLOW_STATE_SSOT.md`
3. `AI_CONTEXT.md`
4. `docs/HANDOVER.md`
5. 各 task / report

## Verified Current Position

| 項目 | 状態 | 根拠 |
|---|---|---|
| `TASK_013` YMM4プラグイン本番化 | DONE | 13 tests pass, deploy script, ops docs |
| `TASK_014` ゆっくりボイス経路 | DONE | Layer B + YMM4 GUI 最終確認まで完了 |
| `TASK_016` Research Workflow | DONE | Phase 3 UI + Playwright smoke + CSV export |
| `TASK_015` CI/CD強化 | IN_PROGRESS | Layer A 完了。.NETテストジョブ追加済。release.yml検証残 |
| `TASK_021` コード品質 | DONE | mypy 0 errors on Core 3 files |
| `TASK_022` VOICEVOX統合 | CLOSED (WONTFIX) | YMM4一本化により不要。コード全削除済 |
| `TASK_023` E2E実証 | IN_PROGRESS | CSV→mp4パイプライン成功、YMM4エクスポート成功。GUI検証残 |
| `TASK_024` リファクタリング | DONE | pipeline.py 1384→431行 (-69%) |
| 方針再定義 | DONE | Shorts 撤回、16:9 固定、ゆっくりボイス優先、YMM4一本化 |
| Python tests | 105 passed / 10 skipped | 既存スイート安定 (VOICEVOX系テスト削除後) |
| .NET tests | 13 passed / 0 failed | benchmark 含む |

## Consistency Audit

| 論点 | 以前のズレ | 修正方針 | 現在SSOT |
|---|---|---|---|
| 最終出力像 | 「一般的なゆっくり解説動画」が曖昧 | 曖昧語を廃止 | `16:9 の汎用スライド動画` |
| Shorts / 縦動画 | 要件にないのに混入 | 非目標化 | 非目標 |
| 音声優先度 | 自然さ重視へズレた | 優先順位を再定義 | `ゆっくりボイスを使えること`（Path A: YMM4内蔵, Path B: VOICEVOX推奨） |
| キャラクター表示 | 必須か曖昧だった | 任意に固定 | Optional |
| YMM4 の役割 | WAV供給元と誤認されていた | 最終レンダラーに固定 | CSV→音声生成→動画レンダリングの最終工程 |
| Research と Production | 混線しやすかった | 責務分離 | Research は手前工程、Production は別 |
| CI の扱い | 実制作より先行し始めた | 非ブロッカー化 | Windows 実制作を優先 |

## Final Output Definition

### Must

| 項目 | 定義 |
|---|---|
| 画角 | `16:9` |
| 音声 | `ゆっくりボイス` を使えること |
| 画面構成 | スライド / 資料画像ベースで制作できること |
| 制作入力 | CSV から生成できること（YMM4 が音声+動画を一貫処理） |
| 主要経路 | `CSV -> YMM4 -> 動画` が安定していること |

### Recommended

| 項目 | 定義 |
|---|---|
| 背景動画 | 必要時のみ加える |
| 軽い演出 | zoom / pan / 字幕調整など最低限 |
| Batch TTS パイプライン | VOICEVOX → WAVs → run_csv_pipeline.py で自動生成（YMM4不使用時の推奨） |

### Optional

| 項目 | 定義 |
|---|---|
| キャラクター表示 | 立ち絵、アバター、アイコン |
| SofTalk / AquesTalk | レガシー代替経路（VOICEVOX が使えない場合） |

### Non-Goals

| 項目 | 理由 |
|---|---|
| Shorts / portrait | 現行ターゲット外 |
| キャラクター表示の義務化 | 方針外 |
| Linux 対応の深掘り | Windows 実制作に非必須 |

## Final Workflow

### Path A: YMM4 制作フロー（Primary）

1. 台本または構成案を作る
2. CSV を作成する（手動 or Research workflow 経由）
3. YMM4 で CSV を NLMSlidePlugin 経由でインポートする
4. YMM4 がゆっくりボイス音声を生成する
5. YMM4 が動画をレンダリングする → 最終 mp4

> YMM4 が最終レンダラーであり、Python パイプラインは CSV 作成までの前工程に責務を限定する。
> YMM4 は個別 WAV エクスポートができないため、WAV 供給元としては使用しない。

### Path B: Batch TTS 自動パイプライン（Secondary）

1. CSV を作成する（手動 or Research workflow 経由）
2. VOICEVOX で WAV を生成する（`--tts voicevox` オプション、001.wav, 002.wav, ...）
3. `scripts/run_csv_pipeline.py` で mp4 を生成する

> YMM4 を使わない自動化経路。VOICEVOX Engine の起動が前提。
> フォールバック: SofTalk / AquesTalk（レガシー）も利用可能だが、環境構築コストが高い。

### Research 先行フロー（Path A/B 共通の前工程）

1. Web から資料収集する
2. Research Package を保存する
3. NLM たたき台台本と資料を照合する
4. 採否判断を反映して CSV を出力する
5. Path A または Path B へ接続する

## Current E2E Topic

| 項目 | 内容 |
|---|---|
| Topic | `US and Israel launch strikes on Iran – What has happened so far` |
| Seed URL | `http://www.euronews.com/2026/02/28/us-and-israel-launch-strikes-on-iran-what-has-happened-so-far` |
| Route | `B` |
| Reason | breaking news のため単一ソースで確定しない |
| Package | `data/research/rp_20260301_000417/package.json` |
| Alignment | `data/research/rp_20260301_000417/alignment_report.json` |
| Reviewed report | `data/research/rp_20260301_000417/alignment_report_adopted_all.json` |
| Final CSV | `output_csv/final_script_rp_20260301_000417.csv` |
| Current blocker | 多言語自動照合は弱いが、今回は手動採否相当で final CSV まで到達 |

## Workflow Boundaries

| Layer | 主責務 | 出力 |
|---|---|---|
| Research | 出典確認、要約、資料パッケージ化 | Research Package |
| Alignment | 台本との差分比較、採否判断 | Alignment Report / final CSV |
| Production (Path A) | YMM4 で CSV→音声→動画をレンダリング | 最終 mp4 |
| Production (Path B) | VOICEVOX→WAVs→Python pipeline（レガシー: SofTalk/AquesTalk） | mp4 / 字幕 / ログ |

## Agent Operating Policy

| Role | 役割 |
|---|---|
| Orchestrator | 方針固定、SSOT更新、優先順位整理 |
| Driver | 実行、検証、文書同期 |
| Worker | 個別タスクの実装と証跡化 |

補足:
- ブラウザUI確認は Playwright を優先する
- 手動確認は YMM4 GUI など外部依存箇所に限定する
- Windows を primary OS とする
- CI は有用だが、Windows 実制作より優先しない

## Manual Validation Gate

| 項目 | 手順 | 優先度 | 完了条件 |
|---|---|---|---|
| Streamlit Research UI | Playwright smoke で確認済み | 低 | `tests/test_research_ui_playwright.py` と `scripts/smoke_research_ui_playwright.py` が通る |
| YMM4 実画面の最終確認 | 完了 | 高 | ユーザー確認済み |

## Short / Mid / Long Horizon (2026-03-04 updated)

| 尺度 | 次フェーズ | 主タスク | 目的 |
|---|---|---|---|
| 短期 | TASK_023 E2E完走 | YMM4 GUIでCSVインポート→音声生成→mp4レンダリング | 主要導線の実運用接続 |
| 短期 | CI安定化 | TASK_015: release.yml検証、.NETテストCI統合確認 | CI green維持 |
| 中期 | ワークフロー標準化 | TASK_018: YMM4操作手順確定、エラー回復ドキュメント | 再現可能な制作フロー確立 |
| 中期 | 多言語アライメント | TASK_017: 英語key_claims⇔日本語台本の照合精度改善 | Research→台本の精度向上 |
| 長期 | クラウド対応 | TASK_025: Docker化、クラウドレンダリング | スケーラブルな運用基盤 |
| 長期 | 品質成熟 | テンプレート拡充、自動素材調達、品質ゲート強化 | YouTube出力品質の安定化 |

## Primary References

- `docs/WORKFLOW_STATE_SSOT.md`
- `docs/voice_path_comparison.md`
- `docs/research_workflow_design.md`
- `docs/user_guide_manual_workflow.md`
- `docs/tasks/TASK_013_YMM4PluginProduction.md`
- `docs/tasks/TASK_014_AudioOutputOptimization.md`
- `docs/tasks/TASK_016_SourceResearchAndScriptAlignment.md`
