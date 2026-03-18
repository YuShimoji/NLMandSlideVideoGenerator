# HANDOVER

Timestamp: 2026-03-18
Actor: Claude Code (Nightshift)
Type: Session Handover (session 12 nightshift)

## Current Status

44仕様中43 done。残 partial: SP-035(60%), SP-038(90%)。テスト 1182 passed。

| 領域 | 状態 | 備考 |
|------|------|------|
| 仕様書同期 | DONE | 8件 pct→100%、Imagen 4移行反映、開発ガイド全面更新 |
| INDEX.md | DONE | docs/specs/ 10件 + 欠落ファイル追加 |
| 数値同期 | DONE | テスト数1050→1182 (system_spec/arch/SSOT/spec-index) |
| backlog.md | DONE | SP-039/043/044 done反映、ロードマップ更新 |
| テスト | 1182 passed, 3 skipped | Python全テストPASS |
| ドキュメント | 同期済み | spec-index.json + 全主要ドキュメント |

## Production Path

```
CSV(話者,テキスト,画像パス,アニメ) → YMM4 (NLMSlidePlugin CSVインポート) → 音声生成(台本機能) → 動画出力 → mp4
```

## Git State

- Branch: `master`
- Working tree: 変更あり (HANDOVER.md等更新中)
- push はしていない

## Remaining Work

| 優先度 | タスク | 備考 |
|--------|--------|------|
| HIGH | SP-035 YMM4実機テスト (60%) | チェックリスト整備済み。YMM4環境で手動実施が必要 |
| HIGH | SP-038 本番OAuth取得 + 実チャンネルテスト (90%) | Phase 1-3実装完了。本番クレデンシャルが必要 |
| MID | デッドコード整理方針 | persistence NoOp (7参照) / tiktok mock (helpers.py参照) — 削除には設計判断必要 |
| LOW | Docker化 / CI-CD強化 | 長期 |

## Key Architecture

- **Python層**: CSV生成 + 素材パイプライン (collect→script→align→review→CsvAssembler)
- **C#層**: NLMSlidePlugin (YMM4プラグイン: CSVインポート→タイムライン生成)
- **素材取得**: 4層フォールバック (Pexels/Pixabay → Gemini Imagen 4 → TextSlideGenerator → none)
- **スタイル**: style_template.json v1.1 (video/subtitle/animation/bgm/crossfade/timing/validation)
- **LLM**: ILLMProvider 5プロバイダー (Gemini/OpenAI/Anthropic/Groq/モック)

## Primary References

- `docs/spec-index.json` — 全44仕様の状態一覧
- `docs/backlog.md` — バックログ + ロードマップ
- `docs/INDEX.md` — 全ドキュメントインデックス
- `CLAUDE.md` — プロジェクトコンテキスト + DECISION LOG
