# Task: Gemini API 実動作確認 (E2E Verification)
Status: IN_PROGRESS
Tier: 1
Branch: master
Owner: Worker
Created: 2026-02-06T13:50:00+09:00

## 概要

Gemini APIキー設定済み環境で、台本生成→スライド生成→(TTS→)動画生成のE2Eフローを実APIで動作確認する。

## 前提

- TASK_003 (DONE): Gemini API実装・フォールバック・スモークテスト完了
- `google-generativeai` v0.8.5 インストール済み
- `.env` ファイル作成済み（APIキーはプレースホルダー → 実キー設定が必要）

## 現状 (2026-02-06)

- ✅ E2Eテストスクリプト作成: `scripts/test_gemini_e2e.py`
- ✅ モックフォールバック動作確認: 全PASS
- ⏳ 実APIキー未設定: `.env` の `GEMINI_API_KEY` にプレースホルダー値のみ
- ⏳ TTS未設定: `TTS_PROVIDER=none`

## サブタスク

- [x] E2Eテストスクリプト作成 (`scripts/test_gemini_e2e.py`)
- [x] モックフォールバック動作確認
- [ ] GEMINI_API_KEY を実キーに設定
- [ ] 実API台本生成テスト（Step 1）
- [ ] 実APIスライド生成テスト（Step 2）
- [ ] AudioGenerator E2E（Gemini台本→placeholder音声）
- [ ] (Optional) TTS設定後のフルE2E

## 検証手順

```powershell
# 1. APIキー検証
.\venv\Scripts\python.exe scripts\verify_api_keys.py

# 2. E2E動作確認
.\venv\Scripts\python.exe scripts\test_gemini_e2e.py

# 3. 既存テストが壊れていないことを確認
.\venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short
```

## DoD

- [ ] 実APIで台本生成が成功する（モックではなく実レスポンス）
- [ ] 実APIでスライド生成が成功する
- [ ] 既存テスト（109 passed）が維持される
- [ ] 結果をドキュメントに記録

## Forbidden Area

- 既存CSV+WAVワークフローの変更
- フォールバック戦略の変更

## Notes

- APIキーは https://aistudio.google.com/app/apikey で取得
- TTS連携は別途TTSプロバイダ（ElevenLabs/OpenAI/Azure/Google Cloud）の設定が必要
- モックフォールバックのスライド生成はSlides:0になるが、これはモック実装の制約（実APIでは正常動作する想定）
