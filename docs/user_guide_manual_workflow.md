# 手動素材ワークフローガイド

このガイドでは、NotebookLM等で生成した素材から動画を作成する手順を説明します。

---

## 概要

**想定フロー:**
```
[NotebookLM等で素材準備] → [このアプリに提出] → [動画生成]
```

**必要な素材:**
1. **台本/テロップ** - CSV形式 または テキスト
2. **音声ファイル** - WAV形式（行ごとに分割）

**出力:**
- 動画ファイル (.mp4)
- 字幕ファイル (SRT/ASS/VTT)
- (オプション) YMM4プロジェクト

---

## 方法1: CSVタイムラインパイプライン（推奨）

### ステップ1: 素材の準備

#### 1-1. CSV台本の作成

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

**注意:**
- 1行 = 1つの音声ファイルに対応
- 長い行は自動的に複数スライドに分割されます（デフォルト60文字）

#### 1-2. 音声ファイルの準備

各行に対応するWAVファイルを用意します。

```
audio_folder/
├── 001.wav  (1行目の音声)
├── 002.wav  (2行目の音声)
├── 003.wav  (3行目の音声)
└── ...
```

**ファイル命名規則:**
- `001.wav`, `002.wav`, `003.wav`, ...
- 3桁のゼロ埋め番号

**音声生成方法の例:**
- **NotebookLM**: Deep Dive Audio機能で生成
- **SofTalk/AquesTalk**: バッチスクリプトで生成 (`scripts/tts_batch_softalk.py`)
- **ElevenLabs/OpenAI TTS**: API経由で生成

### ステップ2: 動画生成の実行

#### 方法A: コマンドライン (CLI)

```bash
python scripts/run_csv_pipeline.py \
  --csv "path/to/timeline.csv" \
  --audio-dir "path/to/audio_folder" \
  --topic "動画タイトル" \
  --video-quality 1080p
```

**オプション:**
| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--csv` | CSVファイルパス | (必須) |
| `--audio-dir` | 音声ディレクトリ | (必須) |
| `--topic` | 動画タイトル | CSVファイル名 |
| `--video-quality` | 品質 (1080p/720p/480p) | 1080p |
| `--export-ymm4` | YMM4プロジェクト出力 | false |
| `--upload` | YouTube自動アップロード | false |
| `--max-chars-per-slide` | スライド文字数上限 | 60 |

#### 方法B: Web UI

1. `streamlit run src/web/web_app.py` を実行
2. サイドバーで **「CSV Pipeline」** を選択
3. フォームに入力:
   - CSVファイルをアップロード
   - 音声ディレクトリのパスを入力
   - トピック名を入力
   - オプションを設定
4. **「動画生成開始」** をクリック

### ステップ3: 出力の確認

生成後、以下の場所に出力されます:

```
data/
├── videos/
│   └── generated_video_YYYYMMDD_HHMMSS.mp4
├── transcripts/
│   ├── {topic}_subtitles.srt
│   ├── {topic}_subtitles.vtt
│   └── {topic}_subtitles_default.ass
└── ymm4/  (YMM4エクスポート時)
    └── ymm4_project_XXXXXX/
        ├── project.y4mmp
        ├── slides_payload.json
        └── timeline_plan.json
```

---

## 方法2: 通常パイプライン（トピックベース）

トピックを指定して、AI生成を含む完全自動化パイプラインを実行します。

**注:** この方法は現在、一部の機能がモック実装です。

```bash
# CLI実行
python src/main.py --topic "AI技術の最新動向" --quality 1080p
```

または Web UI の「Pipeline Execution」ページから実行。

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
2. **自動分割**: 無音検出で分割するスクリプトを使用

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

- `docs/tts_batch_softalk_aquestalk.md` - SofTalk/AquesTalk連携
- `docs/ymm4_export_spec.md` - YMM4エクスポート仕様
- `docs/spec_transcript_io.md` - 台本I/O仕様
