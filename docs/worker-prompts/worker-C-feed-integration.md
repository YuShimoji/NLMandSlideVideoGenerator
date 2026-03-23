# Worker C: Feed/RSS統合

## 担当範囲
- SP-048 RSS/Feed統合 (80% -> 100%): Phase 2 パイプライン連携
- src/feed/ の保守・拡張

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator
- InoReader: RSSフィードリーダーサービス。OAuth2認証で記事を取得
- TopicExtractor: RSSアイテムからYouTube動画のトピック候補を抽出
- 最終的に topics.json を生成し、制作パイプラインの入力にする
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状
### SP-048 Phase 1 (完了)
- inoreader_client.py: OAuth2認証 + API呼び出し
- topic_extractor.py: RSSアイテム→トピック候補抽出 + JSON出力
- feed_runner.py: CLI (unread/starred/folder等のフィルタ)
- 61テスト全緑

### SP-048 Phase 2 (未着手)
- パイプライン連携: 抽出トピック → research_cli.py の入力として接続
- バッチ処理: 複数トピックの一括処理
- フィルタリング: 重複トピック除外、品質スコアによるランク付け
- 実API疎通: InoReaderの実アカウントでのテスト

## 作業手順
1. docs/DESIGN_FOUNDATIONS.md を読む
2. docs/spec_feed_integration.md (SP-048) を読む
3. src/feed/ の全ファイルを確認
4. InoReader開発者アカウントでOAuth設定
5. 実APIでの動作確認
6. research_cli.py との接続実装
7. バッチ処理・重複除外の実装

## 成果物
- SP-048 Phase 2 実装
- 実API疎通テスト結果
- パイプライン連携テスト追加
- SP-048 pct 100% への更新

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/spec_feed_integration.md
- src/feed/feed_runner.py
- src/feed/inoreader_client.py
- src/feed/topic_extractor.py
- scripts/research_cli.py
- tests/test_feed_runner.py
- tests/test_inoreader_client.py
- tests/test_topic_extractor.py
