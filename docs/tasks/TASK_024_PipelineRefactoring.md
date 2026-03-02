# Task: パイプライン大規模リファクタリング
Status: OPEN
Tier: 3
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Report: (未作成)

## Objective
- `src/core/pipeline.py`（1384行）を保守可能な規模に分割する
- `run()` メソッド（~300行）と `run_csv_timeline()` メソッド（~400行）の重複コードを統合する
- Stage1/2/3 の責務を明確に分離し、テスタビリティを向上する

## Context
- 2026-03-02 監査で `pipeline.py` が最大の技術的負債として特定
- `run()` と `run_csv_timeline()` で Stage2（動画レンダリング）と Stage3（アップロード）のロジックが重複
- `_run_stage2_video_render()` と `_run_stage3_upload()` ヘルパーが既に存在するが、`run()` / `run_csv_timeline()` 本体では未使用
- 内部関数（_build_audio_segments, _combine_wav_files 等）がクロージャとして定義されており、テスト困難

## Deliverables

### Layer A（AI完結）

#### A-1: Stage分離モジュール化
- [ ] `src/core/stages/stage1_script.py` 作成 - Script + Voice パイプライン
- [ ] `src/core/stages/stage2_render.py` 作成 - Timeline + Video レンダリング
- [ ] `src/core/stages/stage3_publish.py` 作成 - Upload + Publishing
- [ ] `src/core/stages/__init__.py` 作成

#### A-2: run() / run_csv_timeline() の統合
- [ ] 共通フローを `_execute_pipeline()` に抽出
- [ ] CSV固有ロジック（WAV検索、結合、TranscriptInfo構築）を `_prepare_csv_inputs()` に分離
- [ ] `run()` と `run_csv_timeline()` は薄いラッパーに変更

#### A-3: 内部関数のモジュール化
- [ ] `_wav_sort_key`, `_find_audio_files` → `src/core/utils/audio_utils.py`
- [ ] `_build_audio_segments`, `_combine_wav_files` → `src/core/utils/audio_utils.py`
- [ ] `_expand_segment_into_slides` 関連 → `src/core/utils/slide_utils.py`

#### A-4: テスト強化
- [ ] 各Stageモジュールの単体テスト追加
- [ ] audio_utils のユニットテスト追加
- [ ] 既存テスト群の回帰確認

### Layer B（手動検証）
- [ ] CSVパイプラインのE2E動作確認（サンプルデータ使用）

## DoD (Definition of Done)
- [ ] pipeline.py が500行以下に削減
- [ ] 各Stageモジュールが独立テスト可能
- [ ] 既存テスト全パス（103+ passed）
- [ ] run() と run_csv_timeline() の Stage2/3 コードが共通メソッドを使用

## Constraints
- 外部向けAPI（run, run_csv_timeline の引数/戻り値）は変更しない
- 段階的リファクタリング（1 Stage ずつ分離）
- 機能追加は行わない（純粋リファクタリング）

## Dependencies
- TASK_021（コード品質ハードニング）完了推奨
- 既存テストが安定していること

## Risk
- リファクタリングによる回帰バグ: 段階的実施 + テスト駆動で軽減
- インポートパスの変更: 既存利用箇所の一括更新が必要

## Estimated Effort
- Layer A: 10-15時間
- Layer B: 1時間
