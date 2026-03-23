# Project Context

## PROJECT CONTEXT

- プロジェクト名: NLMandSlideVideoGenerator
- 環境: Python 3.11 (venv) / .NET 10.0 (YMM4 plugin) / Windows 11
- ブランチ戦略: trunk-based (master)
- 現フェーズ: **成果物駆動への転換完了。VS-1 (初動画) 人間操作待ち。**
- 直近の状態 (2026-03-23):
  - 成果物駆動マップ (DELIVERABLE_MAP.md) 新設
  - レガシー境界マップ統一 (DESIGN_FOUNDATIONS Section 5 + CLAUDE.md + 個別docs)
  - Worker A/B/C/D 検収完了 (1318 passed / 1 skipped)
  - **核心**: 53仕様・1318テスト積み上げ済み、実動画ゼロ。AI側作業は全て完了。VS-1の残りは全て人間操作。

---

## LEGACY BOUNDARIES

> 全セッション必読: `docs/DESIGN_FOUNDATIONS.md` Section 5 (Legacy Boundary Map)
> CLAUDE.md の Legacy Boundaries セクションも参照。

**YMM4 は唯一のマルチメディア合成ワークスペース。**
Python 側の音声合成・TTS・動画レンダリング・PILスライド生成・Brave Searchリサーチは全てレガシー。
外部APIや音声関連の新規開発・拡張は行わない。

---

## CURRENT DEVELOPMENT AXIS

- **開発方式: 成果物駆動 (Deliverable-Driven)**
- 主軸: VS-1 初動画完走 (DELIVERABLE_MAP.md 参照)
- この軸を優先する理由: 53仕様だが実動画ゼロ。「動くもの」を出すことが最優先
- 今ここで避けるべき脱線: 新SP追加、GUI開発、テストカバレッジ追求、ドキュメント整備のためのドキュメント整備
- 成果物スライス優先順: VS-1 → VS-2 → VS-3 → VS-4 → VS-5 (詳細は DELIVERABLE_MAP.md)

---

## CURRENT LANE

- 主レーン: Acceptance / E2E (VS-1 完走)
- 副レーン: なし
- 今このレーンを優先する理由: 実動画を1本通すことが全仕様の受け入れ判定に必須
- いまは深入りしないレーン: Authoring / Tooling (SP-053 GUI), Experience Slice

---

## CURRENT SLICE

- スライス名: VS-1 初動画完走
- 完了条件: NLM音声からパイプラインを通してMP4ファイルが生成される
- AI側作業: **全て完了** (パイプラインコード、テスト、チェックリスト、ドキュメント)
- 人間操作残タスク:
  1. .NET 10 SDK インストール + ymm4-plugin ビルド + YMM4に配置
  2. 環境変数設定 (GEMINI_API_KEY, PEXELS_API_KEY)
  3. NotebookLM でトピック選定 + ソース投入 + Audio Overview 生成
  4. `python scripts/research_cli.py pipeline --audio ...` 実行
  5. YMM4 CSV インポート + レンダリング
  6. MP4 再生確認
- 成功状態: 再生可能なMP4ファイルが存在する
- 手順詳細: `docs/specs/first_publish_checklist.md` (SP-045)

---

## FINAL DELIVERABLE IMAGE

- 最終成果物: YouTube長尺解説動画を半自動生産するパイプライン
- 最終的なユーザーワークフロー:
  1. 人間がNotebookLMにソースを投入しAudio Overviewを生成
  2. Python が音声→構造化→CSV→素材調達を自動実行
  3. YMM4 が CSV インポート→音声合成→レンダリング (人間操作 ~5分)
  4. Python が MP4検証→YouTube公開を半自動実行
- 受け入れ時の使われ方: 制作者が週1本以上のペースで動画を公開
- 成果物スライス (DELIVERABLE_MAP.md):
  - VS-1: 初動画完走 (MP4生成) -- **現在ここ (人間操作待ち)**
  - VS-2: YouTube公開
  - VS-3: 制作品質テンプレート
  - VS-4: サムネイル
  - VS-5: 自動化 (週1本ペース)

---

## DECISION LOG

> 2026-03-14以前のエントリは `docs/archive/decision-log-archive-pre-20260315.md` にアーカイブ済み。
> 最新のエントリは CLAUDE.md の DECISION LOG を参照。本ファイルでは方向性に大きく影響する決定のみ抜粋。

| 日付 | 決定事項 | 決定理由 |
|------|----------|----------|
| 2026-03-19 | NotebookLM回帰 (Geminiドリフト修正) | プロジェクト名 "NLM" = NotebookLM。根本ワークフローを復元 |
| 2026-03-21 | 設計公理文書 (DESIGN_FOUNDATIONS.md) 新設 | 三層モデル (NLM/Python/YMM4) を明文化。ドリフト防止 |
| 2026-03-22 | 根本ワークフロー復元 | NLM音声→テキスト化→Gemini構造化→CSV→YMM4 |
| 2026-03-22 | Brave Searchリサーチ廃止 | 人間がNLMに直接ソース投入する |
| 2026-03-22 | 品質優先 (「一晩3本」SSOT化を撤回) | 制作ペースは結果指標。品質が先 |
| 2026-03-23 | レガシー境界マップ統一 | ドキュメント散逸によるWorker混乱を防止 |
| 2026-03-23 | **成果物駆動への転換** | 53仕様・実動画ゼロ。SPリストではなく成果物スライスで開発を管理 |

完全な DECISION LOG は `CLAUDE.md` を参照。

---

## IDEA POOL

| ID | アイデア | 状態 | 関連VS | 再訪トリガー |
|----|----------|------|--------|-------------|
| IP-001 | Playwright NLM半自動化 | hold | VS-5 | VS-1手動操作が制作ボトルネックになったとき |
| IP-002 | Google Slides API テンプレート | hold | VS-3/5 | Phase 3 スライド品質が YouTube水準に未達のとき |
| IP-003 | SP-053 Phase 3: Electron/Tauri GUI | hold | VS-5 | Streamlit の制約に当たったとき |
| IP-004 | overlay_plan.json (動画内テキストオーバーレイ) | hold | VS-3 | VS-1完走後の品質評価時 |
| IP-005 | PyNotebookLM (v0.21.0) 統合 | hold | VS-5 | NLM API 代替として検討 |

---

## HANDOFF SNAPSHOT

- 現在の主レーン: Acceptance / E2E (VS-1完走)
- 現在のスライス: VS-1 初動画完走 (AI側完了, 人間操作待ち)
- 今回変更した対象 (session 23):
  - DELIVERABLE_MAP.md 全面改訂 (成果物駆動のVS-1〜5定義)
  - project-context.md 全面改訂 (スペック駆動→成果物駆動)
  - CLAUDE.md 成果物駆動方針追記 + DECISION LOG追記
  - レガシー境界マップ統一 (前セッション)
  - Worker A/B/C/D 検収 (前セッション)
- 次回最初に確認すべきファイル:
  - docs/DELIVERABLE_MAP.md (成果物スライス定義)
  - docs/specs/first_publish_checklist.md (VS-1チェックリスト)
- 未確定の設計論点 (全てVS-1完走後):
  - YMM4テンプレート Pattern A-E のうちどれを先に作るか (HUMAN_AUTHORITY, VS-3)
  - アニメーション方針 (HUMAN_AUTHORITY, VS-3)
  - サムネイルデザイン (HUMAN_AUTHORITY, VS-4)
- 今は触らない範囲: 新SP追加, GUI開発, OAuth設定, テストカバレッジ追求
