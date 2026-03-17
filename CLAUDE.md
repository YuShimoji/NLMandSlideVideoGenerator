# NLMandSlideVideoGenerator

CSVから動画・字幕のサムネイルを生成するパイプライン。Python / YMM4 連携。

## PROJECT CONTEXT
プロジェクト名: NLMandSlideVideoGenerator
環境: Python 3.11 (venv) / .NET 10.0 (YMM4 plugin) / Windows 11
ブランチ戦略: trunk-based (master)
現フェーズ: 実運用品質仕上げ
直近の状態 (2026-03-17 session 3 nightshift):
  - 全40仕様 (SP-001〜SP-040)。34 done + 3 partial (SP-035/SP-039/SP-040) + 2 draft (SP-037/SP-038) + 1 archived
  - SP-036 Script Style Presets → done (100%): 42テスト追加で全機能検証完了
  - SP-040 Batch Production Queue (60%→80%): 11テスト追加。Phase 1+2完了。Web UIバッチ残
  - SP-039 MP4 Quality Verification (80%): FFprobeチェッカー + CLI verify + 17テスト
  - ruff/mypy リグレッション5件修正 (全0)
  - ドキュメント全面同期: backlog.md 陳腐化更新、テスト数7ファイル同期
  - テスト: 1050 passed, 0 warnings, Ruff 0, Mypy 0
  - Brave Search API 移行完了 (Google Custom Search JSON API は新規利用不可・2027/1終了)
  - 残: BRAVE_SEARCH_API_KEY設定, SP-035 YMM4実機テスト, SP-040 Web UI, SP-037/038 (draft)

## DECISION LOG
| 日付 | 決定事項 | 選択肢 | 決定理由 |
|------|----------|--------|----------|
| 2026-03-01 | 16:9スライド動画+ゆっくりボイス優先 | 16:9/縦型/Shorts | プロジェクト本来の目的に合致 |
| 2026-03-01 | キャラ表示: オプション、時刻動画: nice-to-have | 必須オプション/不要 | MVPスコープ縮小 |
| 2026-03-04 | YMM4一本化 (Path A primary) | YMM4のみ/MoviePy併用/両方継続 | YMM4がfinal renderer。Python は前処理・素材準備 |
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
| 2026-03-15 | SP-033 Direct API移行 (リフレクション全廃) | Direct API/リフレクション継続 | Animation.From/To が安定動作。リフレクションは脆弱で不透明度0%バグの原因だった |
| 2026-03-17 | SP-033 Phase 2: Pexels/Pixabay二重構成 | Pexels単独/Pixabay単独/両方 | Pexels高品質(200req/h)+Pixabayフォールバック(5000req/h)の冗長構成 |
| 2026-03-17 | auto-review: orphaned→adopt方針 | adopt/reject | ソース不一致でもスクリプトとしては有効。mockフォールバック時にも有用な出力を保証 |
| 2026-03-17 | 30分+対応: セグメント数ヒント動的生成 | 固定/動的 | target_durationからセグメント数目安を算出。5分=5-7、15分=10-15、30分=20-30、60分+=30-45 |
| 2026-03-17 | Geminiモデルフォールバックチェーン | 単一モデル固定/フォールバックチェーン | gemini-2.5-flash(高品質)→gemini-2.0-flash(高クォータ)→モック。GEMINI_MODEL env varで切替可。無料枠20req/day制限への対策 |
| 2026-03-17 | ターゲット: YouTube一般公開の長尺解説動画 | 自分用/YouTube公開/未定 | YouTube公開を前提とした品質・ワークフロー設計。ニュース/解説/汎用 |
| 2026-03-17 | 想定尺: 長尺(20-30分+)、制作ペース: 週1本以上 | 短尺/中尺/長尺 | 一晩3本ペースの制作能力を想定。短尺は旨味がない |
| 2026-03-17 | 品質4軸: 制作スピード+情報密度+視覚完成度+一貫性 | 各軸単独優先/全軸 | 全4軸を重視。情報密度はNotebookLM/Geminiプロンプト整備に依存する部分が大きい |
| 2026-03-17 | OP/ED: 不要 | 必要/後回し/不要 | 動画本編のみで十分。制作コストに見合わない |
| 2026-03-17 | カバレッジ基準: 全体84%/コア92%で十分 | 85%全体目標追求/コア基準採用 | 外部API 4件+レガシースタブ1件は実API/SDK依存でテスト不能。コアモジュール92%が実質的な品質指標 |
| 2026-03-17 | SP-039 MP4品質検証はPhase 1(FFprobe+CLI)先行 | Phase 1のみ/Phase 1+2同時 | Phase 2 (SP-038 YouTube連携) は本番OAuth未整備のため後送り |
| 2026-03-18 | Google Custom Search → Brave Search API 移行 | Brave/Serper/Tavily/Vertex AI/現状維持 | Custom Search JSON APIが新規利用不可(2027/1完全終了)。Brave Search APIは独自インデックス+$5/月無料枠で十分 |
| 2026-03-18 | Imagen 3→4 移行 | imagen-4.0-generate-001 | Imagen 3は廃止済み。Imagen 4 (standard/fast/ultra) が現行。ただしGemini無料プランでは利用不可(400 paid plans only) |

## Key Paths

- Source: `src/`
- Tests: `tests/`
- Config: `config/`
- YMM4 Plugin: `ymm4-plugin/`
- Docs: `docs/`
- Spec Index: `docs/spec-index.json`
- Samples: `samples/`

## Rules

- Respond in Japanese
- No emoji
- Do NOT read `docs/reports/`, `docs/inbox/` unless explicitly asked
- Use Serena's symbolic tools (find_symbol, get_symbols_overview) instead of reading entire .py files
- When exploring code, start with get_symbols_overview, then read only the specific symbols needed
- Keep responses concise - avoid repeating file contents back to the user
