# HANDOVER

Timestamp: 2026-03-18
Actor: Claude Code (Nightshift + REFRESH)
Type: Session Handover (session 12)

## Current Status

46仕様中44 done + 1 partial (SP-035) + 1 draft (SP-045)。テスト 1258 passed。

| 領域 | 状態 | 備考 |
|------|------|------|
| 仕様書同期 | DONE | 8件 pct→100%、Imagen 4移行、ガイド全面更新、INDEX拡充 |
| 数値同期 | DONE | テスト数1050→1258、backlog整合 |
| SP-043 仕様同期 | DONE | Phase 4完了を spec ファイルに反映。pages.py.backup 削除 |
| SP-045 チェックリスト | DRAFT | 初回YouTube公開の通しチェックリスト (Phase A/B/C全ステップ) |
| SP-035 preflight | PASS | 36 PASS / 5 WARN / 0 FAIL。Python側準備完了 |
| SP-038 upload テスト | PASS | 45テスト全緑 (mockモード)。OAuth未取得 |
| task-scout | DONE | TikTok方針未決定/style_template仕様欠落/IPublishingQueue空実装 を発見 |
| テスト | 1258 passed, 0 failed | 全緑 |

## Current Slice

**SP-045: 初回YouTube公開** (REFRESH で設定)

ユーザー操作列:
1. `research_cli.py pipeline` で CSV 生成 (Phase A: 自動)
2. YMM4 で CSV インポート → Voice 生成 → レンダリング (Phase B: 手動)
3. `research_cli.py upload --privacy private` で YouTube テスト投稿 (Phase C)

成功条件: YouTube Studio で動画が再生可能

ブロッカー: OAuth トークン未取得 (手動1回で解消)

## Git State

- Branch: `master`
- HEAD: `3ca3169` (feat(SP-045): 初回YouTube公開チェックリスト)
- 未 push コミット: 4件
- Working tree: HANDOVER.md + CLAUDE.md 更新中

## Next Actions

| 優先度 | タスク | 手動/自動 |
|--------|--------|----------|
| 1 | SP-045 チェックリスト実行 (初回公開を1本通す) | 手動 |
| 1a | → Google Cloud Console で OAuth クライアント ID 作成 | 手動 |
| 1b | → `python scripts/google_auth_setup.py` で token.json 取得 | 手動 |
| 1c | → YMM4 実機テスト (SP-035 チェックリスト A-G) | 手動 |
| 1d | → `research_cli.py upload --privacy private` でテスト投稿 | 手動 |
| 2 | TikTokAdapter 方針決定 (廃止推奨) | 設計判断 |
| 3 | style_template cinematic/minimal の仕様記載 | 自動 |
| 4 | IPublishingQueue / BasicTimelinePlanner の方針決定 | 設計判断 |

## Pending Design Decisions

1. **TikTokAdapter**: 220行モック実装。仕様なし。YouTube長尺がターゲットなので廃止が妥当
2. **style_template バリアント**: cinematic/minimal が仕様書未記載。SP-031に追記すべきか
3. **IPublishingQueue**: Protocol定義のみ。スケジュール投稿も未実装。削除か将来予約か
4. **BasicTimelinePlanner**: テスト済みだがパイプライン未接続。接続の要否

## Primary References

- `docs/specs/first_publish_checklist.md` — 初回公開チェックリスト (SP-045)
- `docs/spec-index.json` — 全45仕様の状態一覧
- `docs/backlog.md` — バックログ + ロードマップ
- `docs/friction_inventory.md` — 摩擦インベントリ
- `CLAUDE.md` — プロジェクトコンテキスト + DECISION LOG
