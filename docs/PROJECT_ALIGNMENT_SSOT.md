# PROJECT ALIGNMENT SSOT

Updated: 2026-03-08T18:00:00+09:00
Owner: Orchestrator
Audience: All Agents

## Purpose

この文書は、プロジェクトの方針、最終出力、最終ワークフロー、優先順位を固定するための全Agent向けSSOTです。

参照優先順:
0. `docs/DESIGN_FOUNDATIONS.md` (設計公理: 三層モデル・外部ツール前提・Python責務境界)
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
| `TASK_015` CI/CD強化 | DONE | CIワークフロー11→6整理、.NET Core分離でubuntu CI、deprecated actions修正、全グリーン |
| `TASK_021` コード品質 | DONE | mypy 0 errors (76 files), ruff 0 |
| `TASK_022` 外部TTS統合 | CLOSED (WONTFIX) | YMM4一本化により不要。コード全削除済 |
| `TASK_023` E2E実証 | IN_PROGRESS | SP-024 Voice自動生成UI実装完了。YMM4 GUI手動検証待ち |
| `TASK_024` リファクタリング | DONE | pipeline.py 1384→431行 (-69%) |
| 方針再定義 | DONE | Shorts 撤回、16:9 固定、ゆっくりボイス優先、YMM4一本化 |
| Gemini API統合 | DONE | CsvScriptCompletionPlugin にGemini REST API実装、6テスト追加 |
| .NET Core分離 | DONE | NLMSlidePlugin.Core.csproj (YMM4非依存) + CI ubuntu テスト |
| Path B完全削除 | DONE | 15ファイル削除、7ファイル修正、コード・テスト・API・Web UI全削除 (2026-03-08) |
| Python tests | 1262 passed / 0 failed | カバレッジ84%+ (全体)。43/44仕様done。SP-035 partial(60%) |
| .NET tests | 34 passed / 0 failed | Core分離後 |

## Consistency Audit

| 論点 | 以前のズレ | 修正方針 | 現在SSOT |
|---|---|---|---|
| 最終出力像 | 「一般的なゆっくり解説動画」が曖昧 | 曖昧語を廃止 | `16:9 の汎用スライド動画` |
| Shorts / 縦動画 | 要件にないのに混入 | 非目標化 | 非目標 |
| 音声優先度 | 自然さ重視へズレた | 優先順位を再定義 | `ゆっくりボイスを使えること`（Path A: YMM4内蔵。外部TTS全削除済） |
| キャラクター表示 | 必須か曖昧だった | 任意に固定 | Optional |
| YMM4 の役割 | WAV供給元と誤認されていた | 最終レンダラーに固定 | CSV→音声生成→動画レンダリングの最終工程 |
| Research と Production | 混線しやすかった | 責務分離 | Research は手前工程、Production は別 |
| CI の扱い | 実制作より先行し始めた | 非ブロッカー化 | Windows 実制作を優先 |
| CI ワークフロー肥大化 | 11本に膨張、broken多数 | 必要十分に整理 | 6本に統合 (ci-main, ci-rollback, dotnet-build, orchestrator-audit, release, research-ui-smoke) |
| OpenSpec フレームワーク | spec 0件、import broken | 削除 | 3ワークフロー+2スクリプト削除。SPEC VIEW (spec-index.json) が仕様管理を担う |
| .NET テスト分離 | YMM4 DLL不在でCI不可 | Core プロジェクト分離 | NLMSlidePlugin.Core.csproj (net9.0, ubuntu CI) |
| Path B MoviePy | スタブ化後もコード・参照が残存 | 完全削除+レガシー一掃 | 6ファイル削除、データ型をmodels.pyに抽出、video_composerパラメータ除去、34件のレガシー参照修正 (2026-03-08) |
| Path B 経路自体 | YMM4一本化後もPath Bコード・API・UI残存 | 完全削除 | csv_pipeline_runner, run_csv_pipeline, ExportFallbackManager, CSV Timeline API/UI 全削除。Path A一本化 (2026-03-08) |

## Target Audience & Content Strategy (2026-03-17)

| 項目 | 定義 |
|---|---|
| ターゲット視聴者 | 一般視聴者 (YouTube公開) |
| 主な動画種別 | ニュース/時事解説、解説/教育系、ただし種別は限定しない汎用ツール |
| 想定尺 | 長尺 (20-30分+) |
| 制作ペース | 品質優先。ペースは結果指標として扱う (2026-03-22 見直し) |
| OP/ED | 不要。動画本編のみで十分 |

## Quality Definition (2026-03-17)

品質を「偶然」ではなく「構造」で安定させる。以下の4軸すべてを重視する。

| 品質軸 | 定義 | 測定方法 |
|---|---|---|
| 制作スピード | トピック→MP4の制作時間を継続的に改善すること（品質を犠牲にしない） | パイプライン実行時間 + YMM4操作時間 |
| 情報密度/正確性 | 台本の内容が正確で、視聴者が学べること | NotebookLM台本品質 + ソース品質 |
| 視覚的完成度 | アニメーション・字幕・画像の質が安定していること | style_template.json + Pre-Export検証 (SP-031) |
| 一貫性/再現性 | 毎回同じ品質で出力できること | テンプレート駆動 + バリデーション自動化 |

### 情報密度に関する補足

- 情報の質は NotebookLM に投入するソースの品質に大きく依存する
- 台本品質は NotebookLM の Audio Overview → テキスト化で決まる (DESIGN_FOUNDATIONS.md Section 0)
- Gemini は台本の「構造化」(speaker/text 分離) を行い、品質を「生成」しない

## Final Output Definition

### Must

| 項目 | 定義 |
|---|---|
| 画角 | `16:9` |
| 音声 | `ゆっくりボイス` を使えること |
| 画面構成 | スライド / 資料画像ベースで制作できること |
| 制作入力 | CSV から生成できること（YMM4 が音声+動画を一貫処理） |
| 主要経路 | `CSV -> YMM4 -> 動画` が安定していること |
| 長尺対応 | 20-30分+の動画を安定して生成できること |
| 制作スループット | 効率的な制作が可能であること（品質優先、ペースは結果指標） |

### Recommended

| 項目 | 定義 |
|---|---|
| 背景動画 | 必要時のみ加える |
| 8種アニメーション | ken_burns / zoom_in / zoom_out / pan_left / pan_right / pan_up / pan_down / static (実装済み) |
| ストック画像/AI画像 | 台本連動で自動取得 (実装済み: SP-033) |
| 字幕装飾 | 話者色分け+Border+CenterBottom (実装済み: SP-030) |
| BGMテンプレート | style_template.jsonから自動配置 (実装済み: SP-031) |

### Optional

| 項目 | 定義 |
|---|---|
| キャラクター表示 | 立ち絵、アバター、アイコン |
| YouTube自動アップロード | MetadataGenerator + YouTubeUploader (モック実装あり、本番API未接続) |
| サムネイル自動生成 | src/core/thumbnails/ (パイプライン未統合) |

### Non-Goals

| 項目 | 理由 |
|---|---|
| Shorts / portrait | 長尺解説がメイン。短尺は旨味がない |
| キャラクター表示の義務化 | 方針外 |
| Linux 対応の深掘り | Windows 実制作に非必須 |
| OP/ED テンプレート | 不要と判断 (2026-03-17) |
| 量産 (1時間で数十本) | エンコード制約上不可能。品質優先 |

## Final Workflow

### Path A: YMM4 制作フロー（Primary）— 2026-03-22 更新

> **根本ワークフロー** (DESIGN_FOUNDATIONS.md Section 0 参照)

1. 人間が NotebookLM にソース (URL/テキスト/PDF) を投入する
2. NotebookLM が Audio Overview (音声) を生成する
3. 音声を NotebookLM に再投入し、テキスト化 (文字起こし) する
4. Gemini API がテキストを構造化 (speaker/text 分離) する
5. Python がスライド画像 (Google Slides API) と素材画像を調達する
6. Python が CSV を組み立てる (4列: speaker, text, image_path, animation_type)
7. YMM4 で CSV を NLMSlidePlugin 経由でインポートする
8. YMM4 がゆっくりボイス音声を生成する
9. YMM4 が動画をレンダリングする → 最終 mp4

> YMM4 が最終レンダラーであり、Python パイプラインは CSV 作成までの前工程に責務を限定する。
> 台本品質は NotebookLM が決定する。Gemini は構造化のみ。

### ~~Path B~~ (削除済み, 2026-03-08)

> Path B（手動WAV + Python pipeline）は完全に削除された。csv_pipeline_runner, run_csv_pipeline.py,
> ExportFallbackManager, CSV Timeline API/UI、関連テスト7件を含む15ファイルが削除された。
> YMM4一本化により、Pythonパイプラインの役割はCSV生成までの前工程に限定される。

### ~~Research 先行フロー~~ (廃止, 2026-03-22)

> Python の Brave Search リサーチは廃止。ソース投入は人間が NotebookLM に直接行う。
> (DESIGN_FOUNDATIONS.md Section 0 / DECISION LOG 2026-03-22)

## Current E2E Topic

| 項目 | 内容 |
|---|---|
| Topic | `US and Israel launch strikes on Iran – What has happened so far` |
| Seed URL | `http://www.euronews.com/2026/02/28/us-and-israel-launch-strikes-on-iran-what-has-happened-so-far` |
| Route | `A` (Path B削除済み) |
| Reason | breaking news のため単一ソースで確定しない |
| Package | `data/research/rp_20260301_000417/package.json` |
| Alignment | `data/research/rp_20260301_000417/alignment_report.json` |
| Reviewed report | `data/research/rp_20260301_000417/alignment_report_adopted_all.json` |
| Final CSV | `output_csv/final_script_rp_20260301_000417.csv` |
| Current blocker | 多言語自動照合は弱いが、今回は手動採否相当で final CSV まで到達 |

## Workflow Boundaries (2026-03-22 更新)

| Layer | 主責務 | 出力 |
|---|---|---|
| 入力層 (NotebookLM) | ソース投入 → Audio Overview → テキスト化 | 台本テキスト (プレーンテキスト) |
| 変換層 (Python+Gemini) | 台本構造化 + スライド生成 + 素材調達 + CSV組立 | timeline.csv + 画像群 |
| 出力層 (YMM4) | CSV→音声生成→動画レンダリング | 最終 mp4 |

> 詳細は `docs/DESIGN_FOUNDATIONS.md` Section 0 を参照。

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
- CI方針: 最小限の必要十分。broken workflowの保守コスト > 提供価値の場合は削除する
- 仕様管理: SPEC VIEW (docs/spec-index.json + Markdown) を一元管理手段とする。OpenSpecは廃止済み

## Manual Validation Gate

| 項目 | 手順 | 優先度 | 完了条件 |
|---|---|---|---|
| Streamlit Research UI | Playwright smoke で確認済み | 低 | `tests/test_research_ui_playwright.py` と `scripts/smoke_research_ui_playwright.py` が通る |
| YMM4 実画面の最終確認 | 完了 | 高 | ユーザー確認済み |

## Short / Mid / Long Horizon (2026-03-04 updated)

| 尺度 | 次フェーズ | 主タスク | 目的 |
|---|---|---|---|
| 短期 | TASK_023 E2E完走 | YMM4 GUIでCSVインポート→音声生成→mp4レンダリング | 主要導線の実運用接続 |
| 短期 | CI安定化 | DONE: CIワークフロー整理完了、.NET Core CI統合、全グリーン | CI green維持 |
| 中期 | ワークフロー標準化 | TASK_018: YMM4操作手順確定、エラー回復ドキュメント | 再現可能な制作フロー確立 |
| 中期 | 多言語アライメント | TASK_017: 英語key_claims⇔日本語台本の照合精度改善 | Research→台本の精度向上 |
| 長期 | クラウド対応 | TASK_025: Docker化、クラウドレンダリング | スケーラブルな運用基盤 |
| 長期 | 品質成熟 | テンプレート拡充、自動素材調達、品質ゲート強化 | YouTube出力品質の安定化 |

## Primary References

- `docs/WORKFLOW_STATE_SSOT.md`
- `docs/voice_path_comparison.md`
- `docs/research_workflow_design.md`
- `docs/user_guide_manual_workflow.md`
- `docs/ymm4_export_spec.md`
- `docs/tasks/TASK_013_YMM4PluginProduction.md`
- `docs/tasks/TASK_014_AudioOutputOptimization.md`
- `docs/tasks/TASK_016_SourceResearchAndScriptAlignment.md`
- `docs/ymm4_export_spec.md` セクション10 (Voice自動生成plan)
