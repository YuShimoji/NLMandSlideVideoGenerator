# Worker D: NotebookLM自動化

## 担当範囲
- SP-047 NLM品質改善 (75% -> 100%): Playwright NLM自動化
- SP-051 音声転録 (70% -> 100%): 転録パイプライン完成
- src/notebook_lm/ の保守・拡張

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator
- 根本ワークフロー: NotebookLM → Audio Overview → テキスト化 → Gemini構造化 → CSV → YMM4
- NotebookLMは台本品質の源泉。Geminiは構造化のみ担当
- NotebookLM APIは未公開。Playwright (ブラウザ自動化) で操作する必要がある
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと (Section 0 が最重要)

## 現状
### SP-047 Phase 1-2 (完了)
- notebooklm-py (非公式ライブラリ) 調査完了
- P1+A方式確定: notebooklm-py + YMM4キャラ維持 + Study Guide経路
- 台本品質全指標PASS (Phase 2検証済み)

### SP-047 Phase 3以降 (未着手, hold状態)
- Playwright NLM自動化: NotebookLM Web UIのブラウザ自動操作
- src/notebook_lm/playwright_nlm.py: 基礎実装あり (未検証)
- tests/test_playwright_nlm.py: テストあり
- 課題: NotebookLMのUI変更に脆弱、認証フロー (Google OAuth) の自動化

### SP-051 音声転録
- 目的: NotebookLM Audio Overviewの音声をテキスト化
- transcript_processor.py: 基礎実装あり
- 実際の音声ファイルでのテスト未実施

## 技術的課題
1. **Google認証**: Playwright でGoogleログインを自動化する必要がある
2. **UI変更耐性**: NotebookLMのDOM構造が変わるとスクリプトが壊れる
3. **レート制限**: NotebookLMの利用制限 (Audio Overview生成回数)
4. **音声品質**: Audio Overviewの音声品質とテキスト化精度のトレードオフ

## 作業手順
1. docs/DESIGN_FOUNDATIONS.md Section 0 を読む (根本ワークフロー)
2. docs/specs/video_output_quality_standard.md (SP-047) を読む
3. docs/specs/audio_transcription_spec.md (SP-051) を読む
4. src/notebook_lm/playwright_nlm.py を確認
5. NotebookLMの現在のUI構造を調査
6. Playwright自動化の実装・テスト
7. 音声ファイルの転録テスト

## 成果物
- playwright_nlm.py の完成 (ログイン→ソース投入→Audio Overview生成→ダウンロード)
- 転録パイプラインのE2Eテスト
- SP-047 / SP-051 pct更新

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md (特にSection 0)
- docs/specs/video_output_quality_standard.md
- docs/specs/audio_transcription_spec.md
- docs/notebooklm_drift_analysis.md
- src/notebook_lm/playwright_nlm.py
- src/notebook_lm/transcript_processor.py
- src/notebook_lm/audio_generator.py (レガシースタブ - 参考)
- tests/test_playwright_nlm.py
