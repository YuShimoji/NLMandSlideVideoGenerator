# 初回 YouTube 公開チェックリスト

最終更新: 2026-03-18
目的: パイプライン全体を1本の動画で通しで実行し、初回 YouTube 公開を達成する

---

## 前提条件

- [x] Python 1182 テスト PASS
- [x] SP-035 preflight 36 PASS / 0 FAIL
- [x] SP-038 upload テスト 45 PASS (mock モード)
- [x] API キー設定済み: GEMINI, PEXELS, PIXABAY
- [ ] ffmpeg インストール済み (`ffmpeg -version`)
- [ ] YMM4 最新版インストール済み
- [ ] NLMSlidePlugin を YMM4 プラグインフォルダに配置済み

---

## Phase A: Python 自動パイプライン (2-5分)

### Step 1: トピック選定 + CSV 生成

```powershell
.\venv\Scripts\Activate.ps1
python scripts/research_cli.py pipeline --topic "<テーマ>" --auto-images --duration 300
```

確認項目:
- [ ] `output_csv/` に 4列 CSV が生成された
- [ ] `output_csv/metadata.json` が生成された
- [ ] 画像が `data/images/` に取得された (stock or AI or slide)
- [ ] パイプライン完了サマリーにフォールバック WARNING がないか確認

### Step 2: CSV プレビュー確認

```powershell
# CSV の中身を確認 (speaker, text, image_path, animation_type)
python -c "import csv; [print(r) for r in csv.reader(open('output_csv/timeline.csv', encoding='utf-8'))]"
```

- [ ] 全行に image_path が設定されている
- [ ] animation_type が 8種のいずれか

---

## Phase B: YMM4 レンダリング (30-120分)

### Step 3: YMM4 CSVインポート

1. [ ] YMM4 を起動
2. [ ] NLMSlidePlugin → 「CSVインポート」を選択
3. [ ] 生成された CSV ファイルを指定
4. [ ] 「ボイス自動生成」チェックボックスを ON
5. [ ] インポート実行

### Step 4: タイムライン確認

- [ ] AudioItem (音声) が全セグメントに配置されている
- [ ] TextItem (字幕) が話者ごとに色分けされている
- [ ] ImageItem (背景画像) が配置されている
- [ ] アニメーション (Ken Burns / zoom / pan) が反映されている
- [ ] BGM テンプレートが適用されている (style_template.json)

### Step 5: レンダリング

1. [ ] プレビュー再生で最初の30秒を確認
2. [ ] 「動画出力」→ MP4 形式で保存
3. [ ] レンダリング完了まで待機

---

## Phase C: 後処理 + YouTube 公開 (5-10分)

### Step 6: MP4 品質検証

```powershell
python scripts/research_cli.py verify <mp4ファイルパス> --expected-duration 300
```

- [ ] 解像度 OK (1920x1080)
- [ ] コーデック OK (H.264 + AAC)
- [ ] 再生時間が想定範囲内
- [ ] CRITICAL 失敗なし

### Step 7: OAuth 取得 (初回のみ)

```powershell
# Google Cloud Console で OAuth クライアント ID を作成済みであること
# google_client_secret.json をプロジェクトルートに配置済みであること
python scripts/google_auth_setup.py
```

- [ ] ブラウザで Google ログイン + 4 スコープ同意
- [ ] `token.json` が生成された

### Step 8: YouTube アップロード

```powershell
python scripts/research_cli.py upload \
  --video <mp4ファイルパス> \
  --metadata output_csv/metadata.json \
  --privacy private
```

- [ ] 品質ゲート PASS (SP-039 自動実行)
- [ ] アップロード開始 (プログレスバー表示)
- [ ] Video ID / URL が出力された

### Step 9: YouTube Studio 確認

- [ ] YouTube Studio で動画が表示される
- [ ] タイトル・説明文が正しい
- [ ] タグ・チャプターが反映されている
- [ ] サムネイルが設定されている (2MB 以下の場合)
- [ ] 処理完了後、再生して映像・音声・字幕を確認

---

## 完了判定

以下がすべて OK なら「初回公開」スライス成立:

1. Phase A で CSV が自動生成された
2. Phase B で YMM4 がエラーなくレンダリングした
3. Phase C で YouTube にアップロードされ、動画が再生可能

---

## 発見事項の記録

Phase A → B → C の通し実行で見つかった問題:

| # | フェーズ | 問題 | 深刻度 | 対応 |
|---|---------|------|--------|------|
|   |         |      |        |      |

Phase B の手動操作時間の実測:

| ステップ | 実測時間 | 備考 |
|---------|---------|------|
| CSVインポート |  |  |
| プレビュー確認 |  |  |
| レンダリング |  |  |
