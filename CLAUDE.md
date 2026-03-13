# NLMandSlideVideoGenerator

CSV 縺九ｉ蜍慕判繝ｻ蟄怜ｹ輔・繧ｵ繝繝阪う繝ｫ繧堤函謌舌☆繧九ヱ繧､繝励Λ繧､繝ｳ縲１ython / YMM4 騾｣謳ｺ縲・

## PROJECT CONTEXT
繝励Ο繧ｸ繧ｧ繧ｯ繝亥錐: NLMandSlideVideoGenerator
迺ｰ蠅・ Python 3.11 (venv) / .NET 9 (YMM4 plugin) / Windows 11
繝悶Λ繝ｳ繝∵姶逡･: trunk-based (master)
迴ｾ繝輔ぉ繝ｼ繧ｺ: 繝励Ο繝医ち繧､繝怜ｾ梧悄
直近の状態: SP-024 Voice自動生成UI実装完了、spec-index更新済(done/100%)。Python 69/1, .NET 34/0。DOTNET_ROOT修正済(C:\Program Files\dotnet)、ローカル.NETテスト正常化。次: YMM4実機テスト(Voice自動生成E2E = TASK_023完走)。

## DECISION LOG
| 譌･莉・| 豎ｺ螳壻ｺ矩・| 驕ｸ謚櫁い | 豎ｺ螳夂炊逕ｱ |
|------|----------|--------|----------|
| 2026-03-01 | 16:9繧ｹ繝ｩ繧､繝牙虚逕ｻ+繧・▲縺上ｊ繝懊う繧ｹ蜆ｪ蜈・| 16:9/邵ｦ蝙・Shorts | 繝励Ο繧ｸ繧ｧ繧ｯ繝域悽譚･縺ｮ逶ｮ逧・↓蜷郁・ |
| 2026-03-01 | 繧ｭ繝｣繝ｩ陦ｨ遉ｺ: 繧ｪ繝励す繝ｧ繝ｳ縲∬レ譎ｯ蜍慕判: nice-to-have | 蠢・・繧ｪ繝励す繝ｧ繝ｳ/荳崎ｦ・| MVP繧ｹ繧ｳ繝ｼ繝礼ｸｮ蟆・|
| 2026-03-04 | YMM4荳譛ｬ蛹・(Path A primary) | YMM4縺ｮ縺ｿ/MoviePy菴ｵ逕ｨ/荳｡譁ｹ邯ｭ謖・| YMM4縺掲inal renderer縲￣ython 縺ｯ蜑榊・逅・ｰゆｻｻ |
| 2026-03-07 | TTS邨ｱ蜷医さ繝ｼ繝丑o-op繧ｹ繧ｿ繝門喧 | 螳悟・蜑企勁/繧ｹ繧ｿ繝門喧/邯ｭ謖・| import繝代せ邯ｭ謖√〒蠕梧婿莠呈鋤諤ｧ遒ｺ菫・|
| 2026-03-07 | Path B (MoviePy) No-op繧ｹ繧ｿ繝門喧 | 邯ｭ謖・繧ｹ繧ｿ繝門喧/螳悟・蜑企勁 | YMM4荳譛ｬ蛹匁婿驥・蜊ｳ譎らｴ螢雁屓驕ｿ |
| 2026-03-07 | desktop/node_modules git髯､螟・| 蜈ｨ蜑企勁/node_modules縺ｮ縺ｿ髯､螟・邯ｭ謖・| 繧ｽ繝ｼ繧ｹ菫晄戟+繝ｪ繝昴ず繝医Μ霆ｽ驥丞喧 |
| 2026-03-07 | Gemini API邨ｱ蜷・(CsvScriptCompletionPlugin) | Gemini/OpenAI/繝ｭ繝ｼ繧ｫ繝ｫLLM | YMM4髱樔ｾ晏ｭ倥∫┌譁呎棧縺ゅｊ縲∬ｻｽ驥丞ｮ溯｣・|
| 2026-03-07 | .NET Core蛻・屬 (NLMSlidePlugin.Core.csproj) | 蛻・屬/蜊倅ｸ繝励Ο繧ｸ繧ｧ繧ｯ繝育ｶｭ謖・| CI縺ｧYMM4髱樔ｾ晏ｭ倥ユ繧ｹ繝亥ｮ溯｡悟庄閭ｽ蛹・|
| 2026-03-07 | OpenSpec邉ｻ繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ蜑企勁 | 菫ｮ豁｣/蜑企勁/辟｡蜉ｹ蛹・| spec 0莉ｶ繝ｭ繝ｼ繝峨（mport broken縲…i-main縺ｨ讖溯・驥崎､・|
| 2026-03-07 | CI繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ11竊・謨ｴ逅・| 邨ｱ蜷・蛟句挨邯ｭ謖・| 驥崎､・賜髯､ (task-validation, documentation, openspecﾃ・ 蜑企勁) |
| 2026-03-07 | CI譁ｹ驥・ 譛蟆城剞縺ｮ蠢・ｦ∝香蛻・| 螟壽ｩ溯・CI/譛蟆修I | broken workflow縺ｮ菫晏ｮ医さ繧ｹ繝・> 謠蝉ｾ帑ｾ｡蛟､ |
| 2026-03-08 | Path B螳悟・蜑企勁 (Path A荳譛ｬ蛹・ | 邯ｭ謖・deprecate/螳悟・蜑企勁/迴ｾ迥ｶ邯ｭ謖・| YMM4荳譛ｬ蛹匁婿驥昴↓蜷郁・縲・MM4閾ｪ菴薙′Voicevox騾｣謳ｺ蜿ｯ閭ｽ縺ｧPath B縺ｮ蟄伜惠諢冗ｾｩ縺ｪ縺・|
| 2026-03-09 | Voice閾ｪ蜍慕函謌振I蜆ｪ蜈亥ｮ溯｣・| E2E謇句虚讀懆ｨｼ蜈郁｡・Voice UI蜈郁｡・| YMM4 SDK萓晏ｭ倥・隗｣豎ｺ縺梧怙邨ゅΡ繝ｼ繧ｯ繝輔Ο繝ｼ遒ｺ遶九↓蠢・・|
| 2026-03-09 | SimpleLogger encoding-safe蛹・| logger菫ｮ豁｣/CI env險ｭ螳壹・縺ｿ/謾ｾ鄂ｮ | Windows CI (cp1252)縺ｧ譌･譛ｬ隱槭Ο繧ｰ蜃ｺ蜉帶凾縺ｮUnicodeEncodeError隗｣豎ｺ縲・safe_print()縺ｧ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ+PYTHONIOENCODING=utf-8縺ｧ繝吶Ν繝医い繝ｳ繝峨し繧ｹ繝壹Φ繝繝ｼ |

| 2026-03-10 | Path A/B音声責務の明確化 | 旧仕様は外部音源準備、現行はYMM4で音声合成+最終レンダリング | docs/ymm4_integration_arch.md と docs/workflow_boundary.md を更新し運用境界を固定 |
| 2026-03-10 | docs旧コマンド参照のCIガード導入 | 再発防止/仕様逸脱の早期検知 | scripts/check_doc_command_references.py を追加し ci-main.yml に組み込み |
| 2026-03-11 | WAV-to-YMM4インポート経路はレガシー破棄 | WAVコピー維持/除去 | YMM4が唯一の音声合成環境。Python側WAV準備は不要、_copy_audio_assets除去 |
| 2026-03-11 | SP-024 Voice自動生成UIをCsvImportDialogに統合 | 別ダイアログ/既存ダイアログ拡張 | 既存CsvImportDialogにチェックボックス追加が最小変更。VoiceSpeakerDiscovery 3層フォールバックで堅牢性確保 |

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