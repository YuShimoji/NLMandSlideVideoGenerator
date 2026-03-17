# 開発バックログ

最終更新: 2026-03-17

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

---

## アクティブタスク

| ID | 内容 | 状態 | 備考 |
|----|------|------|------|
| SP-030 | 字幕テンプレート | 完了 | FadeIn/Out+字幕テンプレート(Border/Bold/CenterBottom/話者色分け6色)+PlaybackRate修正。実機テスト待ち |
| SP-033 Phase 2a | ストック素材API + 背景充実化基盤 | 完了 | StockImageClient + SegmentClassifier + VisualResourceOrchestrator + CsvAssembler拡張。テスト78件PASS |
| SP-033 Phase 2b | パイプライン統合 + E2E検証 | 完了 | CLI/UI統合済み + Pexels実API動作確認 + 30分動画テスト (74%ヒット率) + クエリ重複バグ修正 |
| SP-033 Phase 2c | Gemini検索品質改善 | 完了 | Gemini分類+英語キーワード抽出+クエリ翻訳+Orchestrator統合。テスト228件PASS |
| SP-034 | パイプラインステップ再開 | 完了 | PipelineState永続化+CLI --resume+UI再開セクション。テスト16件PASS |
| SP-031 Phase 1 | Pre-Export検証 + テンプレートマネージャー | 完了 | ExportValidator+StyleTemplateManager+CLI validate/templates。テスト280件PASS |
| SP-033 Phase 3 | AI画像生成 + Orchestrator統合 | 完了 | AIImageProvider (Gemini Imagen) + stock失敗→AI→slideフォールバック連鎖 + CLI/UI統合。テスト301件PASS |
| SP-033 Phase 3b | テキストスライド自動生成 | 完了 | TextSlideGenerator: source=none→generated変換。PLACEHOLDER_THEMES使用。Orchestrator/CLI統合。テスト38件PASS |

---

## 未実装 / 今後の検討

| 領域 | 内容 | 優先度 | 仕様 | 備考 |
|------|------|--------|------|------|
| 字幕 | TextItem字幕テンプレート (話者色分け) | 完了 | SP-030 | Border/Bold/CenterBottom/MaxWidth/WordWrap/話者色6色サイクル |
| スタイル | テンプレートJSON + Pre-Export検証 | 完了 | SP-031 | Python StyleTemplateManager + C# StyleTemplateLoader統一読み込み。video/crossfade/bgmセクション。ValidateImportItems拡張。BGMテンプレート自動配置済み |
| 素材 | ストック素材API + 背景充実化 | Phase 2c完了 | SP-033 Phase 2 | StockImageClient + SegmentClassifier + Orchestrator + Gemini分類/キーワード統合済み |
| 素材 | AI生成イラスト | 完了 | SP-033 Phase 3 | AIImageProvider (Gemini Imagen) + Orchestrator統合 + CLI/UI自動有効 |
| 背景動画 | ループ背景動画レイヤー (Recommended) | 低 | なし | PROJECT_ALIGNMENT_SSOTで「必要時のみ加える」。YMM4側でVideoItemレイヤーを手動追加可能。自動化は実需が発生してから仕様化 |
| OP/ED | 冒頭タイトルカード + 締めテンプレート | 中 | なし | 動画の「完成品」感に直結。style_template.jsonに intro/outro セクション追加が候補 |
| サムネイル統合 | パイプライン出力にサムネイル自動生成を接続 | 中 | なし | src/core/thumbnails/ が存在するがパイプライン未統合 |
| YouTube公開 | メタデータ生成→アップロードの一気通貫接続 | 中 | なし | MetadataGenerator, YouTubeUploader個別実装済み。パイプライン統合なし |
| クレジット自動挿入 | ストック画像のPexels/PixabayクレジットをYouTube説明欄に自動追記 | 低 | なし | StockImageClientでcredit情報は取得済み。ライセンス準拠 |
| MP4品質自動検証 | FFprobeで出力MP4のcodec/duration/resolution/audio streamsを自動チェック | 低 | なし | 手動目視→自動化 |
| API連携 | Gemini/Google Slides API | 低 | | CsvScriptCompletionPlugin |
| 品質 | 型ヒント・Docstring整備 | 低 | | 継続 |

---

## ロードマップ

### 短期: 全SP完了

- SP-031: 全完了 (style_template.json v1.1 + BGMテンプレート + C#統合 + ValidateImportItems拡張)
- SP-033: 全Phase完了 (8種アニメ + StockImage + AIImage + TextSlide + Orchestrator統合)

### 中期 (1-2ヶ月): 実運用品質 + ドキュメント

- Geminiクォータリセット後の実コンテンツ品質確認
- YMM4実機テスト: BGMテンプレート + ストック画像CSV + 字幕テンプレート
- ドキュメント整備: SP-006 (90%), SP-007 (85%)
- Gemini有料プラン検討 (無料枠20req/day → 本番運用)

### 長期 (3ヶ月+): 自動化

- Docker化 / CI-CD強化
- バッチ処理 / 多言語対応

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

---

## 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様
- `docs/ymm4_final_workflow.md` — 最終ワークフロー
- `docs/e2e_verification_guide.md` — E2E検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/background_enrichment_design.md` — 背景充実化設計 (SP-033 Phase 2)
