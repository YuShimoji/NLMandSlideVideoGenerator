# DECISION LOG Archive (2026-03-01 ~ 2026-03-14)

Archived: 2026-03-23 (session 21)
Reason: 15件超過 (77件→35件に削減)。以下は完了済みまたは前提が確定した決定。

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
