# Project Context

## PROJECT CONTEXT

- プロジェクト名: NLMandSlideVideoGenerator
- 環境: Python 3.11 (venv) / .NET 10.0 (YMM4 plugin) / Windows 11
- ブランチ戦略: trunk-based (master)
- 現フェーズ: docs負債解消完了 → コミット整理待ち → 初回通し実行待ち
- 直近の状態 (2026-03-23 Worker A/C/D session):
  - Worker A: SP-052 Phase 1-3 AI側完了 (overlay_plan.json自動生成+CsvImportDialog統合+ハイブリッドスタイル方針確定)
  - Worker C: SP-048 Phase 2 完了確認 (74テスト全緑、実API疎通のみ残)
  - Worker D: SP-051 AudioTranscriber + SP-047 playwright_nlm改善 + YMM4一本化レガシー整理
  - SP-035実機テスト準備完了 (preflight 35 PASS, テスト画像6枚+overlay_plan.json生成済み)
  - テスト: 1242+ passed / 0 failed
  - 核心課題: 53仕様だが実動画を1本も通しで作っていない → SP-045通し実行が最優先

---

## LEGACY BOUNDARIES

> 全セッション必読: `docs/DESIGN_FOUNDATIONS.md` Section 5 (Legacy Boundary Map)
> CLAUDE.md の Legacy Boundaries セクションも参照。

**YMM4 は唯一のマルチメディア合成ワークスペース。**
Python 側の音声合成・TTS・動画レンダリング・PILスライド生成・Brave Searchリサーチは全てレガシー。
外部APIや音声関連の新規開発・拡張は行わない。

---

## CURRENT DEVELOPMENT AXIS

- 主軸: 初回YouTube公開準備 (SP-045)
- この軸を優先する理由: 53仕様・1241テストが積み上がったが実動画ゼロ。制作者パイプラインの実検証が急務
- 今ここで避けるべき脱線: 新機能開発 (GUI Phase 2, Playwright NLM自動化)

---

## CURRENT LANE

- 主レーン: Acceptance / E2E
- 副レーン: なし
- 今このレーンを優先する理由: 実動画を1本通すことが全仕様の受け入れ判定に必須
- いまは深入りしないレーン: Authoring / Tooling (SP-053 GUI Phase 2), Experience Slice

---

## CURRENT SLICE

- スライス名: SP-045 初回YouTube公開通し実行
- 到達状態 (session 22 CLOSE時点):
  - docs負債解消完了 (project-context.md作成, 孤立参照除去, 統計値修正)
  - コードパス検証完了 (PRODUCER_PIPELINE.md全CLIコマンドがコードと一致)
  - テスト全緑 (1241 passed)
  - src/*.pyに孤立import残存ゼロ
  - **未着手**: 実際のPhase 0-7通し実行 (人間操作必須)
- ユーザー操作列:
  1. トピック選定 + NotebookLM ソース投入 (Phase 0) -- 手動
  2. NotebookLM Audio Overview 生成 + ダウンロード (Phase 1) -- 手動
  3. `python scripts/research_cli.py pipeline --topic X --audio Y` (Phase 2-4) -- 自動
  4. YMM4 起動 + CSV インポート + レンダリング (Phase 5) -- 手動
  5. `python scripts/research_cli.py verify output.mp4` (Phase 6) -- 自動
  6. YouTube 公開 (Phase 7) -- 半自動
- 成功状態: YouTube上に1本の動画が公開されている
- このスライスで必要な基盤能力: Phase 2-4 コードパスが動作する (検証済み)
- 今回はやらないこと: サムネイル自動生成、Playwright NLM自動化、GUI Phase 2

---

## FINAL DELIVERABLE IMAGE

- 最終成果物: YouTube長尺解説動画を半自動生産するパイプライン
- 最終的なユーザーワークフロー:
  1. 人間がNotebookLMにソースを投入しAudio Overviewを生成
  2. Python が音声→構造化→CSV→素材調達を自動実行
  3. YMM4 が CSV インポート→音声合成→レンダリング (人間操作 ~5分)
  4. Python が MP4検証→YouTube公開を半自動実行
- 受け入れ時の使われ方: 制作者 (= プロジェクトオーナー) が週1本以上のペースで動画を公開
- 現時点で未確定な要素:
  - YMM4動画品質テンプレート (SP-052, draft 0%)
  - Google Slides API テンプレート (Phase 3 スライド生成)
  - Playwright NLM半自動化の実現可能性
  - 本番Google OAuth

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
| 2026-03-23 | SP-053 制作者GUI: Streamlit再構成 | 既存UI資産を活用。Phase 1 Streamlit |
| 2026-03-23 | SP-041 TextSlideQuality → superseded | TextSlideGenerator削除に伴い仕様も superseded |

完全な DECISION LOG は `CLAUDE.md` を参照。

---

## IDEA POOL

| ID | アイデア | 状態 | 関連領域 | 再訪トリガー |
|----|----------|------|----------|-------------|
| IP-001 | Playwright NLM半自動化 | hold | tool / automation | Phase 0-1 の手動操作が制作ボトルネックになったとき |
| IP-002 | Google Slides API テンプレート | hold | visual / slides | Phase 3 スライド品質が YouTube水準に未達のとき |
| IP-003 | SP-053 Phase 3: Electron/Tauri GUI | hold | ui | Streamlit の制約に当たったとき |
| IP-004 | overlay_plan.json (動画内テキストオーバーレイ) | hold | plugin / quality | SP-052 実装開始時 |
| IP-005 | PyNotebookLM (v0.21.0) 統合 | hold | automation | NLM API 代替として検討 (session 20 で発見) |

---

## HANDOFF SNAPSHOT

- 現在の主レーン: Acceptance / E2E
- 現在のスライス: SP-045 初回YouTube公開通し実行 (docs準備完了, 実行は人間操作待ち)
- 今回変更した対象 (session 22):
  - docs/project-context.md 新規作成
  - scripts/preflight_sp035.py TextSlideGenerator孤立import除去
  - docs 11ファイル: system_architecture, system_specification, ymm4_integration_arch, ymm4_final_workflow, TROUBLESHOOTING, development_guide, thumbnail_pipeline, ymm4_export_spec, DESIGN_FOUNDATIONS, text_slide_quality, video_output_quality_standard, visual_resource_pipeline_spec の孤立参照修正
  - CLAUDE.md テスト数修正 (1272→1241)
  - HANDOVER.md session 22 追記
  - spec-index.json SP-041 status: done → superseded
- 次回最初に確認すべきファイル:
  - git status (58ファイル変更 + 14 untracked + 25 commits unpushed)
  - docs/PRODUCER_PIPELINE.md (制作者ワークフロー手順書)
  - docs/specs/first_publish_checklist.md (SP-045 チェックリスト)
- 未確定の設計論点:
  - 初回通し実行の対象トピック (HUMAN_AUTHORITY)
  - YMM4テンプレート Pattern A-E のうちどれを先に作るか (HUMAN_AUTHORITY)
  - 未コミット変更のコミット分割戦略 (一括 or session別 or 機能別)
- 今は触らない範囲: SP-053 GUI Phase 2, Playwright NLM自動化, Google OAuth, 新SP追加
