# SP-048: InoReader/RSS フィード連携

## 概要

InoReader API を通じて RSS フィードから動画トピック候補を自動取得し、
パイプライン互換の JSON + 人間レビュー用レポートとして出力する。

## 動機

- 週次バッチ制作 (週1本+) において、トピック選定が手動ボトルネック
- InoReader で日常的に購読しているフィードから、動画化候補を自動抽出したい
- 取得したURLをそのまま NotebookLM のソースとして渡すことで、台本品質も向上する

## アーキテクチャ

```
InoReader API
    ↓ (OAuth 2.0 + App ID/Key)
InoreaderClient (src/feed/inoreader_client.py)
    ↓ (記事リスト)
TopicExtractor (src/feed/topic_extractor.py)
    ↓ (フィルタリング + スコアリング)
FeedRunner (src/feed/feed_runner.py)
    ↓
output/feed/
  ├── topics.json          # パイプライン互換形式
  └── feed_report.md       # 人間レビュー用 Markdown
```

## モジュール構成

### src/feed/__init__.py
パッケージ初期化。

### src/feed/inoreader_client.py
InoReader API クライアント。

**認証**:
- App ID + App Key (HTTPヘッダー)
- OAuth 2.0 Bearer トークン
- 環境変数: `INOREADER_APP_ID`, `INOREADER_APP_KEY`, `INOREADER_TOKEN`

**主要メソッド**:
- `get_subscriptions()` → サブスクリプション一覧
- `get_stream_contents(stream_id, count, exclude_read)` → 記事ストリーム
- `get_unread_articles(count, folder)` → 未読記事取得 (ショートカット)
- `get_folder_articles(folder, count)` → フォルダ別記事取得

**レート制限対応**:
- レスポンスヘッダー `X-Reader-Zone1-Usage` / `X-Reader-Zone1-Limit` を監視
- 制限到達時は警告ログ

### src/feed/topic_extractor.py
記事からトピック候補を抽出。

**処理**:
1. 記事タイトル + URL + 公開日 + ソース名を構造化
2. 重複URL排除
3. 鮮度フィルタ (デフォルト: 7日以内)
4. パイプライン互換形式 `{topic, urls, source, published}` に変換

**出力**:
- `topics.json`: パイプライン入力用。各エントリは `{"topic": str, "urls": [str]}`
- `feed_report.md`: Markdown テーブル形式の一覧。タイトル、ソース、公開日、URL

### src/feed/feed_runner.py
CLI エントリポイント。

```bash
# 未読記事からトピック取得
python -m src.feed.feed_runner --unread --count 50

# 特定フォルダからトピック取得
python -m src.feed.feed_runner --folder "Tech News" --count 30

# 出力先指定
python -m src.feed.feed_runner --unread --output ./output/feed/

# 鮮度フィルタ指定 (日数)
python -m src.feed.feed_runner --unread --days 3
```

## 設定

### 環境変数 (.env)
```
INOREADER_APP_ID=your_app_id
INOREADER_APP_KEY=your_app_key
INOREADER_TOKEN=your_oauth_token
```

### config/settings.py 追加
```python
FEED_SETTINGS = {
    "default_count": 50,
    "freshness_days": 7,
    "output_dir": "output/feed",
}
```

## API エンドポイント

| 用途 | エンドポイント |
|------|---------------|
| サブスクリプション一覧 | `GET /reader/api/0/subscription/list` |
| 記事ストリーム | `GET /reader/api/0/stream/contents/{stream_id}` |
| 未読記事 | stream_id=`user/-/state/com.google/reading-list` + `xt=user/-/state/com.google/read` |
| フォルダ別 | stream_id=`user/-/label/{folder_name}` |

## レート制限

- Zone 1: 100リクエスト/日 (読み取り系)
- Zone 2: 100リクエスト/日 (書き込み系、本機能では未使用)
- レスポンスヘッダーで残量監視

## テスト方針

- `tests/test_inoreader_client.py`: API クライアントのユニットテスト (モックHTTP)
- `tests/test_topic_extractor.py`: 抽出ロジックのユニットテスト
- `tests/test_feed_runner.py`: CLI統合テスト (モックAPI)
- 実API疎通は手動テスト手順書で対応

## 出力例

### topics.json
```json
[
  {
    "topic": "Google DeepMind、Gemini 2.5の推論能力を大幅強化",
    "urls": ["https://example.com/article1"],
    "source": "TechCrunch",
    "published": "2026-03-21T10:00:00Z"
  }
]
```

### feed_report.md
```markdown
# Feed Report (2026-03-21)

取得件数: 15件 | ソース: 5フィード | 期間: 直近7日

| # | トピック | ソース | 公開日 | URL |
|---|---------|--------|--------|-----|
| 1 | Google DeepMind... | TechCrunch | 03-21 | [link](...) |
```

## Phase 2: パイプライン自動連携 (SP-048 Phase 2)

### 概要
フィードトピックをバッチキュー (SP-040) 互換形式に自動変換し、
`research_cli.py batch` で直接実行可能にする。

### 追加モジュール

#### topic_extractor.py 追加関数
- `convert_to_batch_format(topics, batch_name, defaults)` → バッチ互換辞書
- `save_batch_json(topics, output_dir, batch_name, defaults)` → `batch_topics.json` 保存

#### feed_runner.py 追加オプション
- `--batch` — バッチ互換形式 `batch_topics.json` も出力
- `--batch-name` — バッチ名指定 (デフォルト: feed_batch)

#### research_cli.py 追加サブコマンド
- `feed` — InoReaderフィード → トピック取得 → バッチ互換出力を一気通貫実行

### 使用例

```bash
# フィード取得 → バッチ互換出力 (デフォルト)
python scripts/research_cli.py feed --unread --count 50

# フォルダ指定 + カスタムバッチ名
python scripts/research_cli.py feed --folder "Tech News" --batch-name "tech_news"

# バッチ実行 (フィード出力をそのまま投入)
python scripts/research_cli.py batch --topics output/feed/batch_topics.json
```

### 出力形式 (batch_topics.json)
```json
{
  "batch_name": "feed_batch",
  "defaults": {
    "style": "news",
    "duration": 1800,
    "auto_images": true,
    "auto_review": true
  },
  "topics": [
    {
      "topic": "Google DeepMind、Gemini 2.5の推論能力を大幅強化",
      "seed_urls": ["https://example.com/article1"],
      "_source": "TechCrunch",
      "_published": "2026-03-21T10:00:00Z"
    }
  ]
}
```

## ステータス

- Phase 1: InoReader クライアント + トピック抽出 + CLI + テスト (完了)
- Phase 2: バッチキュー連携 + CLI feed サブコマンド (完了)
- Phase 3 (将来): スコアリング、NotebookLM直接投入、トピック重複検出
