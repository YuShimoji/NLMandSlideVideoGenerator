# AI_CONTEXT

## mode
- normal

## report_style
- standard

## 決定事項
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約する（`AUTOHOTKEY_EXE` / `YMM4_EXE` / `FFMPEG_EXE` をサポート）。

## 直近の変更
- `src/core/utils/tool_detection.py`
  - Program Files 配下の候補を環境変数（`ProgramW6432` / `ProgramFiles` / `ProgramFiles(x86)`）から組み立てるように変更。
  - `find_ffmpeg_exe()` を追加。
- `src/core/utils/ffmpeg_utils.py`
  - `find_ffmpeg_exe()` を利用するように統一。
- `src/video_editor/video_composer.py`
  - python-pptx の画像抽出で例外を想定範囲に絞り、`logger.debug` で可視化（挙動はスキップ継続）。
  - MoviePy 合成時のスライド情報読み取り失敗を `logger.debug` で可視化（挙動はフォールバック）。
  - PPTX抽出/動画合成/字幕合成/FFmpegフォールバック/圧縮/サムネイル生成の `except Exception` を想定範囲中心に分割（フォールバック/return/ログ挙動は維持）。
- `src/web/ui/pages.py`
  - 環境チェックの FFmpeg 検出を `detect_ffmpeg()` に統一。
  - ダウンロードボタン用のファイル読込失敗を `logger.debug` で可視化。
  - TTS 実行ファイルの PowerShell 設定例を `$env:ProgramFiles` ベースに変更。
  - UI 内の `except Exception` を想定範囲中心に分割（表示/return/挙動は維持）。
- `src/web/logic/pipeline_manager.py`
  - 進捗DB更新・ジョブ状態取得・キャンセル処理の例外を想定範囲中心に分割（ジョブ状態/return/raise の挙動は維持）。
- `scripts/generate_ymm4_ahk.py`
  - YMM4 実行ファイル未指定時のフォールバックを `%ProgramFiles%` ベースに変更し、ヘルプ表記も更新。
  - slides/timeline JSON 読み込みと AutoHotkey 実行の例外を想定例外中心に分割（挙動は維持）。
- `scripts/e2e_export_test.py`
  - E2E テスト実行の `except Exception` を想定例外中心に分割し、`asyncio.CancelledError` は再送出。
- `scripts/demo_csv_to_video.py`
  - `main()` の `except Exception` を想定例外中心に分割（ログ/return code は維持）。
- `scripts/demo_csv_subtitles.py`
  - `main()` の `except Exception` を想定例外中心に分割（ログ/return code は維持）。
- `templates/scripts/ymm4_export.ahk`
  - `YMM4_EXE`（環境変数）→ `%ProgramFiles%\\YMM4\\YMM4.exe` の順で解決するように変更。
- `src/gapi/google_auth.py`
  - `google-auth` 周りの例外を `ImportError` / `OSError` / `ValueError` 等に分割し、警告ログを改善（挙動は認証スキップ）。
- `src/notebook_lm/gemini_integration.py`
  - Gemini レスポンスの JSON 化失敗を想定例外中心にし、`logger.debug` を追加（挙動は最低限JSONへフォールバック）。
- `src/notebook_lm/transcript_processor.py`
  - 文字起こし処理の例外を `asyncio.CancelledError` / 想定例外 / catch-all に分割（ログ/raise 挙動は維持）。
- `src/server/api.py`
  - 永続化の load/save 周りの例外を想定範囲中心にしつつ、想定外でも警告して継続する catch-all を維持。
  - Spec/接続テスト/パイプライン実行の `except Exception` を想定範囲中心に分割（返却/HTTPException 挙動は維持）。
  - `_to_dict` と CSV inspect API の `except Exception` を想定範囲中心に分割（返却/HTTPException 挙動は維持）。
- `src/notebook_lm/audio_generator.py`
  - 音声ダウンロード/品質検証の例外を想定範囲中心にしつつ、フォールバック生成の挙動を維持。
- `src/notebook_lm/source_collector.py`
  - URL 取得/解析の例外を `requests` 系・解析系に分割し、失敗時は従来通り `None` で継続。
- `src/core/thumbnails/template_generator.py`
  - JSON テンプレート読み込み例外を想定範囲中心にしつつ、想定外でも警告して継続。
- `src/youtube/metadata_generator.py`
  - メタデータテンプレート読み込み例外を想定範囲中心にしつつ、想定外でも警告して継続。
  - メタデータ生成（`generate_metadata`）の `except Exception` を想定範囲中心に分割（ログ/raise は維持）。
- `src/slides/google_slides_client.py`
  - Slides/Drive API クライアント初期化、プレゼン作成、スライド追加、サムネイル取得、PPTX エクスポートの例外を想定範囲中心に分割（戻り値/フォールバック挙動は維持）。
- `src/slides/slide_generator.py`
  - スライド生成/Slides API 呼び出し周りの `except Exception` を想定範囲中心に分割（ログ/raise/フォールバック挙動は維持）。
- `src/video_editor/subtitle_generator.py`
  - 字幕プリセット読み込み/字幕生成の `except Exception` を想定範囲中心に分割（ログ/raise/挙動は維持）。
- `src/server/api_server.py`
  - ヘルスチェック（ファイルシステム/パイプライン）とクリーンアップの `except Exception` を想定範囲中心に分割し、`logger.error` で可視化（返却 dict は維持）。
- `src/video_editor/effect_processor.py`
  - エフェクト処理の `except Exception` を想定範囲中心に分割（ログ/raise の挙動は維持）。
- `src/core/helpers.py`
  - `with_fallback()` の `except Exception` を想定範囲中心に分割（ログ/フォールバック/`PipelineError` の挙動は維持）。
- `src/audio/tts_integration.py`
  - TTS 統合（ElevenLabs/OpenAI/Azure/Google Cloud）の `except Exception` を想定範囲中心に分割（フォールバック/raise の挙動は維持）。
- `src/core/platforms/tiktok_adapter.py`
  - TikTok 投稿の `except Exception` を想定範囲中心に分割（戻り値 dict の挙動は維持）。
- `src/core/editing/export_fallback_manager.py`
  - バックエンド試行ループの `except Exception` を想定範囲中心に分割（リトライ/フォールバック挙動は維持）。
- `src/core/editing/ymm4_backend.py`
  - テンプレ複製/差分適用/AutoHotkey 実行周りの `except Exception` を想定範囲中心に分割（スキップ継続の挙動は維持）。
- `src/main.py`
  - 動画生成パイプライン/CLI 周りの `except Exception` を想定範囲中心に分割（ログ/print/raise 挙動は維持）。
- `src/core/pipeline.py`
  - パイプライン実行/CSVタイムライン内の `except Exception` を想定範囲中心に分割（`PipelineError` 変換/フォールバック挙動は維持）。
- `src/youtube/uploader.py`
  - 各 API 操作の `except Exception` を想定範囲中心に分割（既存ログと raise/return の挙動は維持）。

## テスト
- command: `python -m pytest -q -m "not slow and not integration" --durations=20`
- result: 102 passed, 7 skipped, 4 deselected

## 次の中断可能点
- `docs/Windsurf_AI_Collab_Rules_v1.1.md` と `AI_CONTEXT.md` を作成済み。
- `C:\Program Files` 直書き（YMM4）の主要箇所は環境変数/検出関数ベースへ置換済み。
- `scripts/` 側の broad `except Exception` は generate_ymm4_ahk / e2e_export_test / demo_csv_* まで対応済み。
- `src/` 側の broad `except Exception` は slides/字幕/運用API/動画合成/TTS/周辺（google_slides_client / slide_generator / subtitle_generator / api_server / api / pipeline / web/ui/pages / video_composer / effect_processor / helpers / metadata_generator / uploader / template_generator / tts_integration / tiktok_adapter / export_fallback_manager / ymm4_backend / main）まで対応済み。

## Backlog
- `src/` 内に残っている `except Exception` は特定例外後の catch-all なので、必要に応じてさらに細分化/削除を検討（挙動維持が前提）。
- 生成物/ビルド成果物（例: `ymm4-plugin/obj`）が意図せず管理対象になっていないか確認。
