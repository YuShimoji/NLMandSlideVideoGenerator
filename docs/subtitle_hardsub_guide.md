# 字幕ハードサブ環境ガイド

このドキュメントでは、動画に字幕を直接焼き込む（ハードサブ）機能の使い方と環境設定について説明します。

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

## 環境設定

### 必要なライブラリ

#### 1. pysrt（推奨）

SRTファイルの読み込みに使用します。

```bash
pip install pysrt
```

**確認方法:**
```python
python -c "import pysrt; print('pysrt OK')"
```

#### 2. FFmpeg（必須）

動画への字幕焼き込みに使用します。

**Windows:**
```powershell
winget install FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

**確認方法:**
```bash
ffmpeg -version
```

### 環境チェックスクリプト

プロジェクトに含まれる環境チェックスクリプトを実行して、必要な環境が揃っているか確認できます：

```bash
python scripts/check_environment.py
```

## 使用方法

### 1. 設定ファイルでの制御

`config/settings.py` の `SUBTITLE_SETTINGS` で字幕の設定を変更できます：

```python
SUBTITLE_SETTINGS = {
    "font_size": 36,
    "font_color": "white",
    "outline_color": "black",
    "outline_width": 2,
    "position": "bottom",      # "top" or "bottom"
    "background_opacity": 0.0, # 0.0〜1.0
    "margin": 50,
}
```

### 2. 字幕焼き込みの有効化

現在のパイプラインでは、以下の条件でハードサブが有効になります：

1. `pysrt` がインストールされている
2. 字幕ファイル（SRT）が生成されている
3. MoviePy または FFmpeg で動画を合成する際に自動適用

#### FFmpegによる手動焼き込み

生成された字幕ファイルを使って手動で焼き込む場合：

```bash
# SRT字幕の焼き込み
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt" output.mp4

# ASS字幕の焼き込み（スタイル付き）
ffmpeg -i input.mp4 -vf "ass=subtitles.ass" output.mp4

# フォント・サイズ指定
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt:force_style='FontSize=24,PrimaryColour=&Hffffff&'" output.mp4
```

## 出力ファイル

CSVパイプラインを実行すると、以下の字幕ファイルが生成されます：

| ファイル | 形式 | 用途 |
|----------|------|------|
| `*.srt` | SubRip | 汎用・YouTube |
| `*.ass` | Advanced SubStation | スタイル付き・YMM4 |
| `*.vtt` | WebVTT | Web用 |

これらのファイルは `data/transcripts/` ディレクトリに保存されます。

## トラブルシューティング

### pysrtがインストールできない

```bash
# pipを最新版に更新
pip install --upgrade pip

# 再インストール
pip install pysrt
```

### FFmpegが見つからない

1. FFmpegがインストールされているか確認
2. PATHに追加されているか確認
3. ターミナル/コマンドプロンプトを再起動

```bash
# Windowsでパスを確認
where ffmpeg

# macOS/Linuxでパスを確認
which ffmpeg
```

### 字幕が表示されない

1. 字幕ファイルのエンコーディングがUTF-8か確認
2. タイムスタンプが動画の長さと一致しているか確認
3. フォントが正しくインストールされているか確認

### 日本語が文字化けする

```bash
# フォント指定で焼き込み
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt:fontsdir=/path/to/fonts:force_style='FontName=Noto Sans JP'" output.mp4
```

## YouTube投稿時の字幕

### ソフトサブとして投稿

1. 動画をアップロード
2. 字幕設定で「字幕ファイルをアップロード」を選択
3. 生成された `.srt` ファイルをアップロード

### ハードサブとして投稿

1. 事前に字幕を焼き込んだ動画を生成
2. その動画をアップロード

## 関連ドキュメント

- [CSVパイプライン使用ガイド](user_guide_manual_workflow.md)
- [CSV入力フォーマット仕様](spec_csv_input_format.md)
- [環境セットアップ](../README.md#セットアップ)
