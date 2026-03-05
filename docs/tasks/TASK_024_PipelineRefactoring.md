# Task: パイプライン大規模リファクタリング
Status: DONE
Tier: 3
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Completed: 2026-03-03T
Report: AI_CONTEXT.md

## Objective
- `src/core/pipeline.py`（1384行）を保守可能な規模に分割する
- `run()` メソッドと `run_csv_timeline()` メソッドの重複コードを統合する
- Stage1/2/3 の責務を明確に分離し、テスタビリティを向上する

## Result Summary

pipeline.py: **1,384行 -> 431行 (-69%)**。目標の500行以下を大幅に達成。

### 抽出されたモジュール (4ファイル、計1,038行)

| モジュール | 行数 | 責務 |
|-----------|------|------|
| `src/core/slide_builder.py` | 247 | スライド展開/分割/構築 (純粋関数6個) |
| `src/core/stage_runners.py` | 325 | Stage1/2/3 実行関数 |
| `src/core/csv_audio_utils.py` | 106 | WAVファイルユーティリティ |
| `src/core/csv_pipeline_runner.py` | 360 | CSVタイムラインパイプライン実行 |

### コミット履歴
- `7324df3` Phase 1+2: slide_builder.py + stage_runners.py 抽出
- `4270da0` Phase 3: csv_audio_utils.py 抽出
- `6e3aee8` Phase 4: csv_pipeline_runner.py 抽出 + ラッパー削除

### pipeline.py に残る責務 (431行)
- `ModularVideoPipeline.__init__` (DI設定、50行)
- `ModularVideoPipeline.run` (メインパイプライン、~250行)
- `ModularVideoPipeline.run_csv_timeline` (csv_pipeline_runner への委譲、~30行)
- retry付きヘルパー4個 (~30行)

## Deliverables

### Layer A（AI完結）

#### A-1: Stage分離モジュール化
- [x] `src/core/stage_runners.py` 作成 - Stage1/2/3 実行関数
  - 当初計画の stages/ ディレクトリ構成ではなく、フラットなモジュール構成を採用
  - run_legacy_stage1, run_legacy_stage1_with_fallback, run_stage2_video_render, run_stage3_upload

#### A-2: run() / run_csv_timeline() の統合
- [x] run_csv_timeline を csv_pipeline_runner.py へ完全抽出
- [x] run() 内の Stage2/3 を sr.run_stage2_video_render / sr.run_stage3_upload に委譲
- [x] 9個の薄いラッパーメソッドを削除

#### A-3: 内部関数のモジュール化
- [x] `_wav_sort_key`, `_find_audio_files` -> `src/core/csv_audio_utils.py`
- [x] `_build_audio_segments`, `_combine_wav_files` -> `src/core/csv_audio_utils.py`
- [x] `_expand_segment_into_slides` 関連 -> `src/core/slide_builder.py`

#### A-4: テスト強化
- [x] 既存テスト群の回帰確認: 146 passed (全Phase完了後)
- [ ] 各抽出モジュールの単体テスト追加 (未実施、別タスクとして推奨)

### Layer B（手動検証）
- [ ] CSVパイプラインのE2E動作確認（TASK_023_E2E で実施予定）

## DoD
- [x] pipeline.py が500行以下に削減 (431行)
- [x] 各Stageモジュールが独立テスト可能 (関数ベースで依存注入済み)
- [x] 既存テスト全パス（146 passed）
- [x] run() と run_csv_timeline() の Stage2/3 コードが共通メソッドを使用

## Constraints
- [x] 外部向けAPI（run, run_csv_timeline の引数/戻り値）は変更しない
- [x] 段階的リファクタリング（4 Phase で実施）
- [x] 機能追加は行わない（純粋リファクタリング）
