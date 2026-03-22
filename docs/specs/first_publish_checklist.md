# 初回 YouTube 公開チェックリスト

最終更新: 2026-03-22
目的: パイプライン全体を1本の動画で通しで実行し、初回 YouTube 公開を達成する
準拠: SP-050 E2E ワークフロー仕様 / DESIGN_FOUNDATIONS.md Section 0

---

## 前提条件

- [x] Python 1346 テスト PASS
- [x] SP-035 preflight 36 PASS / 0 FAIL
- [x] SP-038 upload テスト 45 PASS (mock モード)
- [x] API キー設定済み: GEMINI, PEXELS, PIXABAY
- [ ] ffmpeg インストール済み (`ffmpeg -version`)
- [ ] YMM4 最新版インストール済み
- [ ] NLMSlidePlugin を YMM4 プラグインフォルダに配置済み
- [ ] NotebookLM アカウント利用可能

---

## Phase 0: トピック選定 + ソース準備 (人間)

> SP-050 Phase 0 対応

### Step 0-1: トピック選定

- [ ] InoReader/RSS または手動でテーマを決定
- [ ] 必要なソース (URL/テキスト/PDF) を収集

### Step 0-2: NotebookLM ソース投入

- [ ] NotebookLM (https://notebooklm.google.com/) にアクセス
- [ ] ソース資料をアップロード
- [ ] ノートブックにソースが正しく読み込まれたことを確認

---

## Phase 1: NotebookLM Audio Overview 生成 (人間 + NotebookLM)

> SP-050 Phase 1 対応

### Step 1-1: Audio Overview 生成

- [ ] NotebookLM で「Audio Overview」を生成
- [ ] 音声ファイルをダウンロード
- [ ] 音声の内容・テンポを軽く確認

---

## Phase 2: NotebookLM テキスト化 (人間 + NotebookLM)

> SP-050 Phase 2 対応

### Step 2-1: 音声をテキスト化

- [ ] NotebookLM に音声ファイルを再投入
- [ ] テキスト化 (文字起こし) を実行
- [ ] テキストをコピーしてファイルとして保存 (`data/topics/{topic_id}/transcript.txt`)
- [ ] 明らかな誤字・誤認識があれば手動修正

---

## Phase 3: 台本構造化 + CSV 生成 (Python 自動)

> SP-050 Phase 3-4 対応

### Step 3-1: Gemini 構造化 + CSV 自動生成

```powershell
.\venv\Scripts\Activate.ps1
python scripts/research_cli.py pipeline --topic "<テーマ>" --auto-images --duration 300
```

確認項目:
- [ ] `output_csv/` に 4列 CSV が生成された
- [ ] `output_csv/metadata.json` が生成された
- [ ] 画像が `data/images/` に取得された (stock or AI or slide)
- [ ] パイプライン完了サマリーにフォールバック WARNING がないか確認

### Step 3-2: CSV プレビュー確認

```powershell
python -c "import csv; [print(r) for r in csv.reader(open('output_csv/timeline.csv', encoding='utf-8'))]"
```

- [ ] 全行に image_path が設定されている
- [ ] animation_type が 8種のいずれか

---

## Phase 4: YMM4 レンダリング (人間 + YMM4)

> SP-050 Phase 6 対応

### Step 4-1: YMM4 CSVインポート

1. [ ] YMM4 を起動
2. [ ] NLMSlidePlugin -> 「CSVインポート」を選択
3. [ ] 生成された CSV ファイルを指定
4. [ ] 「ボイス自動生成」チェックボックスを ON
5. [ ] インポート実行

### Step 4-2: タイムライン確認

- [ ] AudioItem (音声) が全セグメントに配置されている
- [ ] TextItem (字幕) が話者ごとに色分けされている
- [ ] ImageItem (背景画像) が配置されている
- [ ] アニメーション (Ken Burns / zoom / pan) が反映されている
- [ ] BGM テンプレートが適用されている (style_template.json)

### Step 4-3: レンダリング

1. [ ] プレビュー再生で最初の30秒を確認
2. [ ] 「動画出力」-> MP4 形式で保存
3. [ ] レンダリング完了まで待機

---

## Phase 5: 後処理 + YouTube 公開 (Python + 人間)

> SP-050 Phase 7 対応

### Step 5-1: MP4 品質検証

```powershell
python scripts/research_cli.py verify <mp4ファイルパス> --expected-duration 300
```

- [ ] 解像度 OK (1920x1080)
- [ ] コーデック OK (H.264 + AAC)
- [ ] 再生時間が想定範囲内
- [ ] CRITICAL 失敗なし

### Step 5-2: OAuth 取得 (初回のみ)

```powershell
# Google Cloud Console で OAuth クライアント ID を作成済みであること
# google_client_secret.json をプロジェクトルートに配置済みであること
python scripts/google_auth_setup.py
```

- [ ] ブラウザで Google ログイン + 4 スコープ同意
- [ ] `token.json` が生成された

### Step 5-3: YouTube アップロード

```powershell
python scripts/research_cli.py upload \
  --video <mp4ファイルパス> \
  --metadata output_csv/metadata.json \
  --privacy private
```

- [ ] 品質ゲート PASS (SP-039 自動実行)
- [ ] アップロード開始 (プログレスバー表示)
- [ ] Video ID / URL が出力された

### Step 5-4: YouTube Studio 確認

- [ ] YouTube Studio で動画が表示される
- [ ] タイトル・説明文が正しい
- [ ] タグ・チャプターが反映されている
- [ ] サムネイルが設定されている (2MB 以下の場合)
- [ ] 処理完了後、再生して映像・音声・字幕を確認

---

## 完了判定

以下がすべて OK なら「初回公開」スライス成立:

1. Phase 0-2 で NotebookLM から台本テキストが取得できた
2. Phase 3 で CSV が自動生成された
3. Phase 4 で YMM4 がエラーなくレンダリングした
4. Phase 5 で YouTube にアップロードされ、動画が再生可能

---

## 発見事項の記録

Phase 0-5 の通し実行で見つかった問題:

| # | フェーズ | 問題 | 深刻度 | 対応 |
|---|---------|------|--------|------|
|   |         |      |        |      |

各フェーズの実測時間:

| フェーズ | ステップ | 実測時間 | 備考 |
|---------|---------|---------|------|
| Phase 0 | トピック選定 |  |  |
| Phase 1 | Audio Overview 生成 |  |  |
| Phase 2 | テキスト化 |  |  |
| Phase 3 | CSV 生成 |  |  |
| Phase 4 | CSVインポート |  |  |
| Phase 4 | プレビュー確認 |  |  |
| Phase 4 | レンダリング |  |  |
| Phase 5 | MP4検証+アップロード |  |  |
