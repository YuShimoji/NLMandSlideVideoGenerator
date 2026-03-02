# ゆっくりボイス利用経路 比較・推奨

Updated: 2026-02-28T16:40:00+09:00
Source: TASK_014

## 前提

- 最終出力は 16:9 の汎用スライド動画
- 音声は「ゆっくりボイス」が最優先
- CSV パイプラインへの入力は `audio_dir` 配下の `001.wav`, `002.wav`, ... 形式
- キャラクター表示は必須ではない

---

## 経路比較

| # | 経路 | 役割 | 自動化度 | 安定度 | 環境依存 | 状態 |
|---|------|------|----------|--------|----------|------|
| 1 | **YMM4（最終レンダラー）** | CSV→音声→動画を一貫処理 | 低（GUI操作） | 高 | YMM4 v4.33+ | 動作確認済み |
| 2 | **SofTalk バッチ + Python pipeline** | 自動WAV生成→自動動画生成 | 高 | 中 | SofTalk.exe 必須 | 実装あり・環境依存大 |
| 3 | **AquesTalk バッチ + Python pipeline** | 自動WAV生成→自動動画生成 | 高 | 中 | AquesTalkPlayer.exe 必須 | 実装あり・環境依存大 |
| 4 | **手動準備 + Python pipeline** | 任意ツールでWAV→自動動画生成 | なし | 高 | なし | 常時利用可 |

---

## 推奨順位

### 第1推奨: YMM4 最終レンダラー

**理由**: CSV→音声生成→動画レンダリングを YMM4 が一貫して処理できる。Python パイプラインを経由しない。

**手順**:

| Step | 操作 | 出力 |
|------|------|------|
| 1 | タイムライン CSV を用意する（A列=話者, B列=テキスト） | `timeline.csv` |
| 2 | YMM4 を起動し、新規プロジェクトを作成 | `.ymmp` ファイル |
| 3 | NLMSlidePlugin の「CSVタイムラインをインポート」からCSVを読み込む | タイムラインにアイテム追加 |
| 4 | YMM4 のキャラクター音声機能で各行の音声を自動生成 | YMM4 プロジェクト内音声 |
| 5 | YMM4 内で音声・レイアウトを確認・調整 | — |
| 6 | YMM4 で動画をレンダリング（書き出し） | 最終 mp4 |

**注意点**:
- YMM4 が最終レンダラーであり、Python パイプライン (`run_csv_pipeline.py`) は使用しない
- YMM4 は個別 WAV のエクスポートができないため、WAV 供給元としては使用しない
- YMM4 のキャラクター音声設定（ずんだもん、四国めたん等）は YMM4 側で設定する
- YMM4 v4.33.0.0 以降を推奨

---

### 第2推奨: SofTalk / AquesTalk バッチ + Python パイプライン

**理由**: YMM4 を使わずに自動化可能。ただしインストールと環境設定に手間がかかる。

**前提条件**:
- SofTalk.exe または AquesTalkPlayer.exe がインストール済みであること
- 環境変数 `SOFTALK_EXE` / `AQUESTALK_EXE` にパスを設定するか、PATH に含めること

**手順**:

| Step | 操作 | 出力 |
|------|------|------|
| 1 | SofTalk または AquesTalk をインストール | 実行ファイル |
| 2 | 環境変数を設定 | — |
| 3 | タイムライン CSV を用意 | `timeline.csv` |
| 4 | バッチスクリプトを実行 | `audio_dir/001.wav`, `002.wav`, ... |
| 5 | CSV パイプラインを実行 | 動画 + 字幕 |

```powershell
# Step 4
.\venv\Scripts\python.exe scripts\tts_batch_softalk_aquestalk.py `
  --engine softalk `
  --csv data\timeline.csv `
  --out-dir data\audio\episode01

# Step 5
.\venv\Scripts\python.exe scripts\run_csv_pipeline.py `
  --csv data\timeline.csv `
  --audio-dir data\audio\episode01 `
  --topic "解説動画タイトル"
```

**既知の制約**:
- SofTalk は Shift-JIS 前提の場合がある（スクリプト内で変換処理あり）
- インストール先ディレクトリによって設定ファイルの保存可否が変わる
- ウィンドウの表示/非表示の挙動がバージョンにより異なる

---

### 第3推奨: 手動準備 + Python パイプライン

**理由**: どんな環境でも使えるが、音声生成は手作業。Python パイプラインで動画を自動生成。

**手順**:

| Step | 操作 | 出力 |
|------|------|------|
| 1 | 任意のツールでゆっくり音声を生成（棒読みちゃん、VOICEVOX 等） | 音声ファイル群 |
| 2 | CSV の行番号に合わせて `001.wav`, `002.wav`, ... にリネーム | `audio_dir/` |
| 3 | `run_csv_pipeline.py` で動画を生成 | 動画 + 字幕 |

---

## フォールバック手順

| 状態 | 対処 |
|------|------|
| YMM4 がインストールされていない | 第2推奨（SofTalk バッチ + pipeline）または第3推奨（手動 + pipeline）に切り替え |
| SofTalk/AquesTalk がインストールされていない | 第1推奨（YMM4）または第3推奨（手動 + pipeline）に切り替え |
| WAV ファイルが `audio_dir` にない（Path B使用時） | パイプラインは起動するがデフォルト3秒のプレースホルダーが使われる |
| WAV の連番が CSV 行数と合わない（Path B使用時） | ログに警告が出る。不足分はデフォルト音声長で補完される |
| パイプライン実行中にエラー（Path B使用時） | `--video-quality 480p` で低解像度テストを先に行い、成功を確認してから本番品質で再実行 |

---

## ログの見方

パイプライン実行時のログで音声経路の状態を確認:

```
INFO: CsvTranscriptLoader: Loading CSV ...
INFO: Audio file found: 001.wav (duration=3.2s)
INFO: Audio file found: 002.wav (duration=2.8s)
WARNING: Audio file not found: 003.wav (using default 3.0s)
```

- `Audio file found` → 正常
- `Audio file not found` → WAV が足りていない。生成を確認
- `using default` → プレースホルダー音声が使われている
