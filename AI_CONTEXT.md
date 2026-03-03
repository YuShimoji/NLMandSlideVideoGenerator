# AI Context

## 基本情報

- **最終更新**: 2026-03-03T22:00:00+09:00
- **更新者**: AI Worker (Opus 4.6)

## レポート設定（推奨）

- **report_style**: standard
- **mode**: normal

## 現在のミッション

- **タイトル**: プロジェクト整備完了 - E2E制作フェーズ準備
- **Issue**: shared-workflows脱却、コードベース整理、テスト安定化
- **ブランチ**: master
- **進捗**: リポジトリクリーンアップ完了。再開発可能状態。

## 決定事項

- shared-workflows サブモジュールを削除。オーケストレーションは CLAUDE.md + Serena メモリに移行。
- 表示ルールの外部SSOTは廃止。プロジェクト内ドキュメント（AI_CONTEXT.md, CLAUDE.md）を参照先とする。
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約。
- 品質SSOTは 480p/720p/1080p に統一（4K未対応）。
- CSV + 行ごとのWAV → CSVパイプラインで動画/字幕/サムネ/メタデータ生成が現行SSOT。
- ドメイン固有例外階層を `src/core/exceptions.py` に確立。
- pytest.ini に `pythonpath = . src` を設定し、テストの import 安定化。

## リスク/懸念

- YMM4本体のDLLがローカル環境で見つからないため、C#プロジェクトのビルドが制限されている。
- VOICEVOX実機検証（Layer B）は VOICEVOX Engine 起動が前提。
- CIパイプラインの GitHub Actions 有効化が未完。
- pipeline.py (1384行) の技術的負債。TASK_024 で対応予定。

## テスト

- **command**: `venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short`
- **result**: 138 passed, 7 skipped, 5 deselected (2026-03-03 22:00)

## タスク管理（短期/中期/長期）

| 尺度 | タスクID | 概要 | ステータス | 優先度 |
| :--- | :--- | :--- | :--- | :--- |
| **短期** | TASK_022-B | VOICEVOX実機検証 | 待機 | 高 |
| **短期** | TASK_015-B | CI/CD本番有効化 (GitHub Actions) | IN_PROGRESS | 高 |
| **短期** | SW-CLEANUP | shared-workflows参照除去 | 完了 | 中 |
| **中期** | TASK_024 | パイプラインリファクタリング (pipeline.py分割) | OPEN | 中 |
| **中期** | E2E-PROD | 実トピックE2E制作完走 | 構想 | 高 |
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
- [ ] VOICEVOX Engine実機検証
- [ ] GitHub Actions CI有効化確認
- [ ] Codecov統合
- [ ] pipeline.py 500行以下への分割

## 備考（自由記述）

- Python 3.11.0 / venv 環境を使用。
- テスト: 138 passed, 7 skipped (12.8秒)
- プロジェクト健全性: リポジトリクリーン、CI定義健全、テスト安定

## 履歴

- 2026-02-24: TASK_007 シナリオB完了、実機検証成功。
- 2026-03-02 午前: リモート同期、プロジェクト現状評価。
- 2026-03-02 夜: 総合監査、TASK_021-025起票。
- 2026-03-03 深夜: TASK_021/022/023 Layer A完了。
- 2026-03-03 夜: shared-workflows脱却、リポジトリクリーンアップ、テスト安定化。
