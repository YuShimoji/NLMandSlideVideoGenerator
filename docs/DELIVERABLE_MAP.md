# DELIVERABLE MAP (成果物駆動マップ)

Updated: 2026-03-23
Authority: **全SPの優先順位はこの文書で定義する。** project-context.md の CURRENT DEVELOPMENT AXIS と同等権限。
準拠: DESIGN_FOUNDATIONS.md (三層モデル + レガシー境界)

---

## 設計原則

**成果物駆動開発 (Deliverable-Driven Development)**

このプロジェクトは「仕様を書く」ことではなく「動画を出す」ことが目的である。
53仕様・1318テスト・実動画ゼロという状態を二度と繰り返さない。

原則:
1. 全ての開発は「何が動くようになるか」で評価する
2. 仕様は成果物を定義するために書く。仕様のための仕様は書かない
3. テストは成果物の品質を保証するために書く。カバレッジのためのテストは書かない
4. 縦割りスライス: 各スライスは「動く成果物」で閉じる
5. Worker割当は成果物スライス単位。SPリストで割り当てない
6. 完了判定は「SPが何%完了」ではなく「成果物が動くか」

---

## 最終成果物

**YouTube長尺解説動画を半自動生産するパイプライン。**

成果物の構成要素:
1. **動画本体 (MP4)** — 解説音声 + 字幕 + 背景画像/スライド + オーバーレイ
2. **サムネイル** — YouTube上でクリックされるための画像
3. **メタデータ** — タイトル / 説明文 / タグ
4. **公開** — YouTube にアップロードされ視聴可能

---

## 縦割りスライス (Vertical Slices)

```
VS-1 (初動画) ──> VS-2 (公開) ──> VS-3 (品質) ──> VS-4 (サムネ) ──> VS-5 (自動化)
 全てここから      V1のMP4が入力   V1の実映像で判断  V3のデザイン準拠   手動が安定してから
```

### VS-1: First Video (初動画) — 最優先 / 現在のスライス

**完了条件**: NLM音声からパイプラインを通してMP4ファイルが生成される。

| # | 作業 | 担当 | 状態 | ブロッカー |
|---|------|------|------|-----------|
| 1 | トピック選定 + NLM ソース投入 | 人間 | 未着手 | なし |
| 2 | NLM Audio Overview 生成 + DL | 人間 + NLM | 未着手 | なし |
| 3 | `research_cli.py pipeline --audio` 実行 | Python自動 | コード済み | GEMINI_API_KEY |
| 4 | .NET 10 SDK インストール + plugin ビルド | 人間 | 未着手 | .NET 10 SDK |
| 5 | YMM4 CSV インポート + レンダリング | 人間 + YMM4 | 未着手 | #4 完了 |
| 6 | MP4 再生確認 | 人間 | 未着手 | #5 完了 |

**AI側の作業は全て完了している。VS-1の残りは全て人間操作。**

関連SP: SP-045(checklist), SP-050(workflow), SP-051(transcription), SP-035(integration test)
不要な作業: サムネイル自動生成、GUI、Playwright自動化、batch production、新規テスト追加

---

### VS-2: YouTube 公開

**完了条件**: VS-1のMP4がYouTubeで視聴可能。

| # | 作業 | 担当 | 状態 | ブロッカー |
|---|------|------|------|-----------|
| 1 | ffmpeg インストール | 人間 | 未着手 | なし |
| 2 | `research_cli.py verify` MP4品質検証 | Python自動 | コード済み | ffmpeg |
| 3 | YouTube 手動アップロード (初回) | 人間 | 未着手 | VS-1完了 |
| 4 | Google OAuth設定 (2本目以降の自動化用) | 人間 | 未着手 | Google Cloud Console |
| 5 | `research_cli.py upload` 自動アップロード | Python自動 | コード済み | OAuth |

関連SP: SP-038, SP-039
初回は手動アップロードでも可 (OAuth不要)。

---

### VS-3: Production Quality (制作品質)

**完了条件**: 2本目以降の動画が一貫した視覚品質で生産できる。

| # | 作業 | 担当 | 状態 | ブロッカー |
|---|------|------|------|-----------|
| 1 | VS-1のMP4を見て品質課題を特定 | 人間 | 未着手 | VS-1完了 |
| 2 | YMM4プロジェクトテンプレート (.ymmp) 作成 | 人間 | 未着手 | #1 |
| 3 | overlay_plan.json の実動画での検証・調整 | 人間 + AI | 未着手 | #1 |
| 4 | style_template.json のバリアント調整 | 人間 + AI | 基盤完成 | #1 |
| 5 | Gemini構造化プロンプトの実音声での調整 | AI | 未着手 | #1 |
| 6 | アニメーション方針確定 | 人間 | 保留 | #1 |

関連SP: SP-052, SP-031, SP-051 Phase 2, SP-047
**VS-1での発見事項が入力になる。VS-1を飛ばしてVS-3に着手しないこと。**

---

### VS-4: Thumbnail (サムネイル)

**完了条件**: 動画ごとにYouTubeクリック率を意識したサムネイルが生成される。

| # | 作業 | 担当 | 状態 | ブロッカー |
|---|------|------|------|-----------|
| 1 | サムネイルYMM4テンプレートを人間がデザイン | 人間 | 未着手 | VS-3完了 |
| 2 | バリエーション生成の検証 | AI | コード済み | #1 |
| 3 | Gemini文言生成の実運用調整 | AI | コード済み | VS-2完了 |

関連SP: SP-037

---

### VS-5: Automation (自動化)

**完了条件**: 週1本ペースで動画が制作できる。

| # | 作業 | 担当 | 状態 | ブロッカー |
|---|------|------|------|-----------|
| 1 | YouTube OAuth 本番取得 | 人間 | 未着手 | VS-2で手動運用した後 |
| 2 | InoReader API 実疎通 | AI | コード済み | InoReader OAuth |
| 3 | Producer GUI (Streamlit) | AI | partial 40% | VS-1〜4安定後 |
| 4 | Batch production の実運用 | 人間 + AI | コード済み | VS-1〜3安定後 |
| 5 | Playwright NLM 半自動化の実用性検証 | AI | partial | VS-1手動操作の摩擦度評価後 |
| 6 | Google Slides API テンプレート | AI | コード済み | Google OAuth + VS-3デザイン方針後 |

関連SP: SP-038, SP-048, SP-053, SP-040, SP-047, IP-001〜005

---

## SP → Deliverable マッピング

| SP | VS-1 | VS-2 | VS-3 | VS-4 | VS-5 | 状態 |
|----|:----:|:----:|:----:|:----:|:----:|------|
| SP-045 | **必須** | | | | | partial 80% (人間操作待ち) |
| SP-050 | **必須** | | | | | partial 95% |
| SP-051 | **必須** | | 調整 | | | partial 90% |
| SP-035 | **必須** | | | | | partial 65% (実機テスト待ち) |
| SP-052 | | | **必須** | | | partial 65% (テンプレは人間) |
| SP-038 | | **必須** | | | 自動化 | partial 95% (OAuth待ち) |
| SP-039 | | **必須** | | | | done |
| SP-037 | | | | **必須** | | partial 85% (テンプレは人間) |
| SP-047 | | | 検証 | | 自動化 | partial 85% |
| SP-048 | | | | | **必須** | partial 80% |
| SP-053 | | | | | **必須** | partial 40% |
| SP-040 | | | | | 運用 | done |
| SP-043 | | | | | 候補 | done |
| SP-042 | | | | | 候補 | done |
| 残37件 | | | | | | done/superseded/legacy |

**partial 11件のうち、VS-1に直接必要なのは4件。うちAI側作業は全て完了。**

---

## 開発の禁止事項

VS-1が完了するまで、以下は着手しない:
- 新規SP追加
- GUI開発 (SP-053 Phase 2+)
- Playwright NLM自動化の拡張
- Google OAuth本番取得
- テンプレート自動生成の高度化
- テストカバレッジ追求
- ドキュメント整備のためのドキュメント整備
- レガシーコードのリファクタリング

例外: VS-1のブロッカー解消に直接必要な修正のみ。

---

## VS-1 完走までの人間アクションリスト

```
1. .NET 10 SDK インストール
2. cd ymm4-plugin && dotnet build NLMSlidePlugin.csproj
3. ビルドしたDLLをYMM4プラグインフォルダに配置
4. 環境変数設定: GEMINI_API_KEY, PEXELS_API_KEY (推奨)
5. NotebookLM でテーマを選びソース3件以上を投入
6. Audio Overview を生成・ダウンロード
7. python scripts/research_cli.py pipeline --topic "テーマ" --audio "audio.mp3" --auto-images --duration 300
8. YMM4起動 → NLMSlidePlugin → CSVインポート → ボイス自動生成ON → 実行
9. プレビュー確認 → MP4レンダリング
10. MP4再生確認 → VS-1完了
```

---

## 統合優先タスク一覧 (2026-03-23 検収済み)

> この一覧は全タスクの優先度を Tier 1-5 で定義する。
> 上位セクションのVS定義と矛盾する場合、VS定義が優先。
> 更新時は実際のspec-index.json / DELIVERABLE_MAP本体と照合すること。

### 全体状況

AI側の実装は全て完了。残りは主に人間操作 (環境構築・手動確認・デザイン判断)。
パイプライン: NotebookLM → 音声 → Gemini構造化 → Python CSV → YMM4 → MP4 → YouTube

### Tier 1: VS-1 初動画完走 (最優先・現在スライス)

| # | タスク | 担当 | 状態 | ブロッカー |
| --- | -------- | ------ | ------ | ----------- |
| 1 | .NET 10 SDK インストール + YMM4プラグインビルド・配置 | 人間 | 未着手 | .NET 10 SDK |
| 2 | 環境変数設定 (GEMINI_API_KEY, PEXELS_API_KEY) | 人間 | 未着手 | なし |
| 3 | トピック選定 + NLM ソース投入 | 人間 | 未着手 | なし |
| 4 | NLM Audio Overview 生成 + DL | 人間+NLM | 未着手 | なし |
| 5 | `research_cli.py pipeline --audio` 実行 | 自動 | コード済み | #2完了 |
| 6 | YMM4 CSV インポート + レンダリング | 人間+YMM4 | 未着手 | #1完了 |
| 7 | MP4 再生確認 | 人間 | 未着手 | #6完了 |

狙い: 1本目のMP4を手元で完成させ、パイプライン全体の実動作を検証する。VS-1が全ての後続作業の前提条件。

### Tier 2: VS-2 YouTube公開

| # | タスク | 担当 | 状態 | ブロッカー |
| --- | -------- | ------ | ------ | ----------- |
| 1 | ffmpeg インストール | 人間 | 未着手 | なし |
| 2 | `research_cli.py verify` MP4品質検証 | 自動 | コード済み | ffmpeg |
| 3 | YouTube 手動アップロード (初回) | 人間 | 未着手 | VS-1完了 |
| 4 | Google OAuth設定 (自動化用) | 人間 | 未着手 | Google Cloud Console |
| 5 | `research_cli.py upload` 自動アップロード | 自動 | コード済み | #4完了 |

狙い: 初公開を達成し、YouTube側の制約 (エンコード・メタデータ) を実地検証する。

### Tier 3: VS-3 制作品質確立

| # | タスク | 担当 | 状態 | ブロッカー |
| --- | -------- | ------ | ------ | ----------- |
| 1 | VS-1 MP4の品質課題特定 | 人間 | 未着手 | VS-1完了 |
| 2 | YMM4プロジェクトテンプレート (.ymmp) 作成 | 人間 | 未着手 | #1 |
| 3 | overlay_plan.json の調整 | 人間+AI | 未着手 | #1 |
| 4 | style_template.json のバリアント調整 | 人間+AI | 基盤完成 | #1 |
| 5 | Gemini構造化プロンプト調整 | AI | 未着手 | #1 |
| 6 | アニメーション方針確定 | 人間 | 保留(HUMAN_AUTHORITY) | #1 |

狙い: 2本目以降の動画を一貫した視覚品質で制作できる基盤を作る。

### Tier 4: VS-4 サムネイル + VS-5 自動化

| スライス | 主要タスク | 状態 | ブロッカー |
| --------- | ----------- | ------ | ----------- |
| VS-4 サムネイル | YMM4テンプレートデザイン + Gemini文言生成調整 | 未着手 | VS-3完了 |
| VS-5 自動化 | YouTube OAuth本番 / InoReader API実疎通 / Producer GUI Phase 2+ | partial | VS-1〜4安定後 |

狙い: 週1本ペースの制作を持続可能にする。

### Tier 5: partial仕様書の残作業

| SP | タイトル | 進捗 | 残タスク |
| ---- | --------- | ------ | --------- |
| SP-035 | Integration Test Checklist | 65% | YMM4実機テスト |
| SP-053 | Producer GUI | 40% | ~~AI評価統合~~ 廃止。バッチ選定UI+Playwright統合 |
| SP-052 | YMM4 Video Quality Template | 65% | テンプレート作成+デザイン方針 |
| SP-045 | First Publish Checklist | 80% | VS-1手順の実行 |
| SP-047 | Video Output Quality Standard | 85% | Phase 4(NLMスライド統合), Phase 5(実API+実ブラウザ) |
| SP-048 | InoReader/RSS Integration | 80% | 実API疎通 |
| SP-037 | Thumbnail Pipeline | 85% | テンプレート実物作成 |
| SP-051 | Audio Transcription | 90% | 実音声E2E+プロンプト調整 |
| SP-038 | YouTube Publish Pipeline | 95% | 本番OAuth取得 |
| SP-050 | E2E Workflow | 95% | 未決定事項Q1-1/Q6-2確定 |

### 未確定の設計論点 (HUMAN_AUTHORITY待ち)

| 論点 | 関連VS | 判断時期 |
| ------ | -------- | --------- |
| YMM4テンプレート Pattern A-E の優先順 | VS-3 | VS-1完走後 |
| アニメーション方針 | VS-3 | VS-1完走後 |
| サムネイルデザイン | VS-4 | VS-3完了後 |

### 最大の摩擦 (CRITICAL)

| 摩擦 | 影響度 | 対策状況 |
| ------ | -------- | --------- |
| YMM4手動操作が全体の80% | CRITICAL | SDK制限で根本解決困難 |
| レンダリング時間が動画長の2-5倍 | CRITICAL | 就寝時実行で運用回避 |

### 廃止済みレガシー項目

以下は過去の仕様に含まれていたが、現在は廃止。Workerが誤って着手しないこと。

| 項目 | 元SP / ファイル | 廃止理由 | 残存状況 |
| ------ | ------ | --------- | --------- |
| Gemini動画適性スコアリング (AI評価) | SP-053 Phase 2 | トピック選定は人間判断。DESIGN_FOUNDATIONS Section 0準拠 | production_line.py にLEGACYマーク済フィールド残存 (後方互換) |
| TextSlideGenerator (PILスライド生成) | SP-033/SP-041 | Google Slides API移行決定。DESIGN_FOUNDATIONS Section 5 | pipeline_stats.py に text_slide_count=0 フィールド残存 (後方互換) |
| Brave Search リサーチ (SourceCollector) | SP-014/SP-040 | 人間がNLMに直接ソース投入。Decision 2026-03-22 | source_collector.py にSourceInfo再エクスポート残存 (後方互換) |
| Python TTS / 音声合成 | — | YMM4内蔵ゆっくりボイスが唯一の正規経路 | 削除済み |
| MoviePy 動画レンダリング | — | YMM4が唯一のレンダリングエンジン | 削除済み |
| Gemini Imagen (AIImageProvider) | SP-033 | 有料プラン専用/廃止。DESIGN_FOUNDATIONS Section 5 | pipeline_stats.py に ai_image_count=0 フィールド残存 (後方互換) |
