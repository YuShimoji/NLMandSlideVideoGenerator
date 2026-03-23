# AI Context

## 基本情報

- **最終更新**: 2026-03-22
- **更新者**: Claude Opus 4.6

## レポート設定（推奨）

- **report_style**: standard
- **mode**: normal

## 現在のミッション

- **タイトル**: 中期ロードマップ — 実運用品質 + ドキュメント仕上げ
- **Issue**: 全SP完了後、YMM4実機テスト・Gemini実コンテンツ確認・テストカバレッジ拡充
- **ブランチ**: master
- **進捗**: 全50仕様 (SP-001〜SP-050)。45 done + 4 partial (SP-035/037/047/048) + 1 draft (SP-045)。根本ワークフロー復元済み (DESIGN_FOUNDATIONS.md)。E2Eパイプライン完走確認済み。8種アニメーション、4層フォールバック素材パイプライン、Gemini構造化+フォールバックチェーン稼働中。

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
- 素材パイプライン: Pexels → Pixabay → Wikimedia Commons。Gemini Imagen (有料プラン専用)・TextSlideGenerator (削除済) はレガシー。
- SP-004: pan_down追加で8種アニメーション完成 (2026-03-17)。全spec done化。
- SP-019: Troubleshooting Guide v2.0。Gemini/ストック素材/パイプライン再開/アニメーション追加 (2026-03-17)。
- test_main.py RuntimeWarning修正: _close_and_raiseでコルーチン未awaitを解消。

## 品質指標（2026-03-17）

| 指標 | 値 | 備考 |
| :--- | :--- | :--- |
| Ruff errors | **0** | 79 source files checked |
| Mypy errors | **0** | 79 source files checked |
| Python Tests | **1262 passed** | カバレッジ84% (全体) / 92% (コア) |
| .NET Build | **0 warnings, 0 errors** | CS1998警告解消 |
| .NET Tests | **34 passed** | Core分離後も全通過 |
| CI workflows | **6/6 green** | ローカルCI全緑 |
| Health Score | **100/100 (A+)** | 全仕様done + 980テスト0 warnings + コア92% |

## リスク/懸念

- テストカバレッジ: 84%達成 (1262 tests)。コア92%。残り未テストは外部API/Web UI依存モジュール
- GitHub Actions CI Layer B: ci-main.yml修正済み (mypy全src/, ruff --exit-zero除去, flake8→ruff統合)。push後の実行確認待ち
- YMM4本体のDLLがローカル環境で見つからないため、C#プロジェクトのビルドが制限されている
- pip: google-auth-oauthlib互換性警告あり (google-auth 2.49.1 vs oauthlib要求 <2.42.0、機能影響なし)

## テスト

- **command**: `.\venv\Scripts\python.exe -m pytest tests\ -q -m "not slow and not integration" --tb=short --ignore=tests/test_alignment_export.py`
- **result**: 1262 passed (2026-03-21)
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
| **短期** | TEST-COVERAGE | テストカバレッジ拡充 → 920 (82%) | **完了** | 高 |
| **短期** | SP-004-DONE | pan_downアニメーション追加 → 8種完成 | **完了** | 高 |
| **短期** | SP-019-DONE | Troubleshooting Guide v2.0 (70→100%) | **完了** | 高 |
| **短期** | YMM4-REAL | YMM4実機テスト (BGM+画像+字幕統合) | 待機 | 高 |
| **短期** | GEMINI-QUAL | Geminiクォータリセット後の品質確認 | 待機 | 高 |
| **中期** | DOC-FINISH | SP-006/SP-007 仕上げ (90%/85%→100%/100%) | **完了** | 中 |
| **中期** | GEMINI-PAID | Gemini有料プラン検討 | 構想 | 中 |
| **長期** | DOCKER-CI | Docker化 / CI-CD強化 | BACKLOG | 低 |
| **長期** | MULTI-LANG | 多言語台本自動照合強化 | 構想 | 低 |
| **長期** | MONETIZE | YouTube自動公開パイプライン | 構想 | 低 |

## Production Path (2026-03-22 更新)

> **根本ワークフロー** (DESIGN_FOUNDATIONS.md Section 0)

```text
NLM ソース投入 → Audio Overview → テキスト化 → Gemini構造化 → CSV(話者,テキスト,画像パス,アニメ) → YMM4 (NLMSlidePlugin CSVインポート) → 音声生成(台本機能) → 動画出力 → mp4
```

台本品質は NotebookLM が決定。Gemini は構造化 (speaker/text 分離) のみ。フォールバック時のみ台本生成。

## カバレッジ状況 (2026-03-17, 1050 tests)

全体: 84% (6108行) / コア: 92% (外部API+レガシー除外時 5413行)

### 低カバレッジモジュール (外部API依存、改善困難)

- `src/core/editing/ymm4_backend.py` (18%) — YMM4 SDK依存
- `src/slides/google_slides_client.py` (17%) — Google Slides API
- `src/youtube/uploader.py` (24%) — YouTube Data API (モック実装)
- `src/gapi/google_auth.py` (36%) — Google OAuth
- `src/core/persistence/__init__.py` (0%) — No-opスタブ (意図的)

### テスト済みだが改善余地あり

- `src/core/stage_runners.py` (69%) — 例外ハンドラ分岐
- `src/server/api_server.py` (80%) — ダッシュボード/テンプレート描画
- `src/server/api.py` (87%) — パイプライン実行の例外分岐

### Web UI (Streamlit依存、テスト対象外)

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
- [x] テストカバレッジ拡充 (82%)
- [x] GitHub Actions CI有効化 (2026-03-16: ci-main.yml修正 — mypy全src/, flake8→ruff統合, --exit-zero除去)
- [ ] Codecov統合

## 備考（自由記述）

- Python 3.11.0 / venv 環境を使用。
- テスト: 1050 passed, 0 warnings (Python) + 34 passed (.NET)
- .NET: 34 passed (Core分離後も全通過)
- プロジェクト健全性: Ruff 0 + Mypy 0 + CI全緑 + 全spec done = A+
- テストカバレッジ: 84% (全体) / 92% (コア)
- 全50仕様 (45 done + 4 partial + 1 draft)

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

```text
718fcd2 docs(SP-019): Troubleshooting Guide v2.0 — 70% → 100%
e52d2c7 feat(SP-004): add pan_down animation (8th type) + fix 4 RuntimeWarnings
fe7a1ff ci: disable auto-revert in CI Failure Rollback (notify-only mode)
b8724ed test: expand coverage to 82% (920 tests) + fix all CI mypy errors
e384c26 docs: update CLAUDE.md project context for handoff (coverage 71%, 821 tests)
```
