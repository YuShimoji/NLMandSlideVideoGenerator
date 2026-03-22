# 開発バックログ

最終更新: 2026-03-18 (session 12 nightshift)

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
| アニメーション8種 (SP-033 Phase 1 + SP-004 pan_down) | 完成 | Values in-place方式、YMM4実機テストPASS |
| Baseline E2E (SP-027) | 完成 | CSV→YMM4→mp4 全工程完走確認 |
| Post-Voice Timeline Resync (SP-028) | 完成 | WavDurationReader+VoiceLength同期実装済み |
| トランジション+字幕テンプレート (SP-030) | 完成 | FadeIn/FadeOut 0.5秒+Border/Bold/CenterBottom/話者色分け6色 |
| CsvAssembler (SP-032 Phase A-D) | 完成 | 台本→CSV一気通貫 + CLI + Streamlit UI |
| 研究ワークフロー CLI | 完成 | collect→align→review→CSV + pipeline一気通貫 + --auto-images + --duration |
| Gemini SDK移行 | 完成 | google-generativeai → google-genai |
| 字幕生成 (SRT/ASS/VTT) | 完成 | |
| 長文自動分割 | 完成 | |
| サムネイル自動生成 | 完成 | |
| メタデータ自動生成 | 完成 | |
| SP-036 Script Style Presets | 完成 | 4プリセットJSON + CLI --style + Web UIドロップダウン |
| Brave Search API 移行 | 完成 | Google Custom Search → Brave Search |
| Gemini 2.5-flash 一本化 | 完成 | 旧2.0-flash依存を全廃 |
| SP-037 Thumbnail Phase 1+2 | 完成 | パイプライン統合+CJKフォント+スタイルプリセット連携 |
| SP-043 Multi-LLM Provider Phase 1-3 | 完成 | ILLMProvider抽象化 + 5プロバイダー + 既存コード全移行 |
| F-004 フォールバック可視化 | 完成 | PipelineStats fallback_events + FALLBACK WARNING |
| F-006 クレジット自動統合 | 完成 | パイプライン→metadata.json + image_credits自動統合 |
| SP-039 MP4品質検証 | 完成 | FFprobe 10検証項目 + SP-038連携 (upload前品質ゲート) |
| SP-041 TextSlide品質 Phase 1-3 | 完成 | 4レイアウト + グラデーション5テーマ + プリセット連携 |
| SP-043 Multi-LLM Phase 1-4 | 完成 | 5プロバイダー + 設定UI (Streamlit) |
| SP-044 セグメント尺制御 Phase 1-3 | 完成 | 推定尺 + 自動調整 + 手動モード CLI |

---

## アクティブタスク

現在アクティブなタスクなし。全て完了済みまたは未実装テーブルへ移動。

---

## 未実装 / 今後の検討

| 領域 | 内容 | 優先度 | 仕様 | 備考 |
|------|------|--------|------|------|
| 統合テスト | SP-035 YMM4実機テスト実施 | 中 | SP-035 (60%) | チェックリスト整備済み+pre-flight自動チェック。YMM4環境で実施待ち |
| YouTube公開 | SP-038 本番OAuthトークン取得+実チャンネルテスト | 中 | SP-038 (90%) | Phase 1-3実装完了。残: 本番OAuth取得・実チャンネルテストアップロード |
| 背景動画 | ループ背景動画レイヤー | 低 | なし | 実需発生時に仕様化。YMM4側で手動追加可能 |
| トピック自動取得 | Inoreader/RSSフィードからトピックを自動取得→topics.json生成 | 低 | SP-048 (80%) | Phase 1完了: クライアント+抽出+CLI+61テスト。残: 実API疎通、Phase 2パイプライン連携 |
| 品質 | 型ヒント・Docstring整備 | 低 | なし | 継続 |
| 整理 | BasicTimelinePlanner パイプライン接続確認 | 低 | なし | **NOT DEAD**: helpers.pyでYMM4 backend有効時に実体化。104行、テスト3件。削除不要 |
| 整理 | slide_builder.py のproduction接続確認 | 低 | なし | 246行。テストのみ使用 (test_slide_builder.py)。production未importだが害なし |

---

## ロードマップ

### 短期 (~1週): partial SP を done に

- SP-035 統合実機テスト (60%→100%): YMM4環境で手動実施
- SP-038 YouTube投稿 (90%→100%): 本番OAuthトークン取得 + 実チャンネルテスト

### 中期 (1-2ヶ月): 実運用開始

- 初回YouTube公開 (SP-038 + SP-039品質ゲート連携)
- バッチ制作 (SP-040) の日常運用テスト
- 実運用フィードバックに基づく摩擦解消

### 長期 (3ヶ月+): 自動化 + スケーラビリティ

- Docker化 / CI-CD強化
- トピック自動取得 (RSS/Inoreader)
- Codecov統合

---

## 摩擦インベントリ

詳細は [docs/friction_inventory.md](friction_inventory.md) を参照。

| 摩擦 | 影響度 | 状態 |
|------|--------|------|
| F-001 Geminiクォータ枯渇 | CRITICAL | SP-043で解消 (LLM切替可能) |
| F-002 YMM4手動操作 | CRITICAL | 未解消 (YMM4 SDK制限) |
| F-003 レンダリング時間 | CRITICAL | 運用回避 (就寝時実行) |
| F-004 フォールバック非可視 | HIGH | 解消済 (FALLBACK WARNING) |
| F-005 セグメント粒度制御 | HIGH | SP-044で解消 (検証+自動調整) |
| F-006 クレジット未統合 | HIGH | 解消済 (metadata.json自動統合) |
| F-007 TextSlide生成速度 | MEDIUM | 未対応 |
| F-008 API key設定複雑さ | MEDIUM | 部分対応 (.env.example) |
| F-009 手動プレビュー負荷 | MEDIUM | 未対応 |

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
- 2026-03-15: 研究ワークフロー Phase 1-4 完了
- 2026-03-16: SP-033 Direct API全面移行、SP-027 E2E完走
- 2026-03-17: SP-031/033 Phase 2-3 完了、SP-028/030 done
- 2026-03-18: SP-036/037/040/041/042 完了、Brave移行、SP-043 Phase 1-3
- 2026-03-18: 摩擦インベントリ + F-004/F-006 + SP-044 Phase 1-2
- 2026-03-18: SP-020→SP-031統合、SP-041 Phase 3、SP-043 Phase 4、SP-044 Phase 3
- 2026-03-18: nightshift — 仕様書同期8件(Imagen4, pct100%), 開発ガイド全面更新, INDEX拡充
- 2026-03-21: SP-047 Phase 2実検証(台本品質全指標PASS) + Phase 3(Wikimedia Commons統合+TextSlideアニメーション)
- 2026-03-21: デッドコード削除3件 (TikTokAdapter 221行 + IPublishingQueue 7行 + Gemini+TTS 60行)

---

## 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様
- `docs/ymm4_final_workflow.md` — 最終ワークフロー
- `docs/e2e_verification_guide.md` — E2E検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/background_enrichment_design.md` — 背景充実化設計 (SP-033 Phase 2)
- `docs/friction_inventory.md` — 摩擦インベントリ (体験逆算)
