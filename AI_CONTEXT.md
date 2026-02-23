# AI Context

## 基本情報

- **最終更新**: 2026-02-24T01:16:43+09:00
- **更新者**: Codex (Orchestrator)

## レポート設定（推奨）

- **report_style**: standard
- **mode**: normal
- **creativity_triggers**: 代替案を最低2件提示する / リスクとメリットを表形式で整理する

## 現在のミッション

- **タイトル**: TASK_007 YMM4PluginIntegration - Scenario B Verification（進行中）
- **Issue**: YMM4実機でのプラグイン動作検証と証跡化
- **ブランチ**: master
- **関連PR**: なし
- **進捗**: **進行中** - シナリオZero+A完了、シナリオB待ち

## 次の中断可能点

- **TASK_011完了同期済み** - 方針転換ゲート整備（境界定義/ロールバック条件）反映完了

## 決定事項

- shared-workflows v3 を採用。ORCHESTRATOR_DRIVER.txt（44行）を毎回のエントリポイントとする。
- 表示ルールは `.shared-workflows/data/presentation.json` v3 を SSOT とする。
- 外部実行ファイル検出は `src/core/utils/tool_detection.py` に集約（`AUTOHOTKEY_EXE` / `YMM4_EXE` / `FFMPEG_EXE`）。
- 品質SSOTは 480p/720p/1080p に統一（4K未対応）。
- CSV + 行ごとのWAV → CSVパイプラインで動画/字幕/サムネ/メタデータ生成が現行SSOT。
- TASK_011で方針転換ゲートを整備し、評価スキーマ（★★★/★★☆/★☆☆）とロールバック条件（4トリガー）を採用。

## リスク/懸念

- `src/` 内に残っている `except Exception` は特定例外後の catch-all。必要に応じて細分化/削除を検討（挙動維持が前提）。
- 生成物/ビルド成果物（例: `ymm4-plugin/obj`）が意図せず管理対象になっていないか確認。
- YMM4連携は .NET プラグインAPI優先へ方針転換済みだが、IVoicePlugin/ITextCompletionPlugin 詳細仕様不足のため保留中。
- 実機で確認された `InvalidCastException` は修正済みだが、YMM4 GUIでの再検証完了までは最終確定できない。

## テスト

- **command**: `.\venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short`
- **result**: 109 passed, 7 skipped, 4 deselected (2026-02-06)

## タスク管理（短期/中期/長期）

### 短期（Next）

- [in_progress] YMM4プラグイン連携実装 (ref: docs/tasks/TASK_007_YMM4PluginIntegration.md, Status: IN_PROGRESS)
- [pending] SofTalk連携実装 (ref: docs/tasks/TASK_008_SofTalkIntegration.md, Status: CLOSED)
- [pending] YMM4エクスポート仕様策定 (ref: docs/tasks/TASK_009_YMM4ExportSpecification.md, Status: COMPLETED)

### 中期（Later）

- broad `except Exception` の残存箇所をさらに細分化
- YMM4 プラグインAPI仕様が判明次第、C3-1/C3-2 再開

### 長期（Someday）

- CLI/監査フローを他リポジトリへ展開し、共通運用化
- 動画生成品質の自動評価パイプライン

## Backlog

- [ ] `src/` 内 catch-all `except Exception` の段階的細分化
- [x] `ymm4-plugin/obj` 等のビルド成果物が .gitignore に含まれているか確認（`**/obj/` `**/bin/` で対応済み）
- [x] `orchestrator-audit.js` を CI へ統合（`.github/workflows/orchestrator-audit.yml`）
- [x] docs/ 内のレガシーHANDOVER（日付付き）のアーカイブ整理

## 備考（自由記述）

- Python 3.11.0 を使用（3.14は非対応）。
- 仮想環境: `.\venv\` を使用。
- shared-workflows v3 移行完了（2026-02-06）: サブモジュール 4ad0a0a、.windsurf/workflows/ 新設、.cursorrules v3化。

## 履歴

- 2025-10-31: Python環境構築完了、OpenSpec統合
- 2025-12-16: CSV+WAV E2E安定化、品質SSOT統一（480p/720p/1080p）
- 2026-01-xx: broad except Exception の想定例外中心への分割（全主要モジュール対応済み）
- 2026-02-06: shared-workflows v3 統合、IDE最適化（.windsurf/workflows/ 新設、.cursorrules v3化、AI_CONTEXT v3化）
- 2026-02-06: プロジェクトクリーンアップ（レガシーファイルアーカイブ、ドキュメント整合性修正）

## Worker完了ステータス

- task_004_report_fix: completed, priority: critical, timeout: 30
- task_010_report_fix: completed, priority: critical, timeout: 30
- handover_ai_context_alignment: completed, priority: critical, timeout: 30
- task_011_policy_pivot_gate: completed, priority: high, timeout: 30

## 2026-02-24 01:47 Context Update
- TASK_007 ScenarioB: runtime behavior mismatch traced to old deployed plugin DLL.
- Local build succeeded with latest import logic (`SkipPluginCopy=true`).
- Blocker: YMM4 process lock prevents replacing deployed DLL.
- Next action: close YMM4 -> deploy latest DLL -> re-test timeline import.

## 2026-02-24 03:39 Context Update
- TASK_007 ScenarioB: deploy DLL を最新版へ同期完了（hash match）。
- AutoCheck PASS（build/deploy/contract）。
- Next: GUI manual verification only.
