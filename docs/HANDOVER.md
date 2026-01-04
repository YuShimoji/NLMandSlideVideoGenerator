# 作業申し送り (HANDOVER)

## GitHubAutoApprove
true

## プロジェクト概要
NLMandSlideVideoGenerator - NotebookLMとスライドから動画を生成するシステム

## 主要な決定事項
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約する（`AUTOHOTKEY_EXE` / `YMM4_EXE` / `FFMPEG_EXE` をサポート）。

## 現在のシステムの「実動作」期待

### 主フロー（現行 SSOT: CSV + WAV）

入力:
- CSV（話者名 + テキスト）
- 音声ディレクトリ（`001.wav`, `002.wav` ...）

期待される出力:
- `data/videos/` に mp4
- `data/transcripts/` に SRT/VTT/ASS
- オプションで `data/ymm4/` に YMM4 プロジェクト出力（テンプレ差分適用＋補助JSON）
- サムネイル/メタデータも「APIなし」で生成可能（テンプレ/ルールベース）

実行手段:
- CLI: `scripts/run_csv_pipeline.py`
- Web UI: `src/web/web_app.py`（Streamlit）→ 「CSV Pipeline」ページ

SSOT:
- `docs/user_guide_manual_workflow.md`
- `docs/spec_csv_input_format.md`

## テスト
- command: `python -m pytest -q -m "not slow and not integration" --durations=20`
- result: 102 passed, 7 skipped, 4 deselected

## 作業再開のためのチェックリスト
- `docs/INDEX.md` を起点に必要ドキュメントへ到達できる
- スモークテスト: `python -m pytest -q -m "not slow and not integration" --durations=20`
- 動作確認（最短）:
  - `python scripts/generate_sample_audio.py`
  - `python scripts/run_csv_pipeline.py --csv samples/basic_dialogue/timeline.csv --audio-dir samples/basic_dialogue/audio --topic "sample"`

## Git / 反映
- ブランチ: `master`（origin/master がデフォルト）
- 反映手順:
  - commit → `git push origin master`
  - push 後に `git status` が clean であることを確認
  - `git log -1` と `git ls-remote origin master` の SHA が一致することを確認

## 詳細な履歴
過去の詳細な作業履歴は `docs/HANDOVER_20251214.md` を参照してください。
