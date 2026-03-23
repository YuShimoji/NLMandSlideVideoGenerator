# 制作ワークフローガイド

> **2026-03-22 更新**: 根本ワークフロー (DESIGN_FOUNDATIONS.md Section 0) に準拠。

---

## 概要

**制作パス (根本ワークフロー):**

```
NotebookLM ソース投入 → Audio Overview → テキスト化 → Gemini構造化 → CSV → YMM4 → mp4
```

**必要なもの:**
1. **NotebookLM アカウント** — 台本生成 (Audio Overview + テキスト化)
2. **Gemini API キー** — 台本構造化 (speaker/text 分離)
3. **YMM4 + NLMSlidePlugin** — 音声生成 + 動画レンダリング

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

> **重要**: YMM4 が最終レンダラーとして CSV → 音声合成 → 動画を一貫処理する。
> Python 側は音声生成を行わない。

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

NotebookLM テキストを投入し、Gemini構造化→画像取得→CSV合成までを一気通貫で実行します。

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

### 台本テキストの取得 (根本ワークフロー)

> DESIGN_FOUNDATIONS.md Section 0 参照

1. NotebookLM にソース (URL/テキスト/PDF) を投入
2. Audio Overview を生成 → 音声ファイルをダウンロード
3. **音声を NotebookLM に再投入** → テキスト化 (文字起こし)
4. テキストファイルとして保存 → Python パイプラインに投入
5. Gemini API が speaker/text に構造化 → CSV に変換

> **注意**: 音声を外部ツールで WAV 分割する旧経路は廃止済み。音声は NotebookLM に再投入してテキスト化する。

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

### 「CSVインポート後に音声が生成されない」

- YMM4 の NLMSlidePlugin が正しくインストールされているか確認
- CSV の speaker 列が YMM4 のボイスプリセットにマッピング可能か確認
- VoiceSpeakerDiscovery のログを確認

### 「NotebookLM のテキスト化が不正確」

- Audio Overview の音質が十分か確認
- テキスト化後に手動で明らかな誤りを修正してから Gemini 構造化に投入

---

## 関連ドキュメント

- `docs/voice_path_comparison.md` - ゆっくりボイス経路比較・推奨
- `docs/ymm4_export_spec.md` - YMM4エクスポート仕様
- `docs/spec_transcript_io.md` - 台本I/O仕様
