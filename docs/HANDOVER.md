# HANDOVER

Timestamp: 2026-03-07T23:00:00+09:00
Actor: Claude Code (Driver)
Type: Session 4 Handover

## Current Status

- **DONE**: `TASK_013` YMM4プラグイン本番化
- **DONE**: `TASK_014` ゆっくりボイス経路整理
- **DONE**: `TASK_016` Web資料収集とNLM台本調整ワークフロー
- **DONE**: `TASK_015` CI/CD強化 (CIワークフロー11→6整理、.NET Core分離、deprecated actions修正、全グリーン)
- **DONE**: `TASK_021` コード品質 (mypy 0 errors, ruff 0)
- **DONE**: `TASK_024` リファクタリング (pipeline.py -69%)
- **CLOSED**: `TASK_022` VOICEVOX統合 (WONTFIX, YMM4一本化により不要)
- **IN_PROGRESS**: `TASK_023` E2E実証 (CSV→mp4パイプライン成功、YMM4エクスポート成功。GUI検証残)
- **NEXT**: YMM4 GUIでCSVインポート→音声生成→mp4レンダリングの手動E2E検証

## Session 4 Summary (2026-03-07)

### Completed Work
1. **Gemini API統合**: `CsvScriptCompletionPlugin` に Gemini REST API 実装、6テスト追加
2. **.NET Core分離**: `NLMSlidePlugin.Core.csproj` (net9.0, YMM4非依存) + CI ubuntu テスト
3. **OpenSpec削除**: 3ワークフロー + 2スクリプト + 3生成ドキュメント削除
4. **CIワークフロー統合**: 11→6 (task-validation, documentation 削除)
5. **deprecated actions修正**: v3→v4/v5/v7 (upload-artifact, cache, setup-python, github-script, action-gh-release)
6. **MoviePy fallback stub化**: video_editor/* → NotImplementedError
7. **SSOT/DECISION LOG更新**: PROJECT_ALIGNMENT_SSOT.md + CLAUDE.md 同期

### Commits (this session)
- `48dc154` refactor(ymm4): separate Core project for CI-testable .NET builds
- `7de98ce` fix(ci): upgrade deprecated GitHub Actions from v3 to v4
- `c5cdc88` chore(ci): remove broken OpenSpec workflows and upgrade deprecated actions
- `9aee841` chore(ci): remove redundant task-validation and documentation workflows
- `6c9e30d` docs: update SSOT with session 4 changes

## Quality Gate

| Area | Result |
|---|---|
| Python tests | 104 passed, 5 deselected |
| .NET tests | 19 passed, 0 failures, 0 warnings |
| CI workflows | 6/6 green |
| Ruff | 0 errors |
| Mypy | 0 errors (76 files) |

## CI Workflows (6, all green)

1. `ci-main.yml` — Python lint + test
2. `ci-rollback.yml` — Auto-revert on CI failure
3. `dotnet-build.yml` — .NET Core test (ubuntu) + plugin build (windows)
4. `orchestrator-audit.yml` — Task report validation
5. `release.yml` — GitHub release
6. `research-ui-smoke.yml` — Streamlit Playwright smoke

## Project Policy

- 最終出力ターゲットは `16:9 の汎用スライド動画`
- 音声は `ゆっくりボイスを使えること` を優先 (Path A: YMM4内蔵。外部TTS全削除済)
- キャラクター表示は任意
- 背景動画は加点要素であり必須ではない
- Research Workflow と動画生成 Workflow は分離する
- Windows 実運用を優先し、Linux 差分は非ブロッカー
- CI方針: 最小限の必要十分。broken workflowの保守コスト > 提供価値の場合は削除
- 仕様管理: SPEC VIEW (docs/spec-index.json + Markdown) を一元管理手段とする

## Production Path

- **Path A (Primary, only)**: CSV → YMM4 (NLMSlidePlugin import → voice gen → render) → final mp4

## YMM4 Plugin TODOs (2 remaining)

- `CsvTimelineVoicePlugin.GenerateVoiceAsync` — needs IVoicePlugin.CreateVoiceAsync
- `CsvTimelineVoicePlugin.GetAvailableSpeakers` — needs IVoicePlugin.Voices

## Immediate Runbook (Path A: YMM4 制作)

| Step | 操作 | 目的 |
|---|---|---|
| 1 | YMM4 を起動し、新規プロジェクトを作成 | 制作環境を準備する |
| 2 | NLMSlidePlugin で CSV をインポート | タイムラインにCSV行を反映する |
| 3 | YMM4 内でゆっくりボイス音声を生成 | 各行の音声を自動生成する |
| 4 | レイアウト・音声を確認・調整 | 品質を確認する |
| 5 | YMM4 で動画をレンダリング（書き出し） | 最終 mp4 を生成する |

## Horizon

| 尺度 | タスク | 状態 |
|---|---|---|
| 短期 | TASK_023 E2E完走 (YMM4 GUI手動検証) | IN_PROGRESS |
| 中期 | ワークフロー標準化 (YMM4操作手順確定) | TODO |
| 中期 | 多言語アライメント精度改善 | TODO |
| 長期 | クラウド対応 (Docker化) | TODO |
| 長期 | 品質成熟 (テンプレート拡充, 自動素材調達) | TODO |

## Primary References

- `docs/PROJECT_ALIGNMENT_SSOT.md`
- `docs/WORKFLOW_STATE_SSOT.md`
- `docs/voice_path_comparison.md`
- `docs/research_workflow_design.md`
- `docs/user_guide_manual_workflow.md`
