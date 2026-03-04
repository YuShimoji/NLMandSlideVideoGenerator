# AI Context

## 基本情報

- **最終更新**: 2026-03-04T12:00:00+09:00
- **更新者**: Claude Sonnet 4.5

## レポート設定（推奨）

- **report_style**: standard
- **mode**: normal

## 現在のミッション

- **タイトル**: コードベース刷新 - YMM4に注力
- **Issue**: VOICEVOX/SofTalk削除、テスト削減、YMM4ワークフロー明確化
- **ブランチ**: master
- **進捗**: 迷走期の混入仕様を削除し、YMM4中心の制作フローに集約。テスト110合格。

## 決定事項

- shared-workflows サブモジュールを削除。オーケストレーションは CLAUDE.md + Serena メモリに移行。
- 表示ルールの外部SSOTは廃止。プロジェクト内ドキュメント（AI_CONTEXT.md, CLAUDE.md）を参照先とする。
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約。
- 品質SSOTは 480p/720p/1080p に統一（4K未対応）。
- CSV + 行ごとのWAV → CSVパイプラインで動画/字幕/サムネ/メタデータ生成が現行SSOT。
- 音声方針: YMM4内蔵ゆっくりボイス（唯一の推奨方法）。VOICEVOX/SofTalk/AquesTalkは削除済み。
- ドメイン固有例外階層を `src/core/exceptions.py` に確立。
- pytest.ini に `pythonpath = . src` を設定し、テストの import 安定化。

## リスク/懸念

- YMM4本体のDLLがローカル環境で見つからないため、C#プロジェクトのビルドが制限されている。
- CIパイプラインの GitHub Actions 有効化が未完。
- Web UI (pages.py 1618行) に残存するSofTalk/AquesTalk参照の整理が必要。

## テスト

- **command**: `venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short`
- **result**: 110 passed, 8 skipped, 4 deselected (11.5秒) (2026-03-04 12:00)

## タスク管理（短期/中期/長期）

| 尺度 | タスクID | 概要 | ステータス | 優先度 |
| :--- | :--- | :--- | :--- | :--- |
| **短期** | WEBUI-CLEANUP | WebUIのSofTalk/AquesTalk参照削除 | 保留 | 低 |
| **短期** | DOC-REFRESH | ドキュメント刷新（YMM4中心） | 進行中 | 中 |
| **短期** | TASK_023-B | GitHub Actions完全有効化 | 待機 | 高 |
| **中期** | E2E-PROD | 実トピックE2E制作完走（YMM4のみ） | 構想 | 高 |
| **中期** | DESKTOP-QA | Electronアプリ品質向上 | 構想 | 中 |
| **長期** | TASK_025 | クラウドレンダリング対応 | BACKLOG | 低 |
| **長期** | MULTI-LANG | 多言語台本自動照合強化 | 構想 | 低 |
| **長期** | MONETIZE | YouTube自動公開パイプライン | 構想 | 低 |

## Backlog

- [x] shared-workflows サブモジュール削除 (2026-03-03)
- [x] .gitignore UTF-16LE文字化け修正 (2026-03-03)
- [x] ルート散在.pyファイル整理 (22 -> 5) (2026-03-03)
- [x] CI yml shared-workflows参照除去 (2026-03-03)
- [x] .windsurf/workflows 削除 (2026-03-03)
- [x] pytest.ini pythonpath設定追加 (2026-03-03)
- [x] pipeline.py 500行以下への分割 (2026-03-04: 1384行→431行)
- [x] VOICEVOX/SofTalk/AquesTalk削除 (2026-03-04)
- [ ] GitHub Actions CI有効化確認
- [ ] Codecov統合

## 備考（自由記述）

- Python 3.11.0 / venv 環境を使用。
- テスト: 110 passed, 8 skipped (11.5秒、36テスト削減）
- プロジェクト健全性: YMM4中心に刷新、コードベース簡素化完了

## 履歴

- 2026-02-24: TASK_007 シナリオB完了、実機検証成功。
- 2026-03-02 午前: リモート同期、プロジェクト現状評価。
- 2026-03-02 夜: 総合監査、TASK_021-025起票。
- 2026-03-03 深夜: TASK_021/022/023 Layer A完了。TASK_024 Pipeline Refactoring完了（1384→431行）。
- 2026-03-03 夜: shared-workflows脱却、リポジトリクリーンアップ、テスト安定化。
- 2026-03-04 昼: 迷走期仕様削除 — VOICEVOX/SofTalk/AquesTalkを完全削除。YMM4のみに注力。テスト110合格（36テスト削減）。
