# DELIVERABLE MAP (成果物駆動マップ)

Updated: 2026-03-23
Authority: **全SPの優先順位はこの文書で定義する。** project-context.md の CURRENT DEVELOPMENT AXIS と同等権限。
準拠: DESIGN_FOUNDATIONS.md (三層モデル + レガシー境界)

---

## 設計原則

**成果物駆動開発 (Deliverable-Driven Development)**

このプロジェクトは「仕様を書く」ことではなく「動画を出す」ことが目的である。
53仕様・1316テスト・実動画ゼロという状態を二度と繰り返さない。

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
