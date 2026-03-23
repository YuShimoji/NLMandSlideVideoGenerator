# Core Developer (本セッション) 担当領域

## 役割
変換層 (Python + Gemini) のパイプライン信頼性と統合を担当する。
「初回1本通し実行」を閉じるために必要なコア実装とバグ修正が主軸。

## 担当する仕様

### 最優先: SP-053 Producer GUI Phase 2
- ProductionLine 状態遷移の GUI 操作
- Streamlit 制作ボード拡張 (src/web/ui/pages/production_board.py)
- Phase 0-7 のステータス表示・遷移・リジューム

### 高優先: SP-050 E2Eワークフロー実装ギャップ
- Phase 0-7 の通し実行で発見されるバグ修正
- stage_runners.py / csv_assembler.py / export_validator.py の実運用対応
- パイプライン状態永続化 (pipeline_state.py) の信頼性

### 高優先: Gemini構造化の精度改善
- gemini_provider.py のプロンプト精度向上
- NotebookLMテキスト → CSV構造化の変換精度
- セグメント粒度制御 (segment_duration_validator.py)

### 中優先: パイプライン統合
- production_line.py と pipeline.py の接続
- バッチ処理 (SP-040) の日常運用対応
- エラーハンドリングとリジューム機能

## 担当しない領域 (Worker に委譲)

| 領域 | Worker | 理由 |
|------|--------|------|
| YMM4 Plugin (.NET/C#) | Worker A | 言語・ツールチェーンが異なる |
| YMM4テンプレート設計 | Worker A | デザイン作業 (HUMAN_AUTHORITY) |
| YouTube OAuth取得 | Worker B | 外部サービス設定 (手動作業) |
| InoReader API疎通 | Worker C | 外部サービス認証 (手動作業) |
| Playwright NLM自動化 | Worker D | ブラウザ自動化の専門性 |
| Google Slides API | Worker E | 新規API統合 (独立性高) |

## 主要ファイル

### パイプラインコア
- src/core/pipeline.py -- DI統合パイプライン
- src/core/stage_runners.py -- 4ステージ実行
- src/core/csv_assembler.py -- CSV組立
- src/core/export_validator.py -- Pre-Export検証
- src/core/production_line.py -- 制作ライン状態管理
- src/core/pipeline_state.py -- ステージリジューム
- src/core/pipeline_stats.py -- 実行統計

### Gemini構造化
- src/core/providers/script/gemini_provider.py -- Gemini台本構造化
- src/notebook_lm/gemini_integration.py -- Gemini統合 (役割変更中)
- config/script_presets/*.json -- スタイルプリセット

### UI
- src/web/ui/pages/production_board.py -- 制作ボード
- src/web/ui/pages/pipeline.py -- パイプライン実行
- src/web/pipeline_manager.py -- 実行制御

### テスト
- tests/test_pipeline.py
- tests/test_stage_runners.py
- tests/test_csv_assembler.py
- tests/test_production_line.py
- tests/test_e2e_dry_run.py

## 作業方針
1. SP-053 Phase 2 で制作ボードを実用レベルに引き上げる
2. dry-run (scripts/e2e_dry_run.py) を実行し、パイプラインの実動作を確認
3. 発見されたバグを修正
4. Gemini構造化プロンプトの改善
5. Worker 成果物の統合・レビュー
