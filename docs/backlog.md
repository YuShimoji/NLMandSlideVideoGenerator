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
| アニメーション7種 (SP-033 Phase 1) | 完成 | Values in-place方式、YMM4実機テストPASS (2026-03-16) |
| Baseline E2E (SP-027) | 完成 | CSV→YMM4→mp4 全工程完走確認 (2026-03-16) |
| CsvAssembler (SP-032 Phase A-D) | 完成 | 台本→CSV一気通貫 + CLI + Streamlit UI |
| 研究ワークフロー CLI | 完成 | collect→align→review→CSV + pipeline一気通貫 (scripts/research_cli.py) |
| Gemini SDK移行 | 完成 | google-generativeai → google-genai |
| 字幕生成 (SRT/ASS/VTT) | 完成 | |
| 長文自動分割 | 完成 | |
| サムネイル自動生成 | 完成 | |
| メタデータ自動生成 | 完成 | |

---

## アクティブタスク

| ID | 内容 | 状態 | 備考 |
|----|------|------|------|
| SP-028 | Post-Voice Timeline Resync | 未着手 | Voice生成後の実音声長でItem再計算。次の優先タスク |
| SP-030 | トランジション + 字幕テンプレート | 未着手 | FadeIn/Out + 話者色分け |

---

## 未実装 / 今後の検討

| 領域 | 内容 | 優先度 | 仕様 | 備考 |
|------|------|--------|------|------|
| タイミング | Post-Voice Timeline Resync | 高 | SP-028 | Voice生成後の実音声長でItem再計算 |
| トランジション | FadeIn/Out + 字幕テンプレート | 中 | SP-030 | スライド間遷移 + 字幕位置・色統一 |
| スタイル | テンプレートJSON + Pre-Export検証 | 中 | SP-031 | 品質を構造で安定化 |
| 素材 | ストック素材API (Pexels/Unsplash) | 中 | SP-033 Phase 2 | スライド画像の自動調達 |
| 素材 | AI生成イラスト | 低 | SP-033 Phase 3 | Gemini画像生成統合 |
| API連携 | Gemini/Google Slides API | 低 | | CsvScriptCompletionPlugin |
| 品質 | 型ヒント・Docstring整備 | 低 | | 継続 |

---

## ロードマップ

### 短期 (1-2週間): タイミング安定化

```
SP-028 (Post-Voice Timeline Resync) → SP-030 (トランジション)
```

- SP-028: Voice生成後の実音声長でImageItem/TextItemのLength再計算
- SP-030: FadeIn/Out + 字幕テンプレート (位置・フォント・話者色分け)
- 成功条件: 音声終了と同時に次スライドへ遷移、無音区間1秒以内

### 中期 (1-2ヶ月): 品質パイプライン

```
SP-028 (タイミング安定化) → SP-030 (トランジション) → SP-033 Phase 2 (素材API)
```

- SP-028: Voice生成後の実音声長でタイムライン再計算
- SP-030: FadeIn/Out + 字幕テンプレート (位置・フォント・話者色分け)
- SP-033 Phase 2: ストック素材API (Pexels/Unsplash) 統合
- ドキュメント整備: SP-004 (85%), SP-006 (60%), SP-007 (50%)

### 長期 (3ヶ月+): テンプレート化・自動化

- SP-031: スタイルテンプレートJSON + Pre-Export Validation
- SP-033 Phase 3: AI生成イラスト
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

---

## 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様
- `docs/ymm4_final_workflow.md` — 最終ワークフロー
- `docs/e2e_verification_guide.md` — E2E検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
