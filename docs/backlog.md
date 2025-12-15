# 開発バックログ

最終更新: 2025-12-15

---

## フェーズ概要

| フェーズ | 目的 | 状態 |
|----------|------|------|
| A | NotebookLM / Slides 実装・整備（コア機能） | 🟢 進行中（A-4完了） |
| B | Web / API 運用性向上（UI・ジョブ管理） | ✅ 完了（B-1, B-2） |
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
| B-2 | Web UIページ完全実装（アセット管理/設定） | 2025-11-30 |
| C3-4 | AutoHotkey実用化（ログ/リトライ/音声インポート） | 2025-11-30 |
| D-9 | テストスイート修正（97 passed） | 2025-12-01 |
| C3-3 | 書き出しフォールバック戦略完成 | 2025-12-01 |
| E2E | E2E動画書き出し検証（フォールバック動作確認） | 2025-12-01 |
| D-10 | FFmpeg検出・インストール案内改善 | 2025-12-01 |
| C-1-2 | CSV Webフォーム作成 | 2025-12-01 |
| U-1 | ユーザー向けワークフローガイド作成 | 2025-12-01 |
| U-2 | CSV入力フォーマット仕様書作成 | 2025-12-01 |
| S-1 | サンプルCSV/WAVセット作成 | 2025-12-01 |
| S-2 | READMEクイックスタート追記 | 2025-12-01 |
| S-3 | CSVパイプラインWeb UIエラー体験改善 | 2025-12-01 |
| S-4 | CSVパイプラインWeb UI進捗表示改善 | 2025-12-01 |
| M-1 | CSVタイムライン統合テスト追加（97 passed） | 2025-12-01 |
| D-11 | README/UI/バックログ整合性整理 | 2025-12-01 |
| M-2 | YMM4テンプレート差分適用整備 | 2025-12-01 |
| S-6 | 音声ファイルのWeb UIドラッグ＆ドロップ対応 | 2025-12-01 |
| S-7 | Web UI結果画面強化（動画プレビュー・リンク） | 2025-12-01 |
| S-8 | 入力素材プレビュー（CSV/WAV一覧表示） | 2025-12-01 |
| S-9 | YouTube用サムネイル自動生成 | 2025-12-01 |
| S-10 | YouTube用メタデータ自動生成（APIなし） | 2025-12-01 |
| M-4 | プレースホルダースライドのテーマ化 | 2025-12-01 |
| M-5 | 字幕ハードサブ環境ガイド整備 | 2025-12-01 |
| S-5 | 環境チェックのWeb UI統合 | 2025-12-01 |
| C3-5-1 | YMM4テンプレート差分 export_outputs 連携・テスト追加 | 2025-12-02 |
| M-3 | 音声ファイル自動分割ツール | 2025-12-02 |
| UI-1 | ホームページのユーザー導線改善 | 2025-12-03 |
| UI-2 | ナビゲーションの整理と必須/オプション明示 | 2025-12-03 |
| D-12 | pytest実行時間短縮（integration/slowマーカー分離、スモーク運用確立） | 2025-12-13 |
| D-13 | API設定ガイドの秘匿情報削除（プレースホルダー化） | 2025-12-13 |
| D-14 | broad `except Exception` / bare `except` の整理（想定例外→catch-all、挙動/ログ維持） | 2025-12-14 |
| D-15 | ドキュメント導線整理（INDEX/README）+ 申し送り整備（HANDOVER_20251214） | 2025-12-14 |
| D-16 | Google Slides API 統合の堅牢化（OAuth refresh/利用可否チェック/フォールバックPPTX/VideoComposer PPTX参照修正） | 2025-12-15 |

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

### A-4: 動画合成・エフェクト実装 

| ID | ファイル | 内容 | 状態 |
|----|----------|------|------|
| A4-1 | `core/editing/moviepy_backend.py` | plan 情報を VideoComposer に渡す | |
| A4-2 | `video_editor/video_composer.py` | PPTX からの抽出 | |
| A4-3 | `video_editor/video_composer.py` | FFmpeg フォールバック動画合成 | |
| A4-4 | `video_editor/video_composer.py` | 座標処理実装 | |

---

## フェーズ B: Web / API 運用性向上

### B-1: ジョブ管理機能 

| ID | ファイル | 内容 | 状態 |
|----|----------|------|------|
| B1-1 | `web/logic/pipeline_manager.py` | リアルタイム進捗追跡 | |
| B1-2 | `web/logic/pipeline_manager.py` | 非同期キャンセル対応 | |
| B1-3 | `core/persistence/__init__.py` | 進捗保存/取得API | |
| B1-4 | `web/logic/pipeline_manager.py` | バックグラウンドタスク実行 | |

### B-2: Web UI ページ実装 

| ID | ファイル | 内容 | 状態 |
|----|----------|------|------|
| B2-1 | `web/ui/pages.py` | アセット管理ページ | |
| B2-2 | `web/ui/pages.py` | 設定管理ページ | |

---

## フェーズ C: 新モード UX 向上

### C-1: CSV タイムラインモード

| ID | 内容 | 優先度 | 状態 |
|----|------|--------|------|
| C1-1 | CLI 専用エントリポイント作成 | 中 | ✅ 完了 |
| C1-2 | Web フォーム（CSV + audio_dir 入力）作成 | 中 | ✅ 完了 |
| C1-3 | CSV フォーマット仕様ドキュメント作成 | 低 | ✅ 完了 |
| C1-4 | SofTalk/AquesTalk TTSバッチスクリプト | 中 | ✅ 完了 |
| C1-5 | Speaker列→声プリセットマッピング | 中 | ✅ 完了 |

### C-2: YMM4 エクスポート

| ID | 内容 | 優先度 | 状態 |
| C2-1 | AutoHotkey 連携の安定化 | 中 | |
| C2-2 | テンプレート差分適用の整理 | 中 | |
| C2-3 | 使い方ドキュメント作成 | 低 | |
| C2-4 | YMM4 プラグインAPI連携方針の検討 | 低 | |

#### C-3: YMM4 ギャップ解消（設計→実装乖離対応）

> 参照: `docs/ymm4_export_spec.md` §2.3

| ID | 内容 | ギャップ | 優先度 | 状態 |
|----|------|----------|--------|------|
| C3-1 | YMM4 プラグインAPIクライアント実装 | 大 | 低 | ⏸ 仕様不足で一旦保留 |
| C3-2 | プラグインAPI経由タイムライン挿入 | 大 | 低 | ⏸ C3-1保留に追従 |
| C3-3 | 書き出しフォールバック戦略完成 | 中 | 中 | ✅ 完了 |
| C3-4 | AutoHotkey実用化 | 中 | 中 | ✅ 完了 |
| C3-5 | テンプレート差分適用整備 | 中 | 低 | ✅ 完了 |

#### C-3-3 書き出しフォールバック戦略 詳細

| ID | 内容 | 状態 |
|----|------|------|
| C3-3-1 | `ExportFallbackManager`クラス実装 | |
| C3-3-2 | API→AHK→MoviePy優先順位設定 | |
| C3-3-3 | タイムアウト・リトライロジック | |
| C3-3-4 | バックエンド自動検出 | |
| C3-3-5 | テストスイート（10 passed） | |

#### C-3-4 AutoHotkey実用化 詳細タスク

| ID | 内容 | 状態 |
|----|------|------|
| C3-4-1 | YMM4ウィンドウ検出・起動待ち安定化 | |
| C3-4-2 | エラーハンドリング・リトライロジック | |
| C3-4-3 | タイムアウト戦略実装 | |
| C3-4-4 | ログ・デバッグモード | |
| C3-4-5 | タイムライン操作実装（音声インポート） | |
| C3-4-6 | 書き出しダイアログ操作 | |

---

## 完了済みタスク（参考）

| 日付 | 内容 |
|------|------|
| 2025-11-25 | ロガー統一（8ファイル） |
| 2025-11-25 | `ModularVideoPipeline` に Stage2/3 ヘルパー追加 |
| 2025-11-25 | `TranscriptProcessor` に `process_transcript()` エイリアス追加 |
| 2025-11-25 | モックテスト修正（8/8 成功） |
| 2025-11-25 | `core.utils.logger` に `debug()` メソッド追加 |
| 2025-12-01 | テスト修正: `ai_generator.py` style変数, `template_generator.py` import追加 |
| 2025-12-01 | テスト修正: `test_voice_pipelines.py` TTSモック方法改善 |
| 2025-12-01 | テスト修正: `test_script_providers.py` SourceInfo/Geminiモック |
| 2025-12-01 | テスト修正: `test_platform_adapters.py` uploaderモック方法改善 |
| 2025-12-01 | テスト修正: `test_thumbnail_generators.py` isinstance→hasattr変更 |

---

## 軽微改善・技術的負債

| ID | 内容 | 状態 |
|----|------|------|
| D-1 | 型ヒント・Docstring 整備 | |
| D-2 | 未使用インポートの整理 | |
| D-3 | 設定値の `config/settings.py` への集約 | |
| D-4 | エラーハンドリングの統一（カスタム例外クラス） | |
| D-5 | Web UI アセット管理ページ スケルトン実装 | |
| D-6 | Web UI 設定管理ページ スケルトン実装 | |
| D-7 | パイプラインマネージャー ステータス追跡の仮実装 | |
| D-8 | パイプラインマネージャー キャンセル機能の仮実装 | |
| D-9 | テストスイート修正（75 passed） | |

---

## 次のアクション

### 現在の方針（2025-12-03更新）

> **「APIなしワークフローの完成・安定化」** が完了。
> 次は **API連携フェーズ** への移行準備。

### 補足方針（2025-12-08追記 / 2025-12-10更新）

- CSV タイムラインモードは「`csv` + 行ごと `wav` が揃っていること」のみを前提とし、
  どの TTS エンジンで WAV を生成するかはユーザー環境に委ねる。
- SofTalk / AquesTalk ローカル TTS 連携（`scripts/tts_batch_softalk_aquestalk.py`）は、
  テンプレ実装として維持するが、環境依存が大きいため **主フローではなく任意の上級者向けオプション** として扱う。
- ゆっくり系音声については、**YMM4 に台本 CSV を読み込ませてプロジェクト内で音声生成するフロー** を最終形とし、
  フェーズ C-2 / C-3 系タスク（AutoHotkey 連携・YMM4 プラグインAPI連携）を通じて段階的に自動化していく。
  - 当初は「YMM4 REST API」を想定していたが、実際には **.NET プラグインAPI** が提供されているため、
    今後はプラグインAPIベースでの自動化を前提とする（詳細は `docs/ymm4_integration_arch.md` を参照）。

### 完了済み機能（APIなし運用）

```
[NotebookLM/SofTalk等で素材準備] → [CSV + WAV] → [このアプリ] → [動画出力]
```

| 機能 | CLI | Web UI | 状態 |
|------|-----|--------|------|
| CSVタイムライン→動画 | ✅ | ✅ | 完成 |
| 字幕生成 (SRT/ASS/VTT) | ✅ | ✅ | 完成 |
| YMM4プロジェクト出力 | ✅ | ✅ | 完成 |
| 長文自動分割 | ✅ | ✅ | 完成 |
| サムネイル自動生成 | ✅ | ✅ | 完成 |
| メタデータ自動生成 | ✅ | ✅ | 完成 |
| テーマ切替（5種類） | ✅ | ✅ | 完成 |
| 環境チェック | - | ✅ | 完成 |
| ユーザー導線改善 | - | ✅ | 完成 |

### 関連ドキュメント

- `docs/user_guide_manual_workflow.md` - ユーザー向けガイド
- `docs/spec_csv_input_format.md` - CSV入力仕様
- `docs/spec_transcript_io.md` - Transcript I/O仕様
- `docs/tts_batch_softalk_aquestalk.md` - 音声生成
- `docs/subtitle_hardsub_guide.md` - 字幕ガイド
 - `docs/ymm4_integration_arch.md` - YMM4 連携アーキテクチャ設計（本書）

### 次期フェーズ: API連携

| 優先度 | タスク | 必要な設定 | 状態 |
|--------|--------|-----------|------|
| 高 | A-3 Google Slides API | Cloud Console + OAuth | 準備完了・認証待ち |
| 高 | A-1 NotebookLM/Gemini API | Gemini API Key | 設計済み |
| 中 | YouTube API連携 | OAuth認証 | 準備完了 |
| 低 | C-3-1/C-3-2 YMM4 プラグインAPI（旧: YMM4 REST API） | API仕様確認 | 調査完了・仕様不足のため一旦保留 |

※ 2025-12-11 時点では YMM4 プラグイン API の公開情報が限定的なため、C-3-1/C-3-2 は一旦保留とし、NotebookLM/Gemini/TTS 周辺の API フェーズを優先します。

### 残作業（軽微）

| ID | 内容 | 工数 | 状態 |
|----|------|------|------|
| D-1 | 型ヒント・Docstring 整備 | 継続 | 待機 |
| D-4 | エラーハンドリングの統一 | 2-3時間 | 待機 |
