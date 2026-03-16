# AI Context

## 基本情報

- **最終更新**: 2026-03-16
- **更新者**: Claude Opus 4.6

## レポート設定（推奨）

- **report_style**: standard
- **mode**: normal

## 現在のミッション

- **タイトル**: 中期ロードマップ — 実運用品質 + ドキュメント仕上げ
- **Issue**: 全SP完了後、YMM4実機テスト・Gemini実コンテンツ確認・テストカバレッジ拡充
- **ブランチ**: master
- **進捗**: 全33仕様 (SP-001〜SP-033) + SP-034 完了。E2Eパイプライン全6ステップ完走確認済み。4層フォールバック素材パイプライン、Geminiフォールバックチェーン稼働中。

## 決定事項

- shared-workflows サブモジュールを削除。オーケストレーションは CLAUDE.md + Serena メモリに移行。
- 表示ルールの外部SSOTは廃止。プロジェクト内ドキュメント（AI_CONTEXT.md, CLAUDE.md）を参照先とする。
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約。
- 品質SSOTは 480p/720p/1080p に統一（4K未対応）。
- CSV → YMM4 で音声生成・動画レンダリング (Path A) が現行SSOT。Path B (MoviePy) は完全削除済み。
- 音声方針: YMM4内蔵ゆっくりボイス（唯一の推奨方法）。外部TTS連携コードは全削除済み。
- ドメイン固有例外階層を `src/core/exceptions.py` に確立。
- pytest.ini に `pythonpath = . src` を設定し、テストの import 安定化。
- Ruff import sorting (I001) は無効化 - circular imports を引き起こすため。
- `api_spec_design.py` は設計ファイルとしてmypy除外（mypy.ini設定）。
- Settings クラスに Dict[str, Any] 型アノテーション追加（mypy対応）。
- CI Stage 5 (YMM4) は YMM4未インストール環境でスキップ可能に変更。
- Gemini API統合完了 (CsvScriptCompletionPlugin) - YMM4非依存、無料枠あり。
- .NET Core分離完了 (NLMSlidePlugin.Core.csproj) - CIでYMM4非依存テスト可能化。
- CIワークフロー11→6整理完了 - task-validation, documentation, openspec×3削除。
- OpenSpecフレームワーク削除完了 - spec 0件ロード、import broken、ci-mainと重複のため。
- Geminiモデルフォールバックチェーン: gemini-2.5-flash → gemini-2.0-flash → モック。
- 素材パイプライン4層フォールバック: Pexels/Pixabay → Gemini Imagen → TextSlideGenerator → none。

## 品質指標（2026-03-16）

| 指標 | 値 | 備考 |
| :--- | :--- | :--- |
| Ruff errors | **0** | 79 source files checked |
| Mypy errors | **0** | 79 source files checked |
| Python Tests | **328 passed, 1 skipped** | playwright未インストールのみskip |
| .NET Build | **0 warnings, 0 errors** | CS1998警告解消 |
| .NET Tests | **34 passed** | Core分離後も全通過 |
| CI workflows | **6/6 green** | ローカルCI全緑 |
| Health Score | **98/100 (A+)** | 残: テストカバレッジ拡充のみ |

## リスク/懸念

- テストカバレッジ: 未テスト23モジュール (57%) - 80%+目標
- GitHub Actions CI Layer B: 手動検証待ち（ローカルCIは全緑）
- YMM4本体のDLLがローカル環境で見つからないため、C#プロジェクトのビルドが制限されている
- pip: google-auth-oauthlib互換性警告あり (google-auth 2.49.1 vs oauthlib要求 <2.42.0、機能影響なし)

## テスト

- **command**: `.\venv\Scripts\python.exe -m pytest tests\ -q -m "not slow and not integration" --tb=short --ignore=tests/test_alignment_export.py`
- **result**: 328 passed, 1 skipped (2026-03-16)
- **.NET Core**: `dotnet test ymm4-plugin/tests/NLMSlidePlugin.Tests.csproj -c Release --nologo -q` → 34 passed
- **CI**: `.\scripts\ci.ps1` (5 stages, all green)

## CI パイプライン構成

```
Stage 1: Python Unit Tests (pytest -q -m "not slow and not integration")
Stage 2: Type Check (mypy src/ --ignore-missing-imports)
Stage 3: Lint Check (ruff check src/)
Stage 4: Task Report Consistency (node scripts/check_task_reports.js)
Stage 5: YMM4 Plugin Consistency (optional, skips if YMM4 not installed)
```

## タスク管理（短期/中期/長期）

| 尺度 | タスクID | 概要 | ステータス | 優先度 |
| :--- | :--- | :--- | :--- | :--- |
| **短期** | TEST-COVERAGE | 未テスト23モジュールのテスト追加 | 構想 | 高 |
| **短期** | YMM4-REAL | YMM4実機テスト (BGM+画像+字幕統合) | 待機 | 高 |
| **短期** | GEMINI-QUAL | Geminiクォータリセット後の品質確認 | 待機 | 高 |
| **中期** | DOC-FINISH | SP-006 (90%), SP-007 (85%) 仕上げ | 構想 | 中 |
| **中期** | GEMINI-PAID | Gemini有料プラン検討 | 構想 | 中 |
| **長期** | DOCKER-CI | Docker化 / CI-CD強化 | BACKLOG | 低 |
| **長期** | MULTI-LANG | 多言語台本自動照合強化 | 構想 | 低 |
| **長期** | MONETIZE | YouTube自動公開パイプライン | 構想 | 低 |

## Production Path

```text
CSV(話者,テキスト,画像パス,アニメ) → YMM4 (NLMSlidePlugin CSVインポート) → 音声生成(台本機能) → 動画出力 → mp4
```

## 未テストモジュール一覧（23件）

### Core Infrastructure
- `src/core/exceptions.py`, `src/core/helpers.py`, `src/core/slide_builder.py`
- `src/core/stage_runners.py`, `src/core/utils/decorators.py`
- `src/core/utils/ffmpeg_utils.py`, `src/core/utils/logger.py`, `src/core/utils/tool_detection.py`

### Data & External Services
- `src/gapi/google_auth.py`, `src/notebook_lm/gemini_integration.py`
- `src/notebook_lm/transcript_processor.py`, `src/server/api.py`, `src/server/api_server.py`

### Presentation & Video
- `src/slides/content_splitter.py`, `src/slides/google_slides_client.py`
- `src/youtube/metadata_generator.py`, `src/youtube/uploader.py`

### Web UI
- `src/web/logic/test_manager.py`, `src/web/ui/pages/_utils.py`
- `src/web/ui/pages/asset_management.py`, `src/web/ui/pages/documentation.py`
- `src/web/ui/pages/home.py`, `src/web/ui/pages/settings.py`

## Backlog

- [x] shared-workflows サブモジュール削除 (2026-03-03)
- [x] .gitignore UTF-16LE文字化け修正 (2026-03-03)
- [x] ルート散在.pyファイル整理 (22 -> 5) (2026-03-03)
- [x] CI yml shared-workflows参照除去 (2026-03-03)
- [x] .windsurf/workflows 削除 (2026-03-03)
- [x] pytest.ini pythonpath設定追加 (2026-03-03)
- [x] pipeline.py 500行以下への分割 (2026-03-04: 1384行→431行)
- [x] 外部TTS連携コード全削除 (2026-03-04)
- [x] Web UI modular化 (2026-03-05: pages.py→pages/ 8ファイル)
- [x] .NET CI分離 (2026-03-05)
- [x] Ruff統合 (2026-03-05: 995→0 errors)
- [x] Mypy全修正 (2026-03-05: 228→0 errors, 76 files)
- [x] CI 5段階全緑化 (2026-03-05)
- [x] Gemini API統合 (2026-03-07: CsvScriptCompletionPlugin)
- [x] .NET Core分離 (2026-03-07: NLMSlidePlugin.Core.csproj)
- [x] CIワークフロー整理 (2026-03-07: 11→6、deprecated actions全修正)
- [x] OpenSpec削除 (2026-03-07: spec 0件、broken imports)
- [x] Path B完全削除 (2026-03-08: MoviePy backend + TTS統合 + video_composer等6ファイル削除)
- [x] SP-024 Voice自動生成UI (2026-03-09)
- [x] SP-026 ImageItem自動配置 (2026-03-14)
- [x] SP-031 全完了 — style_template.json v1.1 + BGMテンプレート (2026-03-17)
- [x] SP-032 CsvAssembler + YMM4 backend統合 (2026-03-14)
- [x] SP-033 全Phase完了 — アニメ7種+StockImage+AIImage+TextSlide (2026-03-17)
- [x] SP-034 パイプライン再開機能 (2026-03-17)
- [x] Ruff/Mypy regression修正 (2026-03-16: ruff 12→0, mypy 36→0)
- [ ] テストカバレッジ拡充 (57% → 80%+)
- [ ] GitHub Actions CI有効化確認 (Layer B)
- [ ] Codecov統合

## 備考（自由記述）

- Python 3.11.0 / venv 環境を使用。
- テスト: 328 passed, 1 skipped
- .NET: 34 passed (Core分離後も全通過)
- プロジェクト健全性: Ruff 0 + Mypy 0 + CI全緑 = A+ ランク
- 残り改善ポイント: テストカバレッジ (57%→80%+)

## 履歴

- 2026-02-24: TASK_007 シナリオB完了、実機検証成功。
- 2026-03-02 午前: リモート同期、プロジェクト現状評価。
- 2026-03-02 夜: 総合監査、TASK_021-025起票。
- 2026-03-03 深夜: TASK_021/022/023 Layer A完了。TASK_024 Pipeline Refactoring完了。
- 2026-03-03 夜: shared-workflows脱却、リポジトリクリーンアップ、テスト安定化。
- 2026-03-04 昼: 外部TTS連携コードを完全削除。YMM4のみに注力。
- 2026-03-05 日中: Web UI modular化、.NET CI分離、Ruff統合。
- 2026-03-05 夜: Ruff全修正 (995→0)、Mypy全修正 (228→0)、CI 5段階全緑化。
- 2026-03-07: Gemini API統合、.NET Core分離、CIワークフロー11→6整理、OpenSpec削除。
- 2026-03-08: Path B dead code完全削除。
- 2026-03-09〜17: SP-024/026/027/028/030/031/032/033/034 全完了。E2E完走確認。
- 2026-03-16: 126コミット同期後、ruff/mypy regression修正 (12+36→0)。328 tests passed。

## 直近 Git Commits

```
c685454 fix(types): resolve ruff 12 + mypy 36 regressions across 11 files
87d5490 docs: HANDOVER.md Phase 3b + 4層フォールバック反映
608169f docs: spec-index.json SP-004 summary を全機能反映に更新
b34ff5e docs: HANDOVER.md HEAD参照を最新コミットに更新
c7f2afd docs: ymm4_export_spec セクション番号修正 + 7種アニメーション仕様拡充
```
