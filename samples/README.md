# サンプルファイル

動画生成パイプラインをすぐに試せるサンプルです。

## サンプル一覧

### basic_dialogue（音声なし対話）

ゆっくりボイスによる2人の対話サンプル。画像なし。

```
basic_dialogue/
├── timeline.csv    # 台本（10行、話者: れいむ/まりさ）
└── audio/          # テスト用無音WAV (使用しない)
```

### image_slide（画像付き解説）

スライド画像付きの解説動画サンプル。全機能の動作確認用。

```
image_slide/
├── timeline.csv        # 台本（8行、話者: れいむ/まりさ、画像パス付き）
├── test_with_images.csv  # 短縮版（6行）
└── slides/
    ├── slide_0001.png  # 1920x1080 タイトルスライド
    ├── slide_0002.png  # 1920x1080 本編スライド
    └── slide_0003.png  # 1920x1080 まとめスライド
```

---

## 使い方: サンプルからmp4を書き出すまで

### 前提条件

- YMM4 v4.50+ がインストール済み
- NLMSlidePlugin がデプロイ済み (`ymm4-plugin/` のビルド成果物を YMM4 plugin フォルダにコピー)

### 手順

#### Step 1: CSVの画像パスを絶対パスに変換

サンプルCSVの画像パスは相対パスなので、YMM4に読み込む前に絶対パスに変換する。

```bash
# PowerShell
$base = (Resolve-Path samples/image_slide).Path
(Get-Content samples/image_slide/timeline.csv) -replace 'slides/', "$base\slides\" | Set-Content samples/image_slide/timeline_abs.csv
```

または手動で `slides/slide_0001.png` を `C:\...\samples\image_slide\slides\slide_0001.png` に書き換える。

#### Step 2: YMM4で新規プロジェクト作成

1. YMM4を起動
2. 新規プロジェクト → 1920x1080, 30fps
3. プロジェクトを保存（任意の場所）

#### Step 3: CSVインポート

1. メニュー → NLMSlidePlugin → 「CSVタイムラインをインポート」
2. `timeline_abs.csv` (絶対パス版) を選択
3. 「字幕を追加」「音声を生成」にチェック
4. 「インポート」をクリック

#### Step 4: インポート結果の確認

タイムラインに以下が配置される:

| レイヤー | 種類 | 内容 |
|---------|------|------|
| N | AudioItem | ゆっくりボイス音声 |
| N+1 | ImageItem | スライド画像（全画面フィット + Ken Burns 5%ズーム + フェードイン） |
| N+2 | TextItem | 字幕テキスト（画面下部固定、48pt） |

#### Step 5: プレビューと調整

- スペースキーでプレビュー再生
- 確認ポイント:
  - 画像が全画面に表示されているか
  - Ken Burnsのゆるやかなズームが見えるか
  - 字幕が画面下部に表示されているか
  - 音声と字幕のタイミングが合っているか
  - スライド切替時にフェードインが見えるか

#### Step 6: レンダリング

1. ファイル → 動画出力
2. 出力先とファイル名を指定
3. レンダリング実行 → mp4

---

## 自分のサンプルを作成する

### CSV形式

```csv
話者名,テロップテキスト,画像パス(任意)
れいむ,こんにちは,C:\slides\slide_01.png
まりさ,よろしくお願いします,
```

| 列 | 内容 | 備考 |
|----|------|------|
| A列 | 話者名 | YMM4のキャラクター名と一致させる（れいむ、まりさ等） |
| B列 | テロップテキスト | 読み上げ内容 |
| C列 | 画像パス（任意） | 絶対パスを推奨。空欄なら画像なし |

### 話者名のマッピング

| CSV上の話者名 | YMM4音声 |
|-------------|---------|
| れいむ / Reimu / Speaker1 | ゆっくりれいむ |
| まりさ / Marisa / Speaker2 | ゆっくりまりさ |
| ナレーター / Host1 | ゆっくりれいむ（フォールバック） |

### 画像の準備

- 推奨サイズ: 1920x1080 (16:9)
- フォーマット: PNG
- 異なるアスペクト比でも動作する（containフィットで黒帯が付く）

---

## 関連ドキュメント

- [ユーザーガイド](../docs/user_guide_manual_workflow.md)
- [CSV入力フォーマット仕様](../docs/spec_csv_input_format.md)
- [YMM4エクスポート仕様](../docs/ymm4_export_spec.md)
