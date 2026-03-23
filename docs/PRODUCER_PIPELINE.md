# 制作者パイプライン全体像

最終更新: 2026-03-23
準拠: DESIGN_FOUNDATIONS.md Section 0 (根本ワークフロー)

---

## 目的

この文書は「制作者が1本の動画を作るために、実際に何をするか」を1枚にまとめる。
52仕様に散在する情報を統合し、各ステップの手動/自動/未実装を明示する。

**対象読者**: 動画制作者 (= プロジェクトオーナー自身)

---

## パイプライン全体フロー

```
Phase 0          Phase 1          Phase 2          Phase 3
トピック選定 --> NLM Audio --> 文字起こし+ --> スライド+
(人間)          Overview        構造化          素材調達
                (人間+NLM)      (自動/半自動)   (自動)

    Phase 4          Phase 5          Phase 6          Phase 7
--> CSV組立 -------> YMM4制作 ------> MP4検証 -------> YouTube公開
    (自動)           (人間+YMM4)      (自動)           (半自動)
```

---

## 各ステップ詳細

### Phase 0: トピック選定 + ソース準備

| 項目 | 内容 |
|------|------|
| 実行者 | **人間** |
| 自動化状態 | **手動** |
| 所要時間目安 | 5-15分 |
| 入力 | ニュース、関心テーマ |
| 出力 | NotebookLM ノートブック (ソース3件以上) |

**やること**:
1. InoReader/RSS、ニュースサイト等でテーマを探す
2. NotebookLM (https://notebooklm.google.com/) で新規ノートブック作成
3. ソース資料をアップロード (URL/PDF/テキスト)

**自動化の可能性**: SP-048 (InoReader API) でトピック候補の自動取得は実装済みだが、最終的なトピック選定は人間の判断が必要。

---

### Phase 1: NotebookLM Audio Overview 生成

| 項目 | 内容 |
|------|------|
| 実行者 | **人間 + NotebookLM** |
| 自動化状態 | **手動** (NotebookLM Web UI 操作) |
| 所要時間目安 | 5-15分 (生成待ち含む) |
| 入力 | Phase 0 のノートブック |
| 出力 | 音声ファイル (MP3/WAV) |

**やること**:
1. NotebookLM で Audio Overview を生成
   - Customize ボタンでフォーカスエリアを指定可能
   - 話者は固定2名 (変更不可)
   - 尺は NLM が自動決定 (目安5-15分)
2. 音声ファイルをダウンロード
3. `data/topics/{topic_id}/audio/` に保存

**自動化の可能性**: NotebookLM Enterprise API (有料) で自動化できる可能性があるが、未検証。現時点では Web UI 手動操作が前提。

---

### Phase 2: 文字起こし + 構造化

| 項目 | 内容 |
|------|------|
| 実行者 | **Python (自動)** |
| 自動化状態 | **自動** (Gemini Audio API) |
| 所要時間目安 | 1-2分 |
| 入力 | Phase 1 の音声ファイル |
| 出力 | 構造化 JSON (speaker, text, key_points) |

**実行コマンド**:
```bash
# 音声ファイルから直接構造化 (SP-051: 1回のAPIコールで文字起こし+構造化)
python scripts/research_cli.py pipeline \
  --topic "テーマ名" \
  --audio data/topics/{topic_id}/audio/overview.mp3
```

**フォールバック** (Gemini Audio API が使えない場合):
```bash
# 手動テキスト投入 (NLMで文字起こし → テキストファイルを指定)
python scripts/research_cli.py pipeline \
  --topic "テーマ名" \
  --transcript data/topics/{topic_id}/transcript/transcript.txt
```

**実装状態**: SP-051 Phase 1 実装済み (AudioTranscriber + CLI + 23テスト)。Phase 2 (E2E自動化) は partial。

**既知の制約**:
- Gemini API: 20 req/day (無料枠)。SP-043 で複数プロバイダー対応済み
- 長尺音声 (30分+) の処理時間は未実測

---

### Phase 3: スライド生成 + 素材調達

| 項目 | 内容 |
|------|------|
| 実行者 | **Python (自動)** |
| 自動化状態 | **部分自動** |
| 所要時間目安 | 2-5分 |
| 入力 | Phase 2 の構造化台本 |
| 出力 | スライド画像 (PNG) + 補助画像 |

**スライド生成**:
- **目標**: Google Slides API テンプレートベース
- **現状**: Google Slides API クライアントは存在するが、テンプレートは未作成。PIL テキストスライド生成は廃止済み
- **フォールバック**: ストック画像のみで進行可能

**素材画像調達** (自動):
- Pexels API → Pixabay API → Wikimedia Commons のフォールバックチェーン
- SP-033 Phase 1-3 完了。8種アニメーション自動割当

**未実装**:
- Google Slides テンプレートの実物作成
- スライドと素材画像の混合配置ロジック

---

### Phase 4: CSV 組立 + バリデーション

| 項目 | 内容 |
|------|------|
| 実行者 | **Python (自動)** |
| 自動化状態 | **自動** |
| 所要時間目安 | < 1分 |
| 入力 | Phase 2 の台本 + Phase 3 の画像 |
| 出力 | timeline.csv (4列) + metadata.json |

**CSV形式**: `speaker, text, image_path, animation_type`

**実行**: Phase 2-4 は `pipeline` コマンドで一気通貫実行される。

**バリデーション** (自動):
- CSV フォーマット検証
- 画像パス存在確認
- セグメント粒度チェック (15-25秒/セグメント)
- speaker 名検証

**実装状態**: SP-032 (CsvAssembler), SP-044 (セグメント尺制御), SP-031 (Pre-Export検証) 全て完了。

---

### Phase 5: YMM4 制作

| 項目 | 内容 |
|------|------|
| 実行者 | **人間 + YMM4** |
| 自動化状態 | **手動** (GUI 操作必須) |
| 所要時間目安 | 5-30分 (操作) + 40-150分 (レンダリング) |
| 入力 | Phase 4 の CSV + 画像 |
| 出力 | MP4 (H.264 + AAC, 1920x1080) |

**やること**:
1. YMM4 起動
2. NLMSlidePlugin → CSV インポート
   - Voice自動生成: チェックボックスON (SP-024)
   - ImageItem自動配置: CSV 3列目から自動 (SP-026)
3. プレビュー再生で最初30秒を確認
4. BGM配置 (style_template.json 参照)
5. 動画出力 → MP4

**目標**: YMM4操作はほぼノータッチ (5分以内)。ただし現時点では未検証。

**自動化の可能性**: YMM4 に CLI モードはない。根本的に GUI 操作が必要。
CSV の品質が高ければ手動調整は最小化できる。

**既知の制約**:
- レンダリング時間: 動画尺の2-5倍 (30分動画 → 60-150分)
- 就寝前にレンダリング開始する運用を推奨

---

### Phase 6: MP4 検証

| 項目 | 内容 |
|------|------|
| 実行者 | **Python (自動)** |
| 自動化状態 | **自動** |
| 所要時間目安 | < 1分 |
| 入力 | Phase 5 の MP4 |
| 出力 | 検証レポート |

**実行コマンド**:
```bash
python scripts/research_cli.py verify output.mp4
```

**検証項目** (SP-039 完了):
- 解像度、コーデック、再生時間、ビットレート等 10項目
- CRITICAL 失敗でアップロード阻止

---

### Phase 7: YouTube 公開

| 項目 | 内容 |
|------|------|
| 実行者 | **Python + 人間** |
| 自動化状態 | **部分自動** (OAuth未整備) |
| 所要時間目安 | 5-10分 |
| 入力 | 検証済み MP4 + metadata.json |
| 出力 | YouTube URL |

**実行コマンド** (実装済みだが本番未接続):
```bash
python scripts/research_cli.py publish output.mp4 \
  --metadata output_csv/metadata.json
```

**実装状態**:
- メタデータ自動生成: 完了 (SP-038 Phase 1-2)
- YouTube Data API v3 resumable upload: 完了 (SP-038 Phase 3-4)
- **本番 OAuth トークン**: 未取得 (手動でGoogle Cloud Consoleで設定が必要)
- サムネイル: YMM4テンプレートベース (SP-037)。テンプレート実物は未作成

**現実的な Phase 7 (初回)**:
1. メタデータ生成 → metadata.json を編集
2. サムネイル → YMM4 or 手動作成
3. YouTube Studio で手動アップロード (OAuth未整備のため)

---

## 自動化状態サマリー

| Phase | 名称 | 自動化 | ブロッカー |
|-------|------|--------|-----------|
| 0 | トピック選定 | 手動 | 人間の判断が必要 |
| 1 | NLM Audio Overview | 手動 | NLM Web UI 操作必須 |
| 2 | 文字起こし+構造化 | **自動** | -- |
| 3 | スライド+素材 | **部分自動** | Google Slides テンプレート未作成 |
| 4 | CSV組立 | **自動** | -- |
| 5 | YMM4制作 | 手動 | YMM4 GUI 操作必須 |
| 6 | MP4検証 | **自動** | -- |
| 7 | YouTube公開 | 部分自動 | OAuth未取得、サムネイルテンプレ未作成 |

**自動化率**: Phase 2, 4, 6 が完全自動。Phase 3, 7 が部分自動。Phase 0, 1, 5 が手動。

---

## 最短で1本作るための最小パス

Google Slides テンプレートや YouTube OAuth がなくても、以下の最小パスで1本作れる:

1. **Phase 0**: テーマ決定 + NLM にソース投入 (5-15分)
2. **Phase 1**: NLM Audio Overview 生成 + ダウンロード (5-15分)
3. **Phase 2**: `pipeline --audio` で構造化 (自動, 1-2分)
4. **Phase 3**: ストック画像のみで進行 (自動, スライドなし) (2-5分)
5. **Phase 4**: CSV 自動生成 (自動, < 1分)
6. **Phase 5**: YMM4 で CSV インポート + レンダリング (5分+レンダリング待ち)
7. **Phase 6**: `verify` で品質確認 (自動, < 1分)
8. **Phase 7**: YouTube Studio で手動アップロード (5-10分)

**推定合計**: 25-50分 (手動作業) + 40-150分 (レンダリング待ち)

---

## 現行コードとのギャップ一覧

| 項目 | 仕様/目標 | 現状 | 影響度 |
|------|----------|------|--------|
| 初回通し実行 | SP-045 | 未実施 | CRITICAL |
| Google Slides テンプレート | SP-047 Phase 4 | テンプレート未作成 | HIGH |
| YouTube OAuth | SP-038 Phase 5 | 未取得 | MEDIUM |
| サムネイルテンプレート | SP-037 Pattern A-E | 実物未作成 | MEDIUM |
| NLM Enterprise API | -- | 未検証 | LOW |
| Phase B 自動化 | -- | YMM4 CLI なし | LOW (構造的制約) |

---

## 関連仕様

- SP-050: E2E ワークフロー仕様 (What)
- SP-045: 初回公開チェックリスト (How)
- SP-053: 制作者GUI (Production Dashboard) — このパイプラインのGUI化
- DESIGN_FOUNDATIONS.md: 三層モデル + 根本ワークフロー
- friction_inventory.md: 摩擦ランキング
