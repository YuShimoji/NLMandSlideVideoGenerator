# 開発バックログ

最終更新: 2026-03-18

---

## 現在の制作パス

```
[CSV作成 (Web UI)] → [YMM4 (NLMSlidePlugin CSVインポート)] → [音声生成(台本機能)] → [動画出力] → [mp4]
```

Path A (YMM4一本化) が唯一の制作経路。Path B (MoviePy) は 2026-03-08 に完全削除済み。

---

## 実装済み機能

| 機能 | 状態 | 備考 |
|------|------|------|
| CSVタイムライン→YMM4プロジェクト出力 | 完成 | CLI + Web UI |
| NLMSlidePlugin CSVインポート | 完成 | CsvImportDialog + Ymm4TimelineImporter |
| Voice自動生成 UI接続 (SP-024) | 完成 | VoiceSpeakerDiscovery + CsvImportDialog |
| ImageItem自動配置 (SP-026) | 完成 | CSV 3列目に画像パス指定 |
| アニメーション8種 (SP-033 Phase 1 + SP-004 pan_down) | 完成 | Values in-place方式、YMM4実機テストPASS (2026-03-16、pan_down追加 2026-03-17) |
| Baseline E2E (SP-027) | 完成 | CSV→YMM4→mp4 全工程完走確認 (2026-03-16) |
| Post-Voice Timeline Resync (SP-028) | 完成 | WavDurationReader+VoiceLength同期実装済み |
| トランジション+字幕テンプレート (SP-030) | 完成 | FadeIn/FadeOut 0.5秒+Border/Bold/CenterBottom/話者色分け6色 |
| CsvAssembler (SP-032 Phase A-D) | 完成 | 台本→CSV一気通貫 + CLI + Streamlit UI |
| 研究ワークフロー CLI | 完成 | collect→align→review→CSV + pipeline一気通貫 + --auto-images + --duration (scripts/research_cli.py) |
| Gemini SDK移行 | 完成 | google-generativeai → google-genai |
| 字幕生成 (SRT/ASS/VTT) | 完成 | |
| 長文自動分割 | 完成 | |
| サムネイル自動生成 | 完成 | |
| メタデータ自動生成 | 完成 | |
| SP-036 Script Style Presets | 完成 | 4プリセットJSON + CLI --style + Web UIドロップダウン。42テストPASS (2026-03-18) |
| Brave Search API 移行 | 完成 | Google Custom Search → Brave Search。独自インデックス+無料枠 (2026-03-18) |
| Gemini 2.5-flash 一本化 | 完成 | 旧2.0-flash依存を全廃。単一モデルで品質統一 (2026-03-18) |
| SP-037 Thumbnail Phase 1 | 完成 | generate_from_script() + run_pipeline統合 + CJKフォント対応 (2026-03-18) |

---

## アクティブタスク

現在アクティブなタスクなし。全て完了済みまたは未実装テーブルへ移動。

---

## 未実装 / 今後の検討

| 領域 | 内容 | 優先度 | 仕様 | 備考 |
|------|------|--------|------|------|
| サムネイル | SP-037 Phase 2: スタイルプリセット連携、レイアウト改善 | 中 | SP-037 (60%) | Phase 1完了。残: スタイル連携、高品質レイアウト |
| バッチ制作 | SP-040 Batch Production Queue Web UI統合 | 中 | SP-040 (80%) | Phase 1+2完了(11テスト)。Web UIバッチ実行画面残 |
| MP4品質検証 | SP-039 FFprobe自動チェック + YouTube連携 | 中 | SP-039 (80%) | Phase 1完了 (17テスト)。Phase 2 (SP-038連携) 後送り |
| 統合テスト | SP-035 YMM4実機テスト実施 | 中 | SP-035 (50%) | チェックリスト整備済み。YMM4環境で実施待ち |
| YouTube公開 | SP-038 メタデータ生成→アップロードの一気通貫接続 | 中 | SP-038 (draft) | MetadataGenerator, YouTubeUploader個別実装済み。OAuth未整備 |
| クレジット自動挿入 | ストック画像のPexels/PixabayクレジットをYouTube説明欄に自動追記 | 低 | なし | StockImageClientでcredit情報は取得済み。ライセンス準拠 |
| 背景動画 | ループ背景動画レイヤー | 低 | なし | 実需発生時に仕様化。YMM4側で手動追加可能 |
| トピック自動取得 | Inoreader/RSSフィードからトピックを自動取得→topics.json生成 | 低 | なし | バッチ制作日常化時に再訪。Inoreader API or 直接RSS/Atomパース |
| 品質 | 型ヒント・Docstring整備 | 低 | なし | 継続 |

---

## ロードマップ

### 短期 (~1週): partial SP を done に

- SP-037 Thumbnail Phase 2 (60%→100%): スタイルプリセット連携 + レイアウト改善
- SP-040 Batch Production Queue (80%→100%): Web UI統合
- SP-039 MP4 Quality Verification (80%→100%): SP-038連携待ち
- SP-035 統合実機テスト (50%→100%): YMM4環境で実施

### 中期 (1-2ヶ月): YouTube公開パイプライン

- SP-038 YouTube Publish Pipeline (draft→done): OAuth整備 + 自動公開
- Gemini有料プラン検討 (無料枠20req/day → 本番運用)

### 長期 (3ヶ月+): 自動化 + スケーラビリティ

- Docker化 / CI-CD強化
- 多言語台本自動照合強化
- Codecov統合

---

## 完了タスク（アーカイブ）

過去の完了タスクは `docs/archive/` 内の各ハンドオーバードキュメントを参照。

主要マイルストーン:
- 2025-11-28: Transcript/Script I/O仕様固定
- 2025-11-30: CSVタイムラインモード基盤、YMM4エクスポートPoC
- 2025-12-01: E2E動画書き出し検証、テスト97 passed
- 2026-03-04: 外部TTS統合 CLOSED、pipeline.pyリファクタリング(-69%)
- 2026-03-08: Path B完全削除、YMM4一本化
- 2026-03-09: SP-024 Voice自動生成UI完了
- 2026-03-14: SP-026 ImageItem自動配置完了
- 2026-03-14: SP-032 CsvAssembler + YMM4 backend統合
- 2026-03-15: 研究ワークフロー Phase 1-4 完了 (CLI review + E2Eテスト)
- 2026-03-15: SP-032 Phase C完了 (CLI pipeline サブコマンド: collect→script→align→review→CsvAssembler)
- 2026-03-15: SP-032 Phase D完了 (Streamlit UI素材パイプライン)、Gemini SDK移行
- 2026-03-16: SP-033 Direct API全面移行 (リフレクション全廃、-312行)
- 2026-03-16: SP-027 Baseline E2E完走 + SP-033 Phase 1 全7種アニメーション実機テストPASS
- 2026-03-17: SP-028 既存実装発見 (WavDurationReader+VoiceLength同期)、ステータス→done
- 2026-03-17: SP-030 既存実装発見 (ApplySubtitleStyle: 話者色6色+Border+CenterBottom)、ステータス→done
- 2026-03-17: SP-033 Phase 2 StockImageClient完了: Pexels/Pixabay + CLIパイプライン統合 + 30分+対応プロンプト改善
- 2026-03-16: SP-033 Phase 2a 背景充実化基盤: SegmentClassifier + VisualResourceOrchestrator + CsvAssembler拡張 + テスト78件PASS
- 2026-03-16: SP-033 Phase 2b パイプライン統合 + 30分動画E2Eテスト: クエリ重複バグ修正 (48%→74%ヒット率)、CLI/UI統合完了
- 2026-03-16: SP-033 Phase 2b エラーハンドリング強化: _request_with_retry (指数バックオフ/429/5xx/接続エラー)、validate_api_keys()、Orchestrator進捗ログ改善
- 2026-03-17: SP-033 Phase 2c 完了: Gemini分類+キーワード抽出+日英翻訳+Orchestrator統合。テスト228件PASS
- 2026-03-16: SP-034 パイプラインステップ再開機能: PipelineState永続化+CLI --resume+UI再開セクション+テスト16件PASS
- 2026-03-17: SP-031 Phase 1 完了: ExportValidator+StyleTemplateManager+3テンプレート(default/cinematic/minimal)+CLI validate/templates。テスト280件PASS
- 2026-03-17: SP-031 Phase 2 完了: style_template.json v1.1 (video/crossfadeセクション追加)、C# StyleTemplateLoader拡張(VideoConfig/CrossfadeConfig)、ValidateImportItems拡張(連続同一画像検出/統計サマリー)
- 2026-03-16: SP-031 C#ハードコード値全面テンプレート化: ApplySubtitleStyle/ApplyAnimationDirect/GetSpeakerColor/crossfade/padding/defaultDuration全てstyle_template.json参照に置換
- 2026-03-17: SP-033 Phase 3 完了: AIImageProvider (Gemini Imagen 3.0) + Orchestrator AI統合 (stock→AI→slideフォールバック連鎖) + source分離。テスト301件PASS
- 2026-03-17: SP-031 BGMテンプレート完了: style_template.json bgmセクション (volume/fadeIn/fadeOut/layer) + Python/C#双方対応。テスト330件PASS
- 2026-03-18: SP-036 Script Style Presets done (42テストPASS)
- 2026-03-18: Brave Search API移行完了 (Google Custom Search廃止対応)
- 2026-03-18: Gemini 2.5-flash一本化
- 2026-03-18: SP-037 Thumbnail Phase 1完了 (CJKフォント対応含む)

---

## 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様
- `docs/ymm4_final_workflow.md` — 最終ワークフロー
- `docs/e2e_verification_guide.md` — E2E検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/background_enrichment_design.md` — 背景充実化設計 (SP-033 Phase 2)
