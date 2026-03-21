# HANDOVER

Timestamp: 2026-03-21
Actor: Claude Code (session 15 NIGHTSHIFT)
Type: Session Handover

## Current Status

47仕様中44 done + 2 partial (SP-035 60%, SP-047 40%) + 1 draft (SP-045)。テスト 1262 passed / 0 failed。

**今回の進捗: 台本品質改善 + NotebookLM API調査 + パイプラインバリデーション接続**

| 領域 | 状態 | 備考 |
|------|------|------|
| SP-047 Phase 1 | DONE | NotebookLM Enterprise API調査完了。Enterpriseライセンス必要、スライドAPI未公開 |
| SP-047 Phase 1.5 | DONE | 台本品質改善: セグメント粒度15-25秒、プロンプト5項目改善、テスト4件追加 |
| SP-044 接続 | DONE | segment_duration_validatorをstage_runners.pyに接続。バリデーション+自動調整 |
| テスト | 1262 passed (+4) | 台本品質検証テスト追加 |

## Commits (session 15)

1. `a0cd8a1` fix(SP-047): セグメント粒度短縮 + 台本プロンプト品質改善
2. `ca06b16` fix(SP-044): セグメントバリデータの期待範囲を新粒度に同期
3. `adc35d8` docs: SP-047台本品質改善を反映 + テスト数1258→1262同期
4. `0623d17` feat(SP-044): セグメントバリデーションをパイプラインに接続
5. `3df3c41` docs(SP-047): Phase 1 NotebookLM API調査完了

## Key Findings (session 15)

### 1. NotebookLM Enterprise API

- 正式API (Discovery Engine v1alpha) が存在する
- notebooks.create / sources.batchCreate / audioOverviews.create が利用可能
- **スライド生成APIは未提供** (Web UIのSlide Deck / Infographics機能のみ)
- **Enterprise ライセンスが必要** — 無料版NotebookLMではAPI利用不可
- 非公式ライブラリ (notebooklm-py) はWeb UIの非公開APIをリバースエンジニアリング

### 2. 台本品質改善 (実装済み)

- セグメント粒度: 40-65秒 → 15-25秒 (全4プリセット)
- 発話長: 200-400文字 → 50-150文字
- フック: 冒頭セグメントにフック指示追加
- ソース引用: リテラル番号 → 自然な言い回し
- キャラクター個性: テンプレート相槌排除指示 (news/educational)

### 3. パイプラインバリデーション接続

- segment_duration_validator はテストのみで利用されていた (productionコード未接続)
- stage_runners.py に validate_segments + adjust_segments を接続済み

## Next Actions

| 優先度 | タスク | 手動/自動 |
|--------|--------|----------|
| 1 | SP-047 Phase 2: 台本品質を実際のGemini出力で検証 (1本生成して確認) | 手動 |
| 2 | 著作権クリア画像の自動収集方法の実装 (Wikimedia Commons / CC検索) | 自動 |
| 3 | SP-035: YMM4実機テスト (60%→100%) | 手動 |
| 4 | SP-038: 本番OAuth取得 + 実チャンネルテスト | 手動 |
| 5 | デッドコード整理 (TikTokAdapter/IPublishingQueue) | HUMAN_AUTHORITY |

## Pending Design Decisions

1. **NotebookLM Enterprise ライセンス取得**: コスト vs 価値の判断 (HUMAN_AUTHORITY)
2. **notebooklm-py (非公式API) の採用**: 安定性リスク vs 機能の豊富さ (HUMAN_AUTHORITY)
3. **TikTokAdapter / IPublishingQueue**: デッドコード削除 (HUMAN_AUTHORITY, session 13からの持ち越し)
4. **スライド生成の方向性**: PIL改善 / NotebookLM非公式API / Gemini+テンプレート (HUMAN_AUTHORITY)

## Primary References

- `docs/specs/video_output_quality_standard.md` — SP-047 品質基準仕様 (API調査結果含む)
- `docs/video_quality_diagnosis.md` — 品質診断結果
- `docs/notebooklm_drift_analysis.md` — NLM→Geminiドリフト分析
- `config/script_presets/*.json` — 台本スタイルプリセット (更新済み)
- `src/core/segment_duration_validator.py` — セグメントバリデータ (更新済み)
- `src/core/stage_runners.py` — パイプラインステージ (バリデーション接続済み)
