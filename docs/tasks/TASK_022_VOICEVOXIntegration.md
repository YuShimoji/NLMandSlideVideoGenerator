# Task: VOICEVOX TTS統合
Status: CLOSED (WONTFIX)
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Closed: 2026-03-04
Report: (N/A)

## Closure Reason
2026-03-04の方針決定により、プロジェクトはYMM4一本化に移行。
VOICEVOX/SofTalk/AquesTalkの全コードがリモートで削除され (commit 675decb)、
ローカルでも受け入れ済み。

### 削除された成果物
- `src/audio/voicevox_client.py`
- `src/core/voice_pipelines/voicevox_pipeline.py`
- `scripts/tts_batch_softalk_aquestalk.py`
- `tests/test_voicevox_pipeline.py`
- `tests/test_tts_batch_softalk_aquestalk.py`
- `tests/test_tts_integration.py`

### 経緯
- Layer Aの実装 (クライアント、パイプラインアダプタ、テスト) は完了していた
- しかしPath A (YMM4) が唯一のアクティブパスとなったため不要に
- YMM4内蔵のゆっくりボイスが音声生成を担う

## Original Objective (archived)
- 高品質ニューラルTTSエンジン VOICEVOX をプロジェクトに統合する
- SofTalk/AquesTalkに加えた3つ目のTTSバックエンドとして、音声品質を大幅に向上させる
- 既存のIVoicePipelineインターフェースに準拠した差し替え可能な設計を維持する
