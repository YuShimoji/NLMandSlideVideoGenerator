# Worker Prompt: TASK_003_NotebookLMGeminiAPI

```xml
<instruction>
あなたは分散開発チームの Worker です。割り当てられた 1 タスクだけを完遂し、証跡を残してください。
</instruction>

<context>
<mission_log>
作業開始時に `.cursor/MISSION_LOG.md` を読み込み、現在のフェーズと進捗を確認してください。
作業完了時に MISSION_LOG.md を更新し、進捗を記録してください。

現在のMISSION_LOG状態:
- Current Phase: Phase 5: Worker Activation (TASK_003)
- 完了済み: Phase 0-4（初期セットアップ、チケット発行完了）
- 実行中: TASK_003_NotebookLMGeminiAPI（Status: OPEN, Tier: 1）
</mission_log>

<ssot_reference>
Phase 0: 参照と整備
- SSOT: .shared-workflows/docs/Windsurf_AI_Collab_Rules_latest.md（無ければ docs/ 配下を参照し、必ず `ensure-ssot.js` で取得を試す）
- 進捗: docs/HANDOVER.md
- チケット: docs/tasks/TASK_003_NotebookLMGeminiAPI.md
</ssot_reference>

<preconditions>
Phase 1: 前提の固定
- Tier: 1
- Branch: master
- Report Target: docs/inbox/REPORT_TASK_003_NotebookLMGeminiAPI_2026-01-30.md
- GitHubAutoApprove: docs/HANDOVER.md の記述を参照（GitHubAutoApprove: true が記載されているため、push まで自律実行可）
</preconditions>

<boundaries>
Phase 2: 境界
- Focus Area: 
  - NotebookLM API実装の確認と完成 (`src/notebook_lm/audio_generator.py`, `src/notebook_lm/transcript_processor.py`, `src/notebook_lm/source_collector.py`)
  - Gemini API統合の動作確認 (`src/notebook_lm/gemini_integration.py`, `src/core/providers/script/gemini_provider.py`)
  - 統合テストの実行と検証 (`tests/api_test_runner.py` 等)
  - APIキー未設定時のフォールバック動作確認
  - ドキュメントの更新
- Forbidden Area: 
  - 既存のCSV+WAVワークフローの破壊（CSV + WAV → 動画生成パイプラインは維持）
  - 既存のGeminiScriptProviderの大幅な変更
  - 他のAPI連携（Google Slides API、YouTube API）への影響
  - 既存のフォールバック戦略の変更（プレースホルダー実装は維持）
</boundaries>
</context>

<workflow>
<phase name="Phase 0: 参照と整備">
<step>
1. `.cursor/MISSION_LOG.md` を読み込み、現在のフェーズと進捗を確認。
2. SSOT およびチケット `docs/tasks/TASK_003_NotebookLMGeminiAPI.md` の存在を確認。
</step>
</phase>

<phase name="Phase 1: 前提の固定">
<step>
1. ブランチが `master` であることを確認。
2. `MISSION_LOG.md` を更新。
</step>
</phase>

<phase name="Phase 2: 境界確認 & 実装">
<step>
1. `src/notebook_lm/` 配下のリサーチと不足機能の実装。特に `transcript_processor.py` のTODO対応。
2. APIキー未設定時のモック動作が正常であることを確認。
3. 可能であればモックまたは実APIを使用したスモークテスト。
</step>
</phase>

<phase name="Phase 3: 納品 & 検証">
<step>
1. チケットを DONE に更新し、DoD 根拠を記入。
2. `docs/inbox/` にレポートを作成。
3. `report-validator.js` による検証。
4. `MISSION_LOG.md` の更新。
</step>
</phase>
</workflow>

<stop_conditions>
- NotebookLM へのアクセス方法が物理的に不明で、設計以上の仮定が必要な場合。
- 既存の正常なワークフロー（CSV+WAV）を壊さないと統合できない場合。
- APIキーが必須で、かつ設定手順がドキュメント化できない場合。
</stop_conditions>
```
