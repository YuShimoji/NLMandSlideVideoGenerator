# HANDOVER

Timestamp: 2026-03-17
Actor: Claude Code (Driver)
Type: Session Handover (全SP完了後)

## Current Status

全仕様書(SP-001〜SP-033)完了。SP-033 Phase 3b テキストスライド自動生成完了。中期ロードマップフェーズ。

| 領域 | 状態 | 備考 |
|------|------|------|
| SP-033 Phase 3b | DONE | TextSlideGenerator: source=none→generated変換、PLACEHOLDER_THEMES使用、Orchestrator/CLI統合 |
| SP-033 Phase 3 | DONE | AIImageProvider (Gemini Imagen 3.0) + Orchestrator 3層フォールバック |
| SP-031 BGM | DONE | style_template.json v1.1 + Python/C#双方対応 |
| SP-034 再開機能 | DONE | PipelineState永続化 + CLI --resume |
| テスト | 997 passed | Python全テストPASS。カバレッジ84% (全体) / 92% (コア) |
| ドキュメント | 同期済み | spec-index.json, backlog.md, 各仕様書を実装に同期 |

## Production Path

```
CSV(話者,テキスト,画像パス,アニメ) → YMM4 (NLMSlidePlugin CSVインポート) → 音声生成(台本機能) → 動画出力 → mp4
```

## Git State

- Branch: `master`
- HEAD: `b34ff5e` (docs: HANDOVER.md HEAD参照を最新コミットに更新)
- Remote: `origin/master` は2コミット遅れ (push待ち)
- Working tree: docs/HANDOVER.md, docs/spec-index.json に軽微な更新あり

## Next Actions (中期ロードマップ)

| 優先度 | タスク | 備考 |
|--------|--------|------|
| HIGH | YMM4実機テスト | BGMテンプレート + ストック画像CSV + 字幕テンプレート全統合確認 |
| HIGH | Geminiクォータリセット後の実コンテンツ確認 | 無料枠20req/day制限下での品質評価 |
| MID | ドキュメント整備 | SP-006 (90%), SP-007 (85%) の残り |
| MID | Gemini有料プラン検討 | 本番運用時の費用対効果 |
| LOW | Docker化 / CI-CD強化 | 長期 |

## Key Architecture

- **Python層**: CSV生成 + 素材パイプライン (collect→script→align→review→CsvAssembler)
- **C#層**: NLMSlidePlugin (YMM4プラグイン: CSVインポート→タイムライン生成)
- **素材取得**: 4層フォールバック (Pexels/Pixabay → Gemini Imagen → TextSlideGenerator → none)
- **スタイル**: style_template.json v1.1 (video/subtitle/animation/bgm/crossfade/timing/validation)
- **Geminiモデル**: フォールバックチェーン (2.5-flash → 2.0-flash → モック)

## Primary References

- `docs/spec-index.json` — 全33仕様の状態一覧
- `docs/backlog.md` — バックログ + ロードマップ
- `docs/ymm4_export_spec.md` — YMM4エクスポート仕様
- `docs/visual_resource_pipeline_spec.md` — 素材パイプライン仕様
- `docs/video_quality_pipeline_spec.md` — 品質パイプライン仕様
- `CLAUDE.md` — プロジェクトコンテキスト + DECISION LOG
