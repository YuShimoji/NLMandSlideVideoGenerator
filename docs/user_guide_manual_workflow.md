# 手動素材ワークフローガイド

このガイドでは、NotebookLM等で生成した素材から動画を作成する手順を説明します。

---

## 概要

**2つの制作パス:**

```
Path A (Primary): CSV → YMM4 → 最終 mp4
Path B (Secondary): CSV + WAV群 → Python pipeline → mp4
```

**Path A（YMM4 制作）の必要素材:**
1. **台本/テロップ** - CSV形式（speaker, text）

**Path B（Batch TTS + Python pipeline）の必要素材:**
1. **台本/テロップ** - CSV形式（speaker, text）
2. **音声ファイル** - WAV形式（001.wav, 002.wav, ... 行ごとに分割）

**出力:**
- **Path A**: YMM4 からレンダリングした最終 mp4
- **Path B**: 動画ファイル (.mp4) + 字幕ファイル (SRT/ASS/VTT)

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

## 方法2: CSVタイムライン + Batch TTS パイプライン（Path B）

### ステップ1: 素材の準備

#### 1-1. CSV台本の作成

方法1と同じフォーマットでCSVを作成します。

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

**音声生成方法（YMM4以外）:**

1. **SofTalk/AquesTalk** [自動化可・環境依存]
   - バッチスクリプト: `scripts/tts_batch_softalk_aquestalk.py`
   - 詳細: `docs/tts_batch_softalk_aquestalk.md`
2. **手動準備** [常時利用可]
   - 棒読みちゃん、VOICEVOX等で音声生成 → 連番WAVにリネーム
3. **NotebookLM**: Deep Dive Audio → 分割 (ゆっくりボイスではない)
4. **ElevenLabs/OpenAI TTS**: API経由 (ゆっくりボイスではない)

### ステップ2: 動画生成の実行（Path B のみ）

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

### CSV+TTS Webフロー E2E 手順（SofTalk/AquesTalk）

> ⚠️ 現在、SofTalk / AquesTalk 連携は環境依存の要素が多く、
> 「動作すれば便利なオプション」という位置づけです。CSV タイムラインモード自体は、
> **任意の手段で 001.wav, 002.wav... を用意できれば利用可能** であり、
> YMM4 や他 TTS を使うワークフローも同等にサポートされます。

このプロジェクトで想定している「CSV+TTS→Web UI→動画生成」の一連の流れは、次のようになります。

1. **前提準備**
   - SofTalk または AquesTalk をローカルにインストール
   - 環境変数 `SOFTALK_EXE` または `AQUESTALK_EXE` に実行ファイルパスを設定
   - 詳細は `docs/tts_batch_softalk_aquestalk.md` を参照

2. **CSV台本の準備**
   - 上記「1-1. CSV台本の作成」に従って、話者列 + テキスト列のCSVを用意
   - サンプル: `docs/spec_csv_input_format.md` や Web UI のサンプルコードを参照

3. **Web UI の起動と CSV Pipeline ページの表示**
   - ターミナルで `streamlit run src/web/web_app.py` を実行
   - ブラウザのサイドバーから **「CSV Pipeline」** を選択

4. **TTSバッチ（SofTalk/AquesTalk）の実行**
   - CSV Pipeline ページ下部の **SofTalk/AquesTalk TTS バッチセクション** を開く
   - 入力内容の例:
     - TTSエンジン: `SofTalk` または `AquesTalk`
     - 出力ディレクトリ: `data/tts_outputs/例)` など任意の空ディレクトリ
     - SpeakerマップJSON: CSVの話者名 → TTSプリセットの対応表
   - 必要に応じて **dry-run** でコマンド内容を確認
   - 実行後、ログエリアで各行のWAV生成結果を確認

5. **audio_dir の自動反映**
   - TTS バッチが成功すると、指定した出力ディレクトリが Web セッションに記憶されます
   - ページ上の **「audio_dir に反映」ボタン**（名称はUIに準拠）から、
     - 生成された音声ディレクトリパスを `audio_dir` 入力欄へワンクリックで反映

6. **動画生成の実行（CSV Timeline パイプライン）**
   - CSVファイルをアップロード
   - `audio_dir` に TTS出力ディレクトリが設定されていることを確認
   - トピック名・画質・YMM4出力有無などオプションを指定
   - **「動画生成開始」** ボタンを押す
   - 実行中はページ内の進捗バーとログを確認

7. **出力物とジョブ履歴の確認**
   - 上記「ステップ3: 出力の確認」にあるように、`data/videos/` と `data/transcripts/` を確認
   - Web UI の結果セクションで:
     - 出力動画のパスと簡易プレビュー
     - 生成された字幕ファイル一覧
     - YMM4 プロジェクト情報（エクスポート有効時）
     - `job_id`（内部ジョブ管理用ID）
   - ジョブIDを元に、設定ページのジョブ履歴UIから過去の実行状況を参照可能です（今後の拡張前提）。

---

## 方法3: 通常パイプライン（トピックベース）

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
- `docs/tts_batch_softalk_aquestalk.md` - SofTalk/AquesTalk連携
- `docs/ymm4_export_spec.md` - YMM4エクスポート仕様
- `docs/spec_transcript_io.md` - 台本I/O仕様
