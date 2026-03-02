# REPORT: TASK_016 Web資料収集とNLM台本調整ワークフロー設計

Ticket: docs/tasks/TASK_016_SourceResearchAndScriptAlignment.md
Timestamp: 2026-02-28T20:13:40+09:00
Status: DONE
Completed: 2026-02-28T20:13:40+09:00
Actor: Codex (Orchestrator)
Type: TaskReport
Duration: 2026-02-28T16:05:00+09:00 to 2026-02-28T20:13:40+09:00
Changes: 研究WF設計、差分分析実装、Streamlit UI、Playwright 自動確認
MCP_CONNECTIVITY: AVAILABLE
Verification Mode: AUTO_VERIFIED
Pending Items: なし

## 概要

Phase 1 / Phase 2 に続いて、Phase 3 Layer A / Layer B の自動確認まで完了した。
Streamlit UI は Playwright スモークで `package.json` 読み込みから最終CSV出力まで自動確認済み。

## 現状

- 自動確認済み:
  - `export_to_csv`
  - Streamlit の `show_research_page`
  - サイドバー登録
  - 契約テストと import 確認
  - `package.json` / script 読み込み
  - orphaned/conflict を含むレビュー画面表示
  - CSV 出力導線
  - Playwright によるブラウザスモーク

## Summary

Web資料収集 + NLMたたき台台本調整ワークフローについて、Phase 1 / Phase 2 に続いて Phase 3 の UI 実装と Layer B 自動確認まで完了した。

- Phase 1: `ResearchPackage`, `AlignmentReport` のデータモデル定義
- Phase 1: Google Custom Search API を用いた実検索の統合
- Phase 1: CLI リサーチコマンド (`scripts/research_cli.py`) の作成
- Phase 1: `data/research/` への永続化機能の追加
- Phase 2: claims抽出、差分分析、AlignmentReport 生成ロジックの実装
- Phase 2: `research_cli.py align` による差分分析レポート保存
- Phase 3 Layer A: Streamlit UI の「リサーチ・台本照合」ページ追加
- Phase 3 Layer A: `export_to_csv` 実装と最終CSV出力導線追加
- Phase 3 Layer B: Playwright で Streamlit UI を起動し、fixture 入力から CSV 出力まで自動確認
- `scripts/smoke_research_ui_playwright.py` によるローカル再実行スモークを追加

## DoD 照合

| DoD 項目 | 状態 | 証跡 |
|----------|------|------|
| 資料収集ワークフローのステップ定義がある | PASS | `docs/research_workflow_design.md` Step 1-3 |
| 収集結果の保存スキーマがある | PASS | ResearchPackage JSON スキーマ定義済み |
| NLMたたき台との比較/修正フローが定義されている | PASS | Step 4-6 + AlignmentReport スキーマ |
| 手動レビュー点が明示されている | PASS | Step 1, Step 6 に明記 |
| 次実装フェーズに切れる単位へ分解されている | PASS | Phase 1-4 のタスク分解 |
| claims抽出と差分分析が実装されている | PASS | `src/notebook_lm/script_alignment.py` |
| AlignmentReport が保存される | PASS | `scripts/research_cli.py align` + `data/research/rp_20260228_181722/alignment_report.json` |
| Phase 3 のレビューUIが追加されている | PASS | `src/web/ui/pages.py::show_research_page`, `src/web/web_app.py` |
| 最終CSV出力ロジックがある | PASS | `ScriptAlignmentAnalyzer.export_to_csv`, `tests/test_alignment_export.py` |
| UI実操作相当が確認されている | PASS | `tests/test_research_ui_playwright.py`, `scripts/smoke_research_ui_playwright.py` |

## 成果物

### 新規作成

- `docs/research_workflow_design.md` — ワークフロー設計メモ（全体）
- `src/notebook_lm/script_alignment.py` — claims抽出と差分分析ロジック
- `tests/test_script_alignment.py` — 差分分析の契約テスト
- `tests/test_research_cli_alignment.py` — CLI 保存の契約テスト
- `tests/test_alignment_export.py` — CSV 出力の契約テスト
- `tests/test_research_ui_playwright.py` — Research UI の Playwright スモーク
- `tests/fixtures/research/sample_package.json` — UI 自動確認用 fixture
- `tests/fixtures/research/sample_script.csv` — UI 自動確認用 fixture
- `scripts/smoke_research_ui_playwright.py` — ローカル再実行用スモーク

### 設計内容

#### 7ステップフロー

1. トピック定義 + 検索条件設定
2. Web資料収集（SourceCollector 拡張）
3. 収集結果の保存 + スコアリング
4. NLMたたき台スクリプト入力
5. 台本 ← → 資料 の差分分析
6. 人手レビュー + 採否判断
7. 確定台本 → CSV 出力

#### 入出力スキーマ

- 検索条件入力 JSON
- ResearchPackage JSON（資料パッケージ）
- 正規化スクリプト JSON（NLMたたき台 → 内部形式）
- AlignmentReport JSON（差分分析結果）
- 確定 CSV（既存パイプラインへの入力）

#### 差分分析ルール

- supported / orphaned / missing / conflict の4分類
- Phase 1 はキーワード一致 + Gemini 要約比較
- Phase 2 は埋め込みベクトルベース（将来）

#### 責務分離

- 資料収集パイプライン: 根拠と整合性
- 台本調整パイプライン: 主張の検証 + 修正
- 動画生成パイプライン: 見た目と出力安定性

#### 既存コードとの接続

- `SourceCollector`, `SourceInfo` を拡張（破壊的変更なし）
- `GeminiIntegration` に差分分析メソッドを追加
- `IScriptProvider`, `IContentAdapter` は変更なし

#### 次フェーズ分解

- Phase 1: 基盤（データモデル、検索API、CLI）
- Phase 2: 差分分析（claims抽出、AlignmentReport生成）
- Phase 3: レビューUI（CLI + Web）
- Phase 4: 統合テスト

## Verification

- `PYTHONPATH=.;src python -m pytest -q tests/test_script_alignment.py tests/test_research_cli_alignment.py tests/test_research_models.py tests/test_source_collector_search.py --tb=short`
  - 結果: `9 passed`
- `PYTHONPATH=.;src python scripts/research_cli.py align --package data/research/rp_20260228_181722/package.json --script samples/basic_dialogue/timeline.csv`
  - 結果: `data/research/rp_20260228_181722/alignment_report.json` を生成
- `PYTHONPATH=.;src python -m pytest -q tests/test_research_ui_playwright.py tests/test_alignment_export.py tests/test_script_alignment.py --tb=short`
  - 結果: `6 passed`
- `PYTHONPATH=.;src python -c "import src.web.web_app; import src.web.ui.pages; print('IMPORT_OK')"`
  - 結果: `IMPORT_OK`
- `PYTHONPATH=.;src python scripts/smoke_research_ui_playwright.py`
  - 結果: `SMOKE_OK output_csv/final_script_rp_playwright_smoke.csv`

## Remaining Scope

- Follow-on: Phase 4 相当の実トピック end-to-end 統合確認
- Follow-on: review decisions の永続化や CI 組み込み

## Reference Runbook

| 項目 | 手順 | 完了条件 |
|---|---|---|
| Streamlit 起動 | `python -m streamlit run src/web/web_app.py` | ダッシュボードが開く |
| Research Page 遷移 | サイドバーで `🔍 リサーチ・台本照合` を選ぶ | 画面が表示される |
| 入力確認 | `package.json` と台本ファイルを読み込む | Summary metrics と照合リストが出る |
| 採否操作 | orphaned / conflict に `採用` / `拒否` を設定する | `analysis_results` が更新される |
| CSV出力 | `🚀 最終CSVを出力` を押す | CSV ダウンロードまたは保存ができる |

## 次のアクション

1. `TASK_015` として Playwright スモークを CI に組み込む
2. 実トピックでの end-to-end 統合確認は follow-on として別管理する
3. review decisions の永続化は follow-on 候補として別チケットで扱う

## Risk

- 実トピックでの根拠品質と引用妥当性は、汎用 fixture だけでは完全に担保できない

## Proposals

- `review_decisions.json` を保存し、AlignmentReport から最終CSVまでの判断履歴を監査可能にする
