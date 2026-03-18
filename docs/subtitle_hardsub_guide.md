# 字幕ハードサブ環境ガイド

最終更新: 2026-03-18

動画に字幕を直接焼き込む（ハードサブ）機能の使い方と環境設定について説明します。

## 概要

### 字幕の種類

1. **ソフトサブ（外部字幕）**
   - 字幕ファイル（SRT/ASS/VTT）を動画と一緒に配布
   - 視聴者が字幕のON/OFFを切替可能
   - YouTubeアップロード時に字幕ファイルをアップロード

2. **ハードサブ（焼き込み）**
   - 字幕を動画の映像に直接焼き込み
   - 視聴者は字幕のON/OFFを切替不可
   - どの環境でも確実に字幕が表示される

### 現行パイプラインでの字幕

本プロジェクトでは **YMM4 が最終レンダラー** です。字幕は以下の2つの方法で扱います:

1. **YMM4 内蔵字幕 (推奨)**: CSVインポート時に `TextItem` として自動配置。`style_template.json` の `subtitle` 設定で書式を制御。話者ごとに色分け (6色サイクル)
2. **FFmpeg 手動焼き込み**: YMM4 で出力した mp4 に対して後処理で字幕を焼き込む (特殊なケースのみ)

## 環境設定

### 必要なツール

#### FFmpeg（字幕焼き込みに必要）

```powershell
# Windows (winget)
winget install FFmpeg

# インストール確認
ffmpeg -version
```

#### pysrt（オプション: SRT ファイル操作）

```bash
pip install pysrt
```

### 環境チェックスクリプト

```bash
python scripts/check_environment.py
```

## 使用方法

### YMM4 での字幕設定 (推奨)

1. CSVパイプラインで4列CSVを生成 (`research_cli.py pipeline`)
2. YMM4 で CSVインポート (NLMSlidePlugin)
3. `TextItem` が自動配置され、`style_template.json` のスタイルが適用される
4. 字幕の書式は `config/style_template.json` の `subtitle` セクションで変更可能:

```json
{
  "subtitle": {
    "font_size": 36,
    "border_width": 3,
    "bold": true,
    "position": "center_bottom"
  }
}
```

### FFmpeg による手動焼き込み

YMM4 で出力した mp4 に後処理で字幕を追加する場合:

```powershell
# SRT字幕の焼き込み
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt" output.mp4

# ASS字幕の焼き込み（スタイル付き）
ffmpeg -i input.mp4 -vf "ass=subtitles.ass" output.mp4

# フォント・サイズ指定 (日本語)
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt:force_style='FontName=Noto Sans JP,FontSize=24,PrimaryColour=&Hffffff&'" output.mp4
```

## 出力ファイル

CSVパイプラインを実行すると、以下の字幕ファイルが生成されます:

| ファイル | 形式 | 用途 |
|----------|------|------|
| `*.srt` | SubRip | 汎用・YouTube |
| `*.ass` | Advanced SubStation | スタイル付き |
| `*.vtt` | WebVTT | Web用 |

これらのファイルは `data/transcripts/` ディレクトリに保存されます。

## トラブルシューティング

### FFmpegが見つからない

1. FFmpegがインストールされているか確認
2. PATHに追加されているか確認
3. ターミナルを再起動

```powershell
where ffmpeg
```

### 日本語が文字化けする

```powershell
# フォント指定で焼き込み
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt:force_style='FontName=Noto Sans JP'" output.mp4
```

### 字幕が表示されない

1. 字幕ファイルのエンコーディングがUTF-8か確認
2. タイムスタンプが動画の長さと一致しているか確認
3. フォントが正しくインストールされているか確認

## YouTube投稿時の字幕

### ソフトサブとして投稿 (推奨)

1. 動画をアップロード
2. 字幕設定で「字幕ファイルをアップロード」を選択
3. 生成された `.srt` ファイルをアップロード

### ハードサブとして投稿

1. 事前に字幕を焼き込んだ動画を生成
2. その動画をアップロード

## 関連ドキュメント

- [CSVパイプライン使用ガイド](user_guide_manual_workflow.md)
- [CSV入力フォーマット仕様](spec_csv_input_format.md)
- [トラブルシューティング](TROUBLESHOOTING.md)
