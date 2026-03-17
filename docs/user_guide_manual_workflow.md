# 手動素材ワークフローガイド

このガイドでは、NotebookLM等で生成した素材から動画を作成する手順を説明します。

---

## 概要

**制作パス:**

```
Path A (唯一): CSV → YMM4 → 最終 mp4
```

**必要素材:**
1. **台本/テロップ** - CSV形式（speaker, text）

**出力:**
- YMM4 からレンダリングした最終 mp4

---

## 方法1: YMM4 制作フロー（推奨 / Path A）

### ステップ1: CSV台本の作成

CSVファイルを作成します。フォーマット:

```csv
Speaker1,これは1行目のテロップです
Speaker2,これは2行目のテロップです
Speaker1,3行目のテロップです
```

| 列 | 内容 | 例 |
|----|------|-----|
| A列 | 話者名 | Speaker1, ナレーター, ずんだもん |
| B列 | テロップテキスト | セリフ内容 |

### ステップ2: YMM4 で制作

1. YMM4 を起動し、新規プロジェクトを作成
2. NLMSlidePlugin の「CSVタイムラインをインポート」からCSVを読み込む
3. YMM4 内でゆっくりボイス音声を自動生成
4. レイアウト・音声を確認・調整
5. YMM4 で動画をレンダリング（書き出し）→ 最終 mp4

> **重要**: YMM4 は個別 WAV エクスポートができないため、WAV 供給元としては使用しない。
> YMM4 が最終レンダラーとして CSV→音声→動画を一貫処理する。

---

## (削除済み) 方法2: CSVタイムライン + Batch TTS パイプライン（Path B）

> **Path B は 2026-03-08 に完全削除されました。**
>
> - MoviePy backend (`src/core/editing/moviepy_backend.py`) 削除済み
> - TTS統合 (`src/audio/tts_integration.py`) 削除済み
> - video_composer (`src/video_editor/video_composer.py`) 削除済み
> - `run_csv_pipeline.py` および `csv_pipeline_runner.py` 削除済み
>
> **現行の制作方法は Path A（YMM4制作フロー）のみです。**

---

## 方法3: 一気通貫パイプライン（トピックベース）

トピックを指定して、リサーチ→台本生成→画像取得→CSV合成までを一気通貫で実行します。

```bash
# CLI実行（推奨）
python scripts/research_cli.py pipeline \
  --topic "AI技術の最新動向" \
  --auto-review \
  --auto-images \
  --duration 5 \
  --speaker-map '{"Host1":"れいむ","Host2":"まりさ"}'
```

または Web UI の「素材パイプライン」ページから実行。

出力されたCSVは方法1 (YMM4制作フロー) のStep 2へ接続する。
詳細: `docs/material_pipeline_spec.md`, `docs/ymm4_final_workflow.md`

---

## NotebookLMからの素材準備

### Deep Dive Audio の利用

1. **NotebookLM** (https://notebooklm.google.com/) にアクセス
2. ソース資料をアップロード
3. 「Audio Overview」を生成
4. 生成された音声をダウンロード

### 台本の準備

NotebookLMで生成された内容を元に、CSVを手動作成:

```csv
Host1,今日はAI技術について話しましょう
Host2,はい、最近の進化はすごいですね
Host1,特に生成AIの分野が注目されています
```

### 音声の分割

NotebookLMの音声は1ファイルなので、以下の方法で分割:

1. **手動分割**: Audacityなどで話者交代部分でカット
2. **自動分割**: 無音検出で分割するスクリプト (`scripts/split_audio_by_silence.py`) を使用

```bash
python scripts/split_audio_by_silence.py \
  --input path/to/long_audio.wav \
  --out-dir path/to/audio_dir \
  --min-silence-sec 0.7 \
  --silence-threshold 0.02
```

---

## トラブルシューティング

### 「FFmpegが見つかりません」

動画出力にはFFmpegが必要です。

**インストール方法:**
```bash
# Windows (winget)
winget install FFmpeg

# Windows (Chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 「音声ファイルが見つかりません」

- ファイル名が `001.wav`, `002.wav` ... の形式か確認
- CSVの行数と音声ファイル数が一致しているか確認

### 「動画が生成されるが空になる」

- FFmpegが正しくインストールされているか確認
- 環境チェック: `python scripts/check_environment.py`

---

## 関連ドキュメント

- `docs/voice_path_comparison.md` - ゆっくりボイス経路比較・推奨
- `docs/ymm4_export_spec.md` - YMM4エクスポート仕様
- `docs/spec_transcript_io.md` - 台本I/O仕様
