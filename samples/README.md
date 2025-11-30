# サンプルファイル

このディレクトリには、動画生成パイプラインをすぐに試せるサンプルファイルが含まれています。

## basic_dialogue（基本的な対話）

2人の話者による対話形式のサンプルです。

```
basic_dialogue/
├── timeline.csv    # 台本（10行）
└── audio/
    ├── 001.wav    # 1行目の音声
    ├── 002.wav    # 2行目の音声
    └── ...        # (計10ファイル)
```

### 実行方法

#### CLI

```bash
python scripts/run_csv_pipeline.py \
  --csv samples/basic_dialogue/timeline.csv \
  --audio-dir samples/basic_dialogue/audio \
  --topic "AI技術解説サンプル"
```

#### Web UI

1. `streamlit run src/web/web_app.py` を実行
2. サイドバーで「CSV Pipeline」を選択
3. CSVファイル: `samples/basic_dialogue/timeline.csv` をアップロード
4. 音声ディレクトリ: `samples/basic_dialogue/audio` を入力
5. 「動画生成開始」をクリック

### 注意事項

- 同梱の音声ファイルは **無音のテスト用** です
- 実際の動画制作では、以下のツールで音声を生成してください:
  - **NotebookLM** - Deep Dive Audio機能
  - **SofTalk / AquesTalk** - `scripts/tts_batch_softalk.py`
  - **ElevenLabs / OpenAI TTS** - API経由

## 自分のサンプルを作成する

### 1. CSVファイルの作成

```csv
話者名,テロップテキスト
Speaker1,こんにちは
Speaker2,よろしくお願いします
```

### 2. 音声ファイルの準備

CSVの行数に対応する音声ファイルを用意:
- `001.wav` (1行目)
- `002.wav` (2行目)
- ...

### 3. 実行

```bash
python scripts/run_csv_pipeline.py --csv your_timeline.csv --audio-dir your_audio/
```

## 関連ドキュメント

- [ユーザーガイド](../docs/user_guide_manual_workflow.md)
- [CSV入力フォーマット仕様](../docs/spec_csv_input_format.md)
- [音声生成バッチ](../docs/tts_batch_softalk_aquestalk.md)
