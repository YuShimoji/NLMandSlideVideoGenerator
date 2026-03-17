# バッチ制作キュー仕様 (SP-040)

**最終更新**: 2026-03-17
**ステータス**: draft

---

## 1. 目的

複数トピックをキューに積み、順次パイプライン実行することで「一晩3本ペース」の制作を実現する。

### 1.1 現状 (As-Is)

- `research_cli.py pipeline` は1トピックずつ手動実行
- 複数本制作する場合、毎回CLIを手打ち
- トピック間でAPIクォータ（Gemini 20req/day, Pexels 200req/h）の管理が人手

### 1.2 目標 (To-Be)

```
[手動] topics.json (3-5トピック) を作成
    ↓
[自動] research_cli.py batch --topics topics.json
    ↓
[自動] トピック1: collect → script → csv → YMM4プロジェクト
    ↓
[自動] トピック2: collect → script → csv → YMM4プロジェクト
    ↓
[自動] トピック3: collect → script → csv → YMM4プロジェクト
    ↓
[手動] YMM4で各プロジェクトをインポート → レンダリング
```

---

## 2. 入力フォーマット

### topics.json

```json
{
  "batch_name": "2026-03-17_evening",
  "defaults": {
    "style": "news",
    "duration": 1800,
    "auto_images": true,
    "auto_review": true,
    "speaker_map": {"Host1": "れいむ", "Host2": "まりさ"}
  },
  "topics": [
    {
      "topic": "量子コンピュータの最新動向",
      "seed_urls": ["https://example.com/quantum"]
    },
    {
      "topic": "AI規制法案の動向",
      "duration": 2400,
      "style": "educational"
    },
    {
      "topic": "宇宙開発2026年の展望"
    }
  ]
}
```

- `defaults`: 全トピック共通のパラメータ
- 各トピックで個別にオーバーライド可能
- `seed_urls` は任意（省略時はGoogle Custom Search APIのみ）

---

## 3. 実装計画

### Phase 1: バッチ実行基盤

| 項目 | 内容 |
|------|------|
| 対象 | `scripts/research_cli.py` に `batch` サブコマンド追加 |
| 処理 | topics.jsonを読み込み、各トピックに対して `run_pipeline()` を順次実行 |
| 出力 | `output_batch/{batch_name}/topic_1/`, `topic_2/`, ... |
| エラーハンドリング | 1トピック失敗時に次トピックへ続行。失敗トピックをレポート |
| クォータ管理 | トピック間に待機時間を挿入（API制限回避） |

### Phase 2: 進捗管理

| 項目 | 内容 |
|------|------|
| SP-034連携 | PipelineState をバッチ単位で管理。`--resume` でバッチ途中から再開 |
| ログ | バッチ実行結果をJSON出力 (`batch_result.json`) |

---

## 4. クォータ管理戦略

| API | 制限 | 3本制作時の消費目安 | 対策 |
|-----|------|-------------------|------|
| Gemini | 20 req/day | 3-6 req (台本+分類+キーワード) | フォールバックチェーン |
| Pexels | 200 req/h | 30-90 req (ストック画像検索) | トピック間にインターバル |
| Pixabay | 5000 req/h | フォールバックのみ | 十分 |
| Google Custom Search | 100 req/day | 3-9 req (ソース収集) | 十分 |

---

## 5. 品質軸との対応

| 品質軸 | SP-040の貢献 |
|--------|-------------|
| 制作スピード | 3本を一括実行。手動CLIの繰り返しを排除 |
| 一貫性/再現性 | 同一defaults設定で全トピックが同一品質 |
