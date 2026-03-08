# NLMandSlideVideoGenerator

CSV から動画・字幕・サムネイルを生成するパイプライン。Python / YMM4 連携。

## PROJECT CONTEXT
プロジェクト名: NLMandSlideVideoGenerator
環境: Python 3.11 (venv) / .NET 9 (YMM4 plugin) / Windows 11
ブランチ戦略: trunk-based (master)
現フェーズ: プロトタイプ後期
直近の状態: Voice自動生成plan承認済 (.claude/plans/unified-imagining-feather.md)。VoiceSpeakerDiscovery実装がE2Eブロッカー。Plugin deployed。Python 67/1, .NET 34/0 全通過。CI全グリーン（6 workflows）。仕様ドキュメント更新完了（ymm4_export_spec.md, spec-index.json, PROJECT_ALIGNMENT_SSOT.md）。

## DECISION LOG
| 日付 | 決定事項 | 選択肢 | 決定理由 |
|------|----------|--------|----------|
| 2026-03-01 | 16:9スライド動画+ゆっくりボイス優先 | 16:9/縦型/Shorts | プロジェクト本来の目的に合致 |
| 2026-03-01 | キャラ表示: オプション、背景動画: nice-to-have | 必須/オプション/不要 | MVPスコープ縮小 |
| 2026-03-04 | YMM4一本化 (Path A primary) | YMM4のみ/MoviePy併用/両方維持 | YMM4がfinal renderer、Python は前処理専任 |
| 2026-03-07 | TTS統合コードNo-opスタブ化 | 完全削除/スタブ化/維持 | importパス維持で後方互換性確保 |
| 2026-03-07 | Path B (MoviePy) No-opスタブ化 | 維持/スタブ化/完全削除 | YMM4一本化方針+即時破壊回避 |
| 2026-03-07 | desktop/node_modules git除外 | 全削除/node_modulesのみ除外/維持 | ソース保持+リポジトリ軽量化 |
| 2026-03-07 | Gemini API統合 (CsvScriptCompletionPlugin) | Gemini/OpenAI/ローカルLLM | YMM4非依存、無料枠あり、軽量実装 |
| 2026-03-07 | .NET Core分離 (NLMSlidePlugin.Core.csproj) | 分離/単一プロジェクト維持 | CIでYMM4非依存テスト実行可能化 |
| 2026-03-07 | OpenSpec系ワークフロー削除 | 修正/削除/無効化 | spec 0件ロード、import broken、ci-mainと機能重複 |
| 2026-03-07 | CIワークフロー11→6整理 | 統合/個別維持 | 重複排除 (task-validation, documentation, openspec×3 削除) |
| 2026-03-07 | CI方針: 最小限の必要十分 | 多機能CI/最小CI | broken workflowの保守コスト > 提供価値 |
| 2026-03-08 | Path B完全削除 (Path A一本化) | 維持/deprecate/完全削除/現状維持 | YMM4一本化方針に合致。YMM4自体がVoicevox連携可能でPath Bの存在意義なし |
| 2026-03-09 | Voice自動生成UI優先実装 | E2E手動検証先行/Voice UI先行 | YMM4 SDK依存の解決が最終ワークフロー確立に必須 |

## Key Paths

- Source: `src/`
- Tests: `tests/`
- Config: `config/`

## Rules

- Respond in Japanese
- No emoji
- Do NOT read `docs/reports/`, `docs/inbox/` unless explicitly asked
- Use Serena's symbolic tools (find_symbol, get_symbols_overview) instead of reading entire .py files
- When exploring code, start with get_symbols_overview, then read only the specific symbols needed
- Keep responses concise — avoid repeating file contents back to the user
