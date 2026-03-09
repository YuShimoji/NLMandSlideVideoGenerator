# Web資料収集 + NLM台本調整 ワークフロー設計

Updated: 2026-02-28T16:50:00+09:00
Source: TASK_016

## 目的

- Webから適切な資料を収集し、動画制作に使える素材パッケージを構成する
- NLMのたたき台ラジオスクリプトと収集資料の差分を比較し、修正候補と採否を管理する
- 動画生成パイプライン（CSV+WAV）とは完全に分離する

---

## 全体フロー

```
[Step 1]  トピック定義 + 検索条件設定
    ↓
[Step 2]  Web資料収集 (SourceCollector 拡張)
    ↓
[Step 3]  収集結果の保存 + スコアリング
    ↓
[Step 4]  NLMたたき台スクリプト入力
    ↓
[Step 5]  台本 ← → 資料 の差分分析
    ↓
[Step 6]  人手レビュー + 採否判断
    ↓
[Step 7]  確定台本 → CSV 出力
    ↓
[既存] CSV + WAV → 動画パイプライン
```

---

## Step 1: トピック定義 + 検索条件

### 入力スキーマ

```json
{
  "topic": "量子コンピュータの最新動向2026",
  "search_queries": [
    "量子コンピュータ 2026 最新",
    "quantum computing breakthrough 2026"
  ],
  "seed_urls": [
    "https://example.com/quantum-2026"
  ],
  "exclude_domains": ["example-spam.com"],
  "preferred_sources": ["academic", "news"],
  "max_sources": 15,
  "language": "ja"
}
```

### 手動レビュー点
- 検索クエリが適切か
- 除外ドメインが漏れていないか

---

## Step 2: Web資料収集

既存の `src/notebook_lm/source_collector.py` の `SourceCollector._process_url()` を基盤にする。

### 拡張ポイント

| 現状 | 拡張 |
|------|------|
| `_search_sources()` はスタブ | 検索API（Google Custom Search/Bing）を追加 |
| URL処理のみ | URL + 検索クエリの両方を受け付け |
| `requests` + `BeautifulSoup` | そのまま維持（静的HTMLで十分） |
| スコアリングはキーワードベース | 出典信頼度のドメインホワイトリスト拡充 |

### 出力: SourceInfo リスト

既存の `SourceInfo` データモデルをそのまま使う:

```python
@dataclass
class SourceInfo:
    url: str
    title: str
    content_preview: str   # 先頭500文字程度
    relevance_score: float # 0-1
    reliability_score: float  # 0-1
    source_type: str       # "news", "academic", "blog", "article"
```

---

## Step 3: 収集結果の保存

### 保存形式: ResearchPackage (JSON)

```json
{
  "package_id": "rp_20260228_quantum",
  "topic": "量子コンピュータの最新動向2026",
  "created_at": "2026-02-28T17:00:00+09:00",
  "sources": [
    {
      "url": "https://example.com/article1",
      "title": "量子コンピュータ、2026年の進化",
      "content_preview": "...",
      "relevance_score": 0.85,
      "reliability_score": 0.9,
      "source_type": "news",
      "adoption_status": "pending",
      "adoption_reason": "",
      "key_claims": [
        "IBM が 1000量子ビットプロセッサを発表",
        "エラー訂正率が前年比50%改善"
      ]
    }
  ],
  "summary": "...(AI生成の要約)",
  "review_status": "pending"
}
```

### 保存先

```
data/research/
├── rp_20260228_quantum/
│   ├── package.json          (ResearchPackage)
│   ├── raw_html/             (取得ページのキャッシュ)
│   │   ├── source_001.html
│   │   └── source_002.html
│   └── screenshots/          (必要に応じてOGP画像等)
```

---

## Step 4: NLMたたき台スクリプト入力

### 入力形式

NLMのたたき台は以下のいずれかで受け取る:

1. **テキストファイル** (`.txt`) — NLM出力の生テキスト
2. **CSV** — 既にCSV形式に整形済みの台本
3. **JSON** — Gemini生成のスクリプトJSON

### 内部正規化スキーマ

```json
{
  "segments": [
    {
      "index": 1,
      "speaker": "Host1",
      "text": "今日は量子コンピュータについて話しましょう",
      "source_refs": [],
      "confidence": "unverified"
    },
    {
      "index": 2,
      "speaker": "Host2",
      "text": "IBMが1000量子ビットを達成したそうですね",
      "source_refs": [],
      "confidence": "unverified"
    }
  ]
}
```

---

## Step 5: 差分分析

### 分析ルール

| チェック項目 | 分類 | 判定 |
|-------------|------|------|
| 台本の主張が資料で裏付けられる | supported | 自動 OK |
| 台本の主張が資料に見当たらない | orphaned | 要確認 |
| 資料にあるが台本にない重要事実 | missing | 追加候補 |
| 台本の数値が資料と不一致 | conflict | 要修正 |

### 出力: AlignmentReport (JSON)

```json
{
  "report_id": "ar_20260228_quantum",
  "package_id": "rp_20260228_quantum",
  "analysis": [
    {
      "segment_index": 2,
      "text": "IBMが1000量子ビットを達成したそうですね",
      "status": "supported",
      "matched_source": "https://example.com/article1",
      "matched_claim": "IBM が 1000量子ビットプロセッサを発表",
      "suggestion": null
    },
    {
      "segment_index": 5,
      "text": "Google も同じ技術を使っています",
      "status": "orphaned",
      "matched_source": null,
      "matched_claim": null,
      "suggestion": "出典不明。削除するか、根拠を追加してください"
    }
  ],
  "summary": {
    "total_segments": 20,
    "supported": 15,
    "orphaned": 3,
    "missing": 1,
    "conflict": 1
  }
}
```

### 分析手法

- **Phase 1（現実的）**: キーワード/フレーズ一致 + Gemini による要約比較
  - 各セグメントから主張キーワードを抽出
  - ResearchPackage の `key_claims` とマッチング
  - マッチしないセグメントを orphaned としてフラグ
- **Phase 2（将来）**: 埋め込みベクトルによる意味類似度比較

---

## Step 6: 人手レビュー + 採否判断

### レビューUI（CLIまたはWeb）

```
=== AlignmentReport: ar_20260228_quantum ===

[SUPPORTED] Seg#2: IBMが1000量子ビットを達成したそうですね
  → 出典: https://example.com/article1
  → OK

[ORPHANED] Seg#5: Google も同じ技術を使っています
  → 出典なし
  → [Accept] [Reject] [Edit] ?

[MISSING] 資料にあるが台本にない:
  → "エラー訂正率が前年比50%改善" (from article1)
  → [Add to script] [Skip] ?

[CONFLICT] Seg#8: 処理速度は100倍
  → 資料では "処理速度は10倍" (from article2)
  → [Use source value] [Keep script value] [Edit] ?
```

### 手動レビュー点
- orphaned セグメントの採否
- conflict セグメントの修正
- missing 事実の追加判断
- 資料の `adoption_status` 更新

---

## Step 7: 確定台本 → CSV 出力

レビュー完了後、確定した台本を CSV に変換:

```csv
Host1,今日は量子コンピュータについて話しましょう
Host2,IBMが1000量子ビットプロセッサを発表したそうですね
Host1,それだけでなく、エラー訂正率も前年比50%改善されました
```

この CSV を Web UI の `CSV Pipeline` ページにそのまま渡す。

---

## 責務境界

| パイプライン | 責務 | 入力 | 出力 |
|-------------|------|------|------|
| 資料収集 | 根拠と整合性 | トピック + 検索条件 | ResearchPackage |
| 台本調整 | 主張の検証 + 修正 | NLMたたき台 + ResearchPackage | 確定CSV |
| 動画生成 | 見た目と出力安定性 | CSV + WAV | MP4 + SRT |

- 資料収集は動画の見た目に関知しない
- 動画生成は資料の正しさに関知しない
- 台本調整は両者をつなぐが、どちらの実装にも依存しない

---

## 既存コードとの接続

| 既存 | 用途 | 変更 |
|------|------|------|
| `src/notebook_lm/source_collector.py` | Web取得の基盤 | `_search_sources()` を実API化 |
| `SourceInfo` | 資料データモデル | `adoption_status`, `key_claims` を追加 |
| `src/notebook_lm/gemini_integration.py` | 差分分析のAI部分 | 新メソッド追加（diff_analyze） |
| `IScriptProvider` | 台本入力の抽象 | 変更なし（消費側として利用） |
| `IContentAdapter` | フォーマット正規化 | 変更なし（NLMたたき台の正規化に利用） |
| `config/settings.py` | 設定 | `RESEARCH_SETTINGS` を追加 |

---

## 次フェーズへの実装タスク分解

### Phase 1: 基盤（2-3日）
- [x] `data/research/` ディレクトリ構造の作成
- [x] `ResearchPackage`, `AlignmentReport` のデータモデル定義
- [x] `SourceCollector._search_sources()` のGoogle Custom Search実装
- [x] CLI でのリサーチ実行コマンド作成

### Phase 2: 差分分析（2-3日）
- [x] キーワードベースの claims 抽出
- [ ] Gemini を使った要約比較
- [x] AlignmentReport の生成ロジック

### Phase 3: レビューUI（2-3日）
- [ ] CLI での採否判断フロー
- [x] Web UI での差分表示 + 編集
- [x] 確定CSV のエクスポート

### Phase 4: 統合テスト
- [ ] サンプルトピックでの End-to-End テスト
- [ ] 既存 CSV パイプラインとの結合確認
