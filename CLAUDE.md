# NLMandSlideVideoGenerator

CSV 縺九ｉ蜍慕判繝ｻ蟄怜ｹ輔・繧ｵ繝繝阪う繝ｫ繧堤函謌舌☆繧九ヱ繧､繝励Λ繧､繝ｳ縲１ython / YMM4 騾｣謳ｺ縲・

## PROJECT CONTEXT
繝励Ο繧ｸ繧ｧ繧ｯ繝亥錐: NLMandSlideVideoGenerator
迺ｰ蠅・ Python 3.11 (venv) / .NET 9 (YMM4 plugin) / Windows 11
繝悶Λ繝ｳ繝∵姶逡･: trunk-based (master)
迴ｾ繝輔ぉ繝ｼ繧ｺ: 繝励Ο繝医ち繧､繝怜ｾ梧悄
直近の状態: SP-032 Phase C完了。CLI pipelineサブコマンドで collect→script gen→align→review→CsvAssembler一気通貫実行可能。Python 171/0。研究ワークフロー Phase 1-5全完了(SP-014 100%)。次: Phase D (Streamlit UI統合) or Gemini SDK移行 or YMM4実機テスト。

## DECISION LOG
| 譌･莉・| 豎ｺ螳壻ｺ矩・| 驕ｸ謚櫁い | 豎ｺ螳夂炊逕ｱ |
|------|----------|--------|----------|
| 2026-03-01 | 16:9繧ｹ繝ｩ繧､繝牙虚逕ｻ+繧・▲縺上ｊ繝懊う繧ｹ蜆ｪ蜈・| 16:9/邵ｦ蝙・Shorts | 繝励Ο繧ｸ繧ｧ繧ｯ繝域悽譚･縺ｮ逶ｮ逧・↓蜷郁・ |
| 2026-03-01 | 繧ｭ繝｣繝ｩ陦ｨ遉ｺ: 繧ｪ繝励す繝ｧ繝ｳ縲∬レ譎ｯ蜍慕判: nice-to-have | 蠢・・繧ｪ繝励す繝ｧ繝ｳ/荳崎ｦ・| MVP繧ｹ繧ｳ繝ｼ繝礼ｸｮ蟆・|
| 2026-03-04 | YMM4荳譛ｬ蛹・(Path A primary) | YMM4縺ｮ縺ｿ/MoviePy菴ｵ逕ｨ/荳｡譁ｹ邯ｭ謖・| YMM4縺掲inal renderer縲￣ython 縺ｯ蜑榊・逅・ｰゆｻｻ |
| 2026-03-07 | TTS統合コードno-opスタブ化 | 完全削除/スタブ化/継続 | importパス継続で後方互換性確保 |
| 2026-03-07 | Path B (MoviePy) No-opスタブ化 | 継続/スタブ化/完全削除 | YMM4一本化方針、即時完全回避 |
| 2026-03-07 | desktop/node_modules git除外 | 全削除/node_modulesのみ除外/継続 | ソース保持+リポジトリ軽量化 |
| 2026-03-07 | Gemini API統合 (CsvScriptCompletionPlugin) | Gemini/OpenAI/ローカルLLM | YMM4非依存、無料枠あり、補完実装 |
| 2026-03-07 | .NET Core分離 (NLMSlidePlugin.Core.csproj) | 分離/単一プロジェクト継続 | CIでYMM4非依存テスト実行可能化 |
| 2026-03-07 | OpenSpec関連ワークフロー削除 | 修正/削除/無効化 | spec 0件ロード+import broken、ci-mainと機能重複 |
| 2026-03-07 | CIワークフロー整理 | 統合/個別継続 | 重複排除 |
| 2026-03-07 | CI方針: 最小限の必要十分切替 | 大規模CI/最小CI | broken workflowの保守コスト > 検証価値 |
| 2026-03-08 | Path B完全削除 (Path A一本化) | 継続/deprecate/完全削除/現状継続 | YMM4一本化方針に合致。外部TTS連携不要でPath Bの存在意義なし |
| 2026-03-09 | Voice自動生成UI優先実装 | E2E手動検証先行/Voice UI先行 | YMM4 SDK依存の解決が最終ワークフロー確立に必須 |
| 2026-03-09 | SimpleLogger encoding-safe化 | logger修正/CI env設定のみ/代替 | Windows CI (cp1252)での日本語ログ出力時UnicodeEncodeError解決 |

| 2026-03-10 | Path A/B音声責務の明確化 | 旧仕様は外部音源準備、現行はYMM4で音声合成+最終レンダリング | docs/ymm4_integration_arch.md と docs/workflow_boundary.md を更新し運用境界を固定 |
| 2026-03-10 | docs旧コマンド参照のCIガード導入 | 再発防止/仕様逸脱の早期検知 | scripts/check_doc_command_references.py を追加し ci-main.yml に組み込み |
| 2026-03-11 | WAV-to-YMM4インポート経路はレガシー破棄 | WAVコピー維持/除去 | YMM4が唯一の音声合成環境。Python側WAV準備は不要、_copy_audio_assets除去 |
| 2026-03-11 | SP-024 Voice自動生成UIをCsvImportDialogに統合 | 別ダイアログ/既存ダイアログ拡張 | 既存CsvImportDialogにチェックボックス追加が最小変更。VoiceSpeakerDiscovery 3層フォールバックで堅牢性確保 |
| 2026-03-14 | SP-026 ImageItem自動配置: CSV 3列目方式 | CSV 3列目/slides_payload.json活用 | CSV拡張が最小変更で後方互換。slides_payload.jsonは将来統合可能 |

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
- Keep responses concise 窶・avoid repeating file contents back to the user