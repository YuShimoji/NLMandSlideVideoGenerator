# 開発バックログ

最終更新: 2026-03-14

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
| 字幕生成 (SRT/ASS/VTT) | 完成 | |
| 長文自動分割 | 完成 | |
| サムネイル自動生成 | 完成 | |
| メタデータ自動生成 | 完成 | |

---

## アクティブタスク

| ID | 内容 | 状態 | 備考 |
|----|------|------|------|
| TASK_023 | E2E実証 (CSV→YMM4→mp4) | NEXT | Voice確認済み、ImageItem実機テスト待ち |

---

## 未実装 / 今後の検討

| 領域 | 内容 | 優先度 | 備考 |
|------|------|--------|------|
| スライド画像 | 画像の位置・サイズ調整（全画面フィット） | 高 | SP-026後続 |
| スライド画像 | アニメーション（パン・ズーム等） | 中 | ユーザー要件: 動きがあること |
| スライド画像 | slides_payload.jsonとの統合 | 低 | 現在はCSV 3列目方式のみ |
| API連携 | Gemini/Google Slides API統合 | 中 | CsvScriptCompletionPlugin (YMM4内) |
| 品質 | 型ヒント・Docstring整備 | 低 | 継続 |

---

## 完了タスク（アーカイブ）

過去の完了タスクは `docs/archive/` 内の各ハンドオーバードキュメントを参照。

主要マイルストーン:
- 2025-11-28: Transcript/Script I/O仕様固定
- 2025-11-30: CSVタイムラインモード基盤、YMM4エクスポートPoC
- 2025-12-01: E2E動画書き出し検証、テスト97 passed
- 2026-03-04: VOICEVOX統合 CLOSED、pipeline.pyリファクタリング(-69%)
- 2026-03-08: Path B完全削除、YMM4一本化
- 2026-03-09: SP-024 Voice自動生成UI完了
- 2026-03-14: SP-026 ImageItem自動配置完了

---

## 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様
- `docs/ymm4_final_workflow.md` — 最終ワークフロー
- `docs/e2e_verification_guide.md` — E2E検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
