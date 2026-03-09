# ワークフロー責務境界（運用メモ）

最終更新: 2026-03-09

## 目的

Web UI経由運用とCLI補助スクリプトの責務を分離し、仕様逸脱を防ぐ。

## 境界定義

### 1. Web UI（本線）

対象: `src/web/`（CSV Pipelineページ）

責務:
- 現行運用の実行入口
- CSV入力と関連素材の受け付け
- YMM4投入向け成果物の生成

非責務:
- YMM4本体のGUI操作の完全自動化保証
- 旧Path B互換のCLIエントリ提供

### 2. Pythonコア（前工程）

対象: `src/core/`, `src/notebook_lm/`

責務:
- リサーチ、台本整形、入力検証
- パイプラインの整合性維持

非責務:
- 最終動画レンダリング（現行はYMM4担当）
- 音声合成（現行はYMM4担当）

### 3. CLI補助スクリプト（支線）

対象: `scripts/*.py`

責務:
- 検証・可視化・補助作業
- 例: `inspect_csv_timeline.py` によるCSV/音声整合チェック（外部音源準備を前提とした旧運用検証）

非責務:
- 本番の単一入口化
- 旧Path Bの代替導線化

## 運用ルール

1. 新しい実行手順は、まず Web UI 導線で定義する。
2. CLIを追加する場合は「補助用途」であることを明記する。
3. 文書に実行コマンドを追記する際は、実在確認を行う。
4. 削除済み導線（`run_csv_pipeline.py` 等）は archive を除き参照しない。

## 参照

- `docs/PROJECT_ALIGNMENT_SSOT.md`
- `docs/ymm4_final_workflow.md`
- `docs/ymm4_export_spec.md`
- `docs/ymm4_integration_arch.md`