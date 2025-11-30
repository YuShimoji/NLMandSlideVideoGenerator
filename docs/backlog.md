# 開発バックログ

最終更新: 2025-11-30

---

## フェーズ概要

| フェーズ | 目的 | 状態 |
|----------|------|------|
| A | NotebookLM / Slides 実装・整備（コア機能） | 🟢 進行中（A-4完了） |
| B | Web / API 運用性向上（UI・ジョブ管理） | 🟢 進行中（B-1完了） |
| C | 新モード UX 向上（CSV / YMM4） | 🟢 進行中（基盤完了） |

## 完了タスク（直近）

| ID | 内容 | 完了日 |
|----|------|--------|
| A-2 | Transcript / Script I/O仕様固定と実装 | 2025-11-28 |
| A-3 | Slides API最小プロトタイプ着手 | 2025-11-28 |
| A-3-3 | Geminiスライド検証とログ強化 | 2025-11-28 |
| C-1 | CSVタイムラインモード基盤実装 | 2025-11-30 |
| C-2 | YMM4エクスポートPoC + 仕様書 | 2025-11-30 |
| - | SofTalk/AquesTalk TTSバッチ連携 | 2025-11-30 |
| - | WAV検出バグ修正 + ログ強化 | 2025-11-30 |
| A-4 | 動画合成強化（PPTX抽出/FFmpegフォールバック） | 2025-11-30 |
| B-1 | ジョブ管理機能（進捗追跡/キャンセル） | 2025-11-30 |

---

## フェーズ A: NotebookLM / Slides 実装・整備

### A-1: NotebookLM / 音声生成 API 実装

| ID | ファイル | 行 | 内容 | 優先度 |
|----|----------|-----|------|--------|
| A1-1 | `notebook_lm/audio_generator.py` | 93 | NotebookLM API 実装 | 高 |
| A1-2 | `notebook_lm/audio_generator.py` | 120 | アップロード処理実装 | 高 |
| A1-3 | `notebook_lm/audio_generator.py` | 138 | 音声生成リクエスト実装 | 高 |
| A1-4 | `notebook_lm/audio_generator.py` | 164 | 生成状態確認実装 | 中 |
| A1-5 | `notebook_lm/audio_generator.py` | 188 | 状態確認実装 | 中 |
| A1-6 | `notebook_lm/audio_generator.py` | 203 | URL取得実装 | 中 |

### A-2: ソース収集・文字起こし実装

| ID | ファイル | 行 | 内容 | 優先度 |
|----|----------|-----|------|--------|
| A2-1 | `notebook_lm/source_collector.py` | 148 | 検索 API 実装 | 高 |
| A2-2 | `notebook_lm/transcript_processor.py` | 98 | NotebookLM 音声アップロード実装 | 高 |
| A2-3 | `notebook_lm/transcript_processor.py` | 118 | 文字起こし実装 | 高 |
| A2-4 | `notebook_lm/transcript_processor.py` | 394 | 台本修正処理実装 | 中 |
| A2-5 | `youtube/metadata_generator.py` | 372 | ソース情報を台本から抽出 | 低 |

### A-3: Google Slides 連携実装

| ID | ファイル | 行 | 内容 | 優先度 |
|----|----------|-----|------|--------|
| A3-1 | `slides/slide_generator.py` | 337 | Google Slides 自動化実装 | 高 |
| A3-2 | `slides/slide_generator.py` | 359 | プレゼンテーション作成実装 | 高 |
| A3-3 | `slides/slide_generator.py` | 425 | スライド作成実装 | 高 |

### A-4: 動画合成・エフェクト実装 ✅ 完了 (2025-11-30)

| ID | ファイル | 内容 | 状態 |
|----|----------|------|------|
| A4-1 | `core/editing/moviepy_backend.py` | plan 情報を VideoComposer に渡す | ✅ 完了 |
| A4-2 | `video_editor/video_composer.py` | PPTX からの抽出 | ✅ 完了 (LibreOffice/python-pptx) |
| A4-3 | `video_editor/video_composer.py` | FFmpeg フォールバック動画合成 | ✅ 完了 |
| A4-4 | `video_editor/video_composer.py` | 座標処理実装 | ⚪ 待機 (低優先) |

---

## フェーズ B: Web / API 運用性向上

### B-1: ジョブ管理機能 ✅ 完了 (2025-11-30)

| ID | ファイル | 内容 | 状態 |
|----|----------|------|------|
| B1-1 | `web/logic/pipeline_manager.py` | リアルタイム進捗追跡 | ✅ 完了 |
| B1-2 | `web/logic/pipeline_manager.py` | 非同期キャンセル対応 | ✅ 完了 |
| B1-3 | `core/persistence/__init__.py` | 進捗保存/取得API | ✅ 完了 |
| B1-4 | `web/logic/pipeline_manager.py` | バックグラウンドタスク実行 | ✅ 完了 |

### B-2: Web UI ページ実装

| ID | ファイル | 行 | 内容 | 優先度 |
|----|----------|-----|------|--------|
| B2-1 | `web/ui/pages.py` | 257 | アセット管理ページ実装 | 中 |
| B2-2 | `web/ui/pages.py` | 290 | 設定管理ページ実装 | 中 |

---

## フェーズ C: 新モード UX 向上

### C-1: CSV タイムラインモード

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| C1-1 | CLI 専用エントリポイント作成 | 中 | ✅ 完了 (`run_csv_pipeline.py`) |
| C1-2 | Web フォーム（CSV + audio_dir 入力）作成 | 中 | ⚪ 待機 |
| C1-3 | CSV フォーマット仕様ドキュメント作成 | 低 | ✅ 完了 (`tts_batch_softalk_aquestalk.md`) |
| C1-4 | SofTalk/AquesTalk TTSバッチスクリプト | 中 | ✅ 完了 |
| C1-5 | Speaker列→声プリセットマッピング | 中 | ✅ 完了 |

### C-2: YMM4 エクスポート

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| C2-1 | AutoHotkey 連携の安定化 | 中 | ⚠️ PoC実装済み |
| C2-2 | テンプレート差分適用の整理 | 中 | ⚠️ プロトタイプ |
| C2-3 | 使い方ドキュメント作成 | 低 | ✅ 完了 (`ymm4_export_spec.md`) |
| C2-4 | YMM4 REST API 連携調査 | 低 | ⚪ 待機 |

### C-3: YMM4 ギャップ解消（設計→実装乖離対応）

> 参照: `docs/ymm4_export_spec.md` §2.3

| ID | 内容 | ギャップ | 優先度 | 状態 |
|----|------|----------|--------|------|
| C3-1 | YMM4 REST APIクライアント実装 | 大 | 低 | ⚪ API調査待ち |
| C3-2 | API経由タイムライン挿入 | 大 | 低 | ⚪ C3-1依存 |
| C3-3 | 書き出しフォールバック戦略完成 | 中 | 中 | ⚪ API→AHK→MoviePy |
| C3-4 | AutoHotkey実用化 | 中 | 中 | ⚠️ PoC段階 |
| C3-5 | テンプレート差分適用整備 | 中 | 低 | ⚠️ プロトタイプ |

---

## 完了済みタスク（参考）

| 日付 | 内容 |
|------|------|
| 2025-11-25 | ロガー統一（8ファイル） |
| 2025-11-25 | `ModularVideoPipeline` に Stage2/3 ヘルパー追加 |
| 2025-11-25 | `TranscriptProcessor` に `process_transcript()` エイリアス追加 |
| 2025-11-25 | モックテスト修正（8/8 成功） |
| 2025-11-25 | `core.utils.logger` に `debug()` メソッド追加 |

---

## 軽微改善・技術的負債

| ID | 内容 | 状態 |
|----|------|------|
| D-1 | 型ヒント・Docstring 整備 | ⚪ 継続 |
| D-2 | 未使用インポートの整理 | ⚪ 継続 |
| D-3 | 設定値の `config/settings.py` への集約 | ⚪ 継続 |
| D-4 | エラーハンドリングの統一（カスタム例外クラス） | ⚪ 継続 |
| D-5 | Web UI アセット管理ページ スケルトン実装 | ✅ 完了 (2025-11-25) |
| D-6 | Web UI 設定管理ページ スケルトン実装 | ✅ 完了 (2025-11-25) |
| D-7 | パイプラインマネージャー ステータス追跡の仮実装 | ✅ 完了 (2025-11-25) |
| D-8 | パイプラインマネージャー キャンセル機能の仮実装 | ✅ 完了 (2025-11-25) |

---

## 次のアクション

### 推奨優先順位

1. **B-2 Web UI ページ実装**
   - アセット管理ページ完全実装
   - 設定管理ページ完全実装
2. **C-3-4 AutoHotkey実用化**
   - YMM4連携PoC → 実用レベル
3. **A-3 Google Slides連携**
   - 実際のAPI実装へ着手

### 保留中
- A-1 NotebookLM API: 公式API待ち
- C-3-1/C-3-2 YMM4 REST API: 調査段階（https://ymm-api-docs.vercel.app/）
