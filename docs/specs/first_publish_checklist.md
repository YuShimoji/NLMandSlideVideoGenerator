# 初回 YouTube 公開チェックリスト

SP-045 | Status: partial | 最終更新: 2026-03-22
目的: パイプライン全体を1本の動画で通しで実行し、初回 YouTube 公開を達成する
準拠: SP-050 E2E ワークフロー仕様 / DESIGN_FOUNDATIONS.md Section 0
品質方針: 品質優先。時間目標は参考値であり Go/No-Go 基準にしない (Decision #72, Q-X1)

---

## 前提条件

### 自動検証

```powershell
.\venv\Scripts\Activate.ps1
python -c "import core, notebook_lm, slides, youtube; print('OK: core imports')"
python scripts/research_cli.py pipeline --help  # --transcript オプションが表示されること
```

- [x] Python 1318 テスト PASS (1 skipped)
- [x] SP-035 preflight 36 PASS / 0 FAIL
- [x] SP-038 upload テスト 45 PASS (mock モード)

### 手動確認

- [ ] ffmpeg インストール済み (`ffmpeg -version`)
- [ ] YMM4 最新版インストール済み
- [ ] NLMSlidePlugin を YMM4 プラグインフォルダに配置済み
- [ ] NotebookLM アカウント利用可能 (https://notebooklm.google.com/)

### API キー

- [ ] GEMINI_API_KEY 設定済み (必須)
- [ ] PEXELS_API_KEY 設定済み (推奨。未設定でも Pixabay → Wikimedia フォールバック)
- [ ] PIXABAY_API_KEY 設定済み (推奨)
- [ ] google_client_secret.json (Phase 5 で必要。未取得の場合: `docs/google_api_setup.md` 参照)

---

## Phase 0: トピック選定 + ソース準備 (人間)

> SP-050 Phase 0 対応 | 参考所要時間: 5-15分

### Step 0-1: トピック選定

- [ ] InoReader/RSS、ニュースサイト、または手動でテーマを決定
- [ ] 初回は馴染みのあるテーマを推奨 (パイプライン検証に集中するため)

### Step 0-2: NotebookLM ソース投入

- [ ] NotebookLM (https://notebooklm.google.com/) で新規ノートブック作成
- [ ] ソース資料をアップロード (URL/PDF/テキスト、3件以上推奨)
- [ ] ノートブックにソースが正しく読み込まれたことを確認

### Go/No-Go

- ソース 3件以上が NotebookLM に読み込まれている → Phase 1 へ
- ソースが読み込めない場合 → 別のソース形式 (PDF → テキスト貼り付け等) を試行

---

## Phase 1: NotebookLM Audio Overview 生成 (人間 + NotebookLM)

> SP-050 Phase 1 対応 | 参考所要時間: 5-15分 (生成待ち含む)

### Step 1-1: Audio Overview 生成

- [ ] NotebookLM で「Audio Overview」を生成
- [ ] 「Customize」ボタンでフォーカスエリアを指定 (任意)
  - 指示例: "このトピックの最新動向と実用的な影響に焦点を当ててください"
  - 指示例: "初心者向けに分かりやすく説明してください"
- [ ] 生成完了まで待機 (通常2-5分)
- [ ] 音声を再生し、内容・テンポを軽く確認

### Step 1-2: 音声ファイル保存

- [ ] 音声ファイルをダウンロード
- [ ] `data/topics/{topic_id}/audio/` に保存

### Go/No-Go

- 音声が再生可能 + 内容がソースに基づいている → Phase 2 へ
- Audio Overview 生成失敗 → ソース量の調整 (多すぎ/少なすぎ) or リトライ

### ブロッカー回避パス

- NotebookLM が一時的に利用不可 → 時間を空けてリトライ
- 音声品質が著しく低い → ソースを厳選して再生成

---

## Phase 2: 音声文字起こし + 構造化 (Python 自動 / SP-051)

> SP-050 Phase 2 対応 | 参考所要時間: 1-2分 (自動)

### Step 2-1: 音声から自動構造化 (推奨: --audio)

Phase 1 でダウンロードした音声ファイルを `--audio` で直接投入。
Gemini Audio API が文字起こし + 構造化を1回のAPIコールで実行する。

```powershell
.\venv\Scripts\Activate.ps1

python scripts/research_cli.py pipeline `
  --topic "<テーマ名>" `
  --audio "data/topics/{topic_id}/audio/overview.mp3" `
  --auto-images `
  --duration 300 `
  --save-transcript  # 中間テキストを保存したい場合
```

- [ ] `--audio` でパイプライン実行
- [ ] 構造化 JSON (generated_script.json) が生成されること
- [ ] セグメント数 > 0、speaker が2名以上

### Step 2-1b: 手動テキスト投入 (フォールバック)

`--audio` が失敗する場合の代替手順:

- [ ] NotebookLM で Audio Overview のテキスト版を取得、またはWhisper等で文字起こし
- [ ] テキストをファイルとして保存 (`data/topics/{topic_id}/transcript/transcript.txt`)
- [ ] `--transcript transcript.txt` で投入

### Go/No-Go

- generated_script.json が存在し、セグメント > 0 → Phase 3 へ
- Gemini Audio API 失敗 → Step 2-1b フォールバックを試行

---

## Phase 3: 画像調達 + CSV 生成 (Python 自動)

> SP-050 Phase 3-5 対応 | 参考所要時間: 2-5分

Note: `--audio` 使用時は Phase 2 で構造化まで完了している。Phase 3 は画像調達と CSV 組立のみ。
`--transcript` 使用時は Phase 3 で構造化も行う。

### Step 3-1: パイプライン実行

```powershell
.\venv\Scripts\Activate.ps1

# 推奨: --audio で音声ファイルを直接投入 (SP-051)
python scripts/research_cli.py pipeline `
  --topic "<テーマ名>" `
  --audio "data/topics/{topic_id}/audio/overview.mp3" `
  --auto-images `
  --duration 300 `
  --save-transcript

# フォールバック: --transcript でテキストを直接投入
# python scripts/research_cli.py pipeline `
#   --topic "<テーマ名>" `
#   --transcript "data/topics/{topic_id}/transcript/transcript.txt" `
#   --auto-images `
#   --duration 300

# --duration: 目標動画尺 (秒)。初回は 300 (5分) 推奨
# --style: スタイルプリセット (default/news/educational/summary)
```

確認項目:
- [ ] `output_csv/timeline.csv` が生成された (4列: speaker, text, image_path, animation)
- [ ] `output_csv/metadata.json` が生成された
- [ ] `output_csv/overlay_plan.json` が生成された (SP-052, key_points/章タイトル/統計のオーバーレイ指示)
- [ ] 画像が取得された (stock / AI / slide)
- [ ] パイプライン完了サマリーに CRITICAL フォールバック WARNING がないこと

### Step 3-2: CSV 検証

```powershell
python scripts/research_cli.py validate output_csv/timeline.csv
```

- [ ] validate PASS
- [ ] 全行に image_path が設定されている
- [ ] animation_type が 8種 (ken_burns/zoom_in/zoom_out/pan_left/pan_right/pan_up/pan_down/fade) のいずれか

### Go/No-Go

- validate PASS + 画像全存在 + CRITICAL WARNING なし → Phase 4 へ
- validate FAIL → エラーメッセージに従い修正、再実行

### ブロッカー回避パス

- Gemini API quota 超過 → `LLM_PROVIDER` 環境変数でモデル切替、または時間を空けてリトライ
- 画像取得全失敗 → 画像なし行としてCSVに出力される (YMM4側でデフォルト背景が適用)
- `--transcript` ではなくソースから生成する場合 → `--topic` のみで実行 (Gemini が台本生成)

---

## Phase 4: YMM4 レンダリング (人間 + YMM4)

> SP-050 Phase 6 対応 | 参考所要時間: 5分 (インポート+確認) + 10-150分 (レンダリング)

### Step 4-1: YMM4 CSVインポート

1. [ ] YMM4 を起動
2. [ ] NLMSlidePlugin -> 「CSVインポート」を選択
3. [ ] 生成された `output_csv/timeline.csv` を指定
4. [ ] 「ボイス自動生成」チェックボックスを ON
5. [ ] インポート実行

### Step 4-2: タイムライン確認

- [ ] AudioItem (音声) が全セグメントに配置されている
- [ ] TextItem (字幕) が話者ごとに色分けされている
- [ ] ImageItem (背景画像) が配置されている
- [ ] アニメーション (Ken Burns / zoom / pan) が反映されている
- [ ] BGM テンプレートが適用されている (style_template.json)
- [ ] テキストオーバーレイ (章タイトル/キーポイント) が Layer 7 に配置されている (SP-052, overlay_plan.json が CSV と同じディレクトリにある場合のみ)

### Step 4-3: プレビュー + レンダリング

1. [ ] プレビュー再生で最初の30秒を確認
2. [ ] 映像・音声・字幕のタイミングに大きな問題がないこと
3. [ ] 「動画出力」-> MP4 (H.264 + AAC, 1920x1080) で保存
4. [ ] レンダリング完了まで待機
5. [ ] レンダリング時間を発見事項テーブルに記録

### Go/No-Go

- プレビュー30秒が自然 + レンダリング完了 → Phase 5 へ
- プレビューで重大な問題 → CSV を修正して Phase 3 からやり直し

### ブロッカー回避パス

- CSVインポート失敗 → encoding (UTF-8 BOM) / パス区切り (Windows) を確認
- ボイス割当失敗 → VoiceSpeakerDiscovery 3層フォールバック確認。YMM4 の音声設定を確認

---

## Phase 5: 後処理 + YouTube 公開 (Python + 人間)

> SP-050 Phase 7 対応 | 参考所要時間: 10-20分

### Step 5-1: MP4 品質検証

```powershell
python scripts/research_cli.py verify <mp4ファイルパス> --expected-duration 300
```

- [ ] 解像度 OK (1920x1080)
- [ ] コーデック OK (H.264 + AAC)
- [ ] 再生時間が想定範囲内 (±20%)
- [ ] CRITICAL 失敗なし

### Step 5-2: OAuth 取得 (初回のみ)

```powershell
# 前提: Google Cloud Console で OAuth クライアント ID を作成済み
# 前提: google_client_secret.json をプロジェクトルートに配置済み
# 手順: docs/google_api_setup.md 参照
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
- [ ] タグが反映されている
- [ ] 処理完了後、再生して映像・音声・字幕を確認

### Go/No-Go

- verify PASS + YouTube Studio で再生可能 → 完了
- verify FAIL → YMM4 出力設定 (コーデック/解像度) を確認し Phase 4 からやり直し

### ブロッカー回避パス

- FFprobe 未インストール → `choco install ffmpeg` または手動インストール
- OAuth 失敗 → `docs/google_api_setup.md` の手順を再確認
- YouTube API quota 超過 → 翌日に再試行 (10,000 units/day)

---

## 完了判定

以下がすべて OK なら「初回公開」スライス成立:

1. Phase 0-2 で NotebookLM から台本テキストが取得できた
2. Phase 3 で `--transcript` 経由で CSV が自動生成された
3. Phase 4 で YMM4 がエラーなくレンダリングした
4. Phase 5 で YouTube にアップロードされ、動画が再生可能

SP-035 (Integration Test) および SP-038 (YouTube Publish) の完了判定を兼ねる。

---

## 発見事項の記録

Phase 0-5 の通し実行で見つかった問題:

| # | フェーズ | 問題 | 深刻度 | 対応 |
|---|---------|------|--------|------|
|   |         |      |        |      |

各フェーズの実測時間 (参考値。品質優先、時間目標は Go/No-Go 基準にしない):

| フェーズ | ステップ | 実測時間 | 備考 |
|---------|---------|---------|------|
| Phase 0 | トピック選定 + ソース準備 |  |  |
| Phase 1 | Audio Overview 生成 |  | Customize 指示内容: |
| Phase 2 | テキスト化 |  | 文字数: |
| Phase 3 | Gemini 構造化 + CSV |  | セグメント数: / フォールバック: |
| Phase 4 | CSVインポート + 確認 |  |  |
| Phase 4 | レンダリング |  | 動画尺: / レンダリング倍率: |
| Phase 5 | MP4検証 + アップロード |  | verify 結果: |
| 合計 |  |  |  |

SP-050 未決定事項の実測結果:

| 項目 | 暫定回答 | 実測結果 | 更新要否 |
|------|---------|---------|---------|
| Q1-1: Audio Overview パラメータ | Customize ボタンでフォーカス指定可能 |  |  |
| Q6-2: レンダリング時間 | 動画尺の2-5倍 |  |  |
