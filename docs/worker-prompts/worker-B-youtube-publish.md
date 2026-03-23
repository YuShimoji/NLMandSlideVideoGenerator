# Worker B: YouTube公開パイプライン

## 担当範囲
- SP-038 YouTube公開 (95% -> 100%): 本番OAuth取得 + 実チャンネルテスト
- SP-045 初回公開チェックリスト (draft -> partial): 通し実行サポート
- SP-039 MP4品質検証: 実MP4での検証確認
- src/youtube/ の保守

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator
- YouTube Data API v3 を使用した resumable upload
- Publisher: Phase 7統合オーケストレーター (MP4検証→メタデータ→アップロード→結果永続化)
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状
### SP-038 YouTube公開
- Phase 1-3 実装完了
- publisher.py / uploader.py / metadata_generator.py 全て done
- テストOAuth使用中。本番OAuthトークン未取得
- 残タスク:
  1. Google Cloud Console で本番OAuth認証情報を作成
  2. YouTube Data API v3 有効化確認
  3. 実チャンネルへのテストアップロード (unlisted)
  4. クォータ使用量の確認 (1日10,000ユニット制限)

### SP-045 初回公開チェックリスト
- SP-050準拠でPhase 0-5構成に全面改版済み
- 手順書完成。人間が実際に1本通すことで検証
- docs/specs/first_publish_checklist.md

### SP-039 MP4品質検証
- FFprobe 10検証項目実装済み
- SP-038連携: upload前品質ゲートとして動作
- 実MP4での検証はSP-035 (Worker A) と連携

## 作業手順
1. docs/DESIGN_FOUNDATIONS.md を読む
2. docs/specs/youtube_publish_pipeline.md (SP-038) を読む
3. docs/specs/first_publish_checklist.md (SP-045) を読む
4. scripts/google_auth_setup.py でOAuth設定
5. src/youtube/publisher.py の動作確認
6. 実チャンネルへの unlisted テストアップロード

## 成果物
- 本番OAuth認証情報 (.env に設定)
- テストアップロード結果レポート
- SP-038 pct 100% への更新
- クォータ使用レポート

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/specs/youtube_publish_pipeline.md
- docs/specs/first_publish_checklist.md
- docs/specs/video_output_quality_standard.md
- src/youtube/publisher.py
- src/youtube/uploader.py
- src/youtube/metadata_generator.py
- scripts/google_auth_setup.py
- .env.example (認証キー設定)
