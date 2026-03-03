# Task: VOICEVOX TTS統合
Status: LAYER_A_DONE
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Report: (未作成)

## Objective
- 高品質ニューラルTTSエンジン VOICEVOX をプロジェクトに統合する
- SofTalk/AquesTalkに加えた3つ目のTTSバックエンドとして、音声品質を大幅に向上させる
- 既存のIVoicePipelineインターフェースに準拠した差し替え可能な設計を維持する

## Context
- docs/technical/SOFTALK_INTEGRATION_ASSESSMENT.md で VOICEVOX が推奨TTS代替として評価済
- 既存TTS抽象化: `src/core/interfaces.py::IVoicePipeline`
- 既存実装: `src/core/voice_pipelines/tts_voice_pipeline.py`（ElevenLabs/OpenAI/Azure対応）
- SofTalk: ローカルWin32合成（低品質だが高速・無料）
- VOICEVOX: ローカルニューラルTTS（高品質・無料・REST API）

## Deliverables

### Layer A（AI完結）

#### A-1: VOICEVOX クライアント実装
- [x] `src/audio/voicevox_client.py` 作成
  - VOICEVOX Engine REST API クライアント
  - /audio_query, /synthesis エンドポイント対応
  - スピーカーID管理（ずんだもん、四国めたん等）
  - 音声パラメータ（速度、ピッチ、抑揚）設定
- [x] 接続チェック + 自動起動ヘルパー

#### A-2: IVoicePipeline 準拠アダプタ
- [x] `src/core/voice_pipelines/voicevox_pipeline.py` 作成
  - IVoicePipeline プロトコルに準拠
  - バッチ合成（セグメント単位並列処理）
  - リトライ + フォールバック（VOICEVOX → SofTalk）

#### A-3: 設定・環境統合
- [x] `config/settings.py` に VOICEVOX 設定セクション追加
  - engine_url (default: http://localhost:50021)
  - speaker_id, speed, pitch, intonation
  - auto_start (bool)
- [ ] `scripts/check_environment.py` に VOICEVOX 検出追加
- [ ] `.env.example` にVOICEVOX設定追加

#### A-4: バッチ処理スクリプト
- [ ] `scripts/tts_batch_voicevox.py` 作成
  - CSV → セグメントごとのWAV生成
  - 既存の `tts_batch_softalk_aquestalk.py` と同じI/O仕様
  - 進捗表示 + エラーハンドリング

#### A-5: テスト
- [x] `tests/test_voicevox_pipeline.py` 作成
  - モック使用の単体テスト（API呼び出しなし）
  - REST APIレスポンスのパーステスト
  - フォールバックシナリオテスト
- [x] 既存テスト群への回帰確認

### Layer B（手動検証）

| # | 検証項目 | 手順 | 期待結果 |
|---|---------|------|---------|
| 1 | VOICEVOX Engine起動 | VOICEVOX Engineインストール → 起動 | http://localhost:50021/speakers でスピーカー一覧取得 |
| 2 | 単一音声合成 | `python -c "from src.audio.voicevox_client import ...; ..."` | WAVファイル生成、再生可能 |
| 3 | バッチ合成 | `python scripts/tts_batch_voicevox.py samples/basic_dialogue/timeline.csv` | セグメントごとのWAV + 結合WAV生成 |
| 4 | パイプライン統合 | `python scripts/run_csv_pipeline.py --tts voicevox ...` | VOICEVOX音声による動画生成 |
| 5 | フォールバック | VOICEVOX停止状態で実行 | SofTalkにフォールバック、警告ログ出力 |

## DoD (Definition of Done)
- [x] IVoicePipeline 準拠の VOICEVOX アダプタ完成
- [x] モックテスト全パス
- [x] config/settings.py に設定統合済
- [ ] バッチスクリプトが既存CSV形式と互換 (A-4未実装)
- [ ] VOICEVOX Engine 停止時にSofTalkフォールバック動作 (Layer B)

## Dependencies
- VOICEVOX Engine のインストール（手動、Layer B）
- TASK_021 完了推奨（例外処理体系化後の方がクリーンな実装可能）

## Technical Notes
- VOICEVOX Engine REST API: POST /audio_query → POST /synthesis
- デフォルトポート: 50021
- 商用利用可（クレジット表記要）
- 対応OS: Windows, macOS, Linux

## Estimated Effort
- Layer A: 6-8時間
- Layer B: 2時間
