# 作業申し送り (HANDOVER)

## 最終更新
2026-02-06T13:30:00+09:00

## 運用フラグ
- **GitHubAutoApprove**: true
- **shared-workflows**: v3.0（コミット 4ad0a0a）
- **IDE**: Windsurf / Antigravity（Mermaid対応）

## プロジェクト概要
NLMandSlideVideoGenerator - NotebookLMとスライドから動画を生成するシステム

## 主要な決定事項
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約（`AUTOHOTKEY_EXE` / `YMM4_EXE` / `FFMPEG_EXE`）
- 品質SSOTは 480p/720p/1080p に統一（4K未対応）
- shared-workflows v3 採用。ORCHESTRATOR_DRIVER.txt を毎回のエントリポイントとする
- 表示ルールは `.shared-workflows/data/presentation.json` v3 を SSOT とする

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
- command: `.\venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short`
- result: 109 passed, 7 skipped, 4 deselected (2026-02-06)

## タスクポートフォリオ
- **DONE**: TASK_001, TASK_002, TASK_003, TASK_004, TASK_005, TASK_006
- **COMPLETED**: TASK_009
- **CLOSED**: TASK_008
- **IN_PROGRESS**: TASK_007（YMM4プラグイン統合、シナリオZero+A完了、シナリオB待ち）

## 作業再開のためのチェックリスト
1. `node .shared-workflows/scripts/sw-update-check.js` でサブモジュール最新確認
2. `node .shared-workflows/scripts/sw-doctor.js --profile shared-orch-bootstrap --format text` で環境診断
3. スモークテスト: `.\venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short`
4. `.shared-workflows/docs/windsurf_workflow/OPEN_HERE.md` を起点に運用開始
5. 動作確認（最短）:
   - `.\venv\Scripts\python.exe scripts/generate_sample_audio.py`
   - `.\venv\Scripts\python.exe scripts/run_csv_pipeline.py --csv samples/basic_dialogue/timeline.csv --audio-dir samples/basic_dialogue/audio --topic "sample"`

## IDE設定ファイル
- `.cursorrules`: v3 グローバルルール
- `.windsurf/workflows/`: Windsurf用ワークフロー定義（5ファイル）
- `.cursor/MISSION_LOG.md`: 現在のミッション状態
- `AI_CONTEXT.md`: プロジェクトAIコンテキスト（v3フォーマット）

## Git / 反映
- ブランチ: `master`（origin/master がデフォルト）
- 反映手順:
  - commit → `git push origin master`
  - push 後に `git status -sb` が clean であることを確認
  - `git log -1` と `git ls-remote origin master` の SHA が一致することを確認

## 詳細な履歴
過去の詳細な作業履歴は `docs/archive/HANDOVER_20251214.md` 等を参照してください。
