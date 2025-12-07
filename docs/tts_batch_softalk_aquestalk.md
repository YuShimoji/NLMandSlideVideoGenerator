# SofTalk / AquesTalk ローカル TTS バッチ連携仕様

このドキュメントは、SofTalk / AquesTalk 等の **ローカル TTS エンジン** を用いて、
CSV タイムライン(P10)モード向けの行ごと WAV 音声を一括生成するための仕様をまとめたものです。

- 対象範囲
  - CSV 1 行ごとに 1 音声ファイル (`001.wav`, `002.wav`, ...) を生成する **バッチ TTS ステージ**。
  - 生成された音声を `run_csv_pipeline.py` / `/api/v1/pipeline/csv` の `audio_dir` に渡す運用。
  - その結果として、YMM4 エクスポート仕様 (`docs/ymm4_export_spec.md`) に従ったプロジェクト出力が行われる前提。
- 非対象範囲
  - SofTalk / AquesTalk 自体のインストール方法や GUI 操作手順。
  - 将来的なクラウド TTS (ElevenLabs, Azure 等) は別仕様とする。

---

## 1. ドキュメント内の言語ポリシー

YMM4 仕様ドキュメントと同様に、以下のポリシーで日本語/英語を使い分けます。

- **説明文・背景・注意事項**: 日本語
- **コード要素・CLI/API 名・ファイル名・JSON キー**: 英語の表記そのまま
  - 例: `audio_dir`, `run_csv_pipeline.py`, `--engine`, `001.wav` など
- **CLI 使用例や疑似コード**: コードブロック内は英語、周囲の説明は日本語

---

## 2. 全体アーキテクチャ概要

### 2.1 現状の CSV タイムラインフロー (おさらい)

1. ユーザーが **タイムライン CSV** を用意
   - A 列: 話者 (例: `Speaker1`)
   - B 列: テキスト (読み上げ内容)
2. 行ごとの WAV (`001.wav`, `002.wav`, ...) を `audio_dir` に配置
3. `run_csv_pipeline.py` または `/api/v1/pipeline/csv` から CSV モードを実行
4. `ModularVideoPipeline.run_csv_timeline` が以下を実施
   - `CsvTranscriptLoader` で CSV + 行ごと音声から `TranscriptInfo` / `AudioInfo` を構築
   - スライド分割 (`_expand_segment_into_slides`) と `slides_payload` の生成
   - 動画合成 (MoviePy or YMM4+MoviePy) と YMM4 エクスポート

### 2.2 SofTalk / AquesTalk バッチ連携の位置づけ

本仕様で定義するのは、上記フローの **前段階** に追加される TTS バッチステージです。

1. 入力: タイムライン CSV (`csv_path`) と、TTS 用設定 (話者/声質 など)
2. 処理: SofTalk / AquesTalk をコマンドラインから呼び出し、
   - 各行のテキストを音声合成
   - `audio_dir` 配下に `001.wav`, `002.wav`, ... として保存
3. 出力: `audio_dir` を CSV パイプラインにそのまま渡す

> パイプライン本体 (`run_csv_timeline`) や YMM4 エクスポートの実装には手を入れず、
> **「行ごと WAV が既に存在する」前提を自動的に満たすための補助レイヤー** として設計します。

### 2.3 現状の運用ポリシーと制約

- 本ドキュメントで想定している SofTalk / AquesTalk 連携は、あくまで
  **「ローカル環境でうまく動く場合に利用できる、任意の補助ツール」** という位置づけです。
- 実際の検証の結果、以下のような制約があることが分かっています。
  - インストール先ディレクトリ（`C:\Program Files` 配下かどうか）によって、
    設定ファイル (`SofTalk.ini` 等) の保存可否が変わる。
  - 録音時の読み上げ有無など、一部の設定が CLI 呼び出しだけでは確実に制御しづらい。
  - バージョンや環境設定により、ウィンドウの表示/非表示や終了方法の挙動が変わる。
- そのため、**CSV タイムラインモードの主フローは「CSV + WAV が揃っていること」だけを前提** とし、
  どの TTS エンジンで WAV を生成するかはユーザーの環境と好みに委ねる方針とします。
  - 例: YMM4（ゆっくりMovieMaker）で台本 CSV を読み込み、プロジェクト内で音声生成する。
  - 例: NotebookLM / 他クラウド TTS / AquesTalk Player 等で 001.wav, 002.wav... を作成する。
- `scripts/tts_batch_softalk_aquestalk.py` と本仕様は、
  - SofTalk / AquesTalk を使いたいユーザー向けの **テンプレ実装・上級者向けオプション** として維持し、
  - 将来、AquesTalk Player など他のローカル TTS への差し替えや追加を行う際の土台とします。

---

## 3. ファイル命名と行番号マッピングポリシー

### 3.1 基本ポリシー: 「行番号 → 連番ファイル名」

- タイムライン CSV の **データ行 (ヘッダ行を除く)** に対して、上から順に 1,2,3,... の行番号を割り当てる。
- 行番号 `n` に対応する音声ファイル名を **ゼロ埋め 3 桁** の `NNN.wav` とする。
  - 例:
    - 1 行目 → `001.wav`
    - 2 行目 → `002.wav`
    - 10 行目 → `010.wav`
- `audio_dir` 直下にこれらの WAV ファイルを配置する。
  - 例: `data/audio/episode01/001.wav`, `data/audio/episode01/002.wav`, ...

### 3.2 CSV 行と音声の対応ルール

- **ヘッダ行が存在する場合**
  - 1 行目がヘッダ (`Speaker,Text` 等) であるとみなし、2 行目以降をデータ行としてカウント。
  - データ行インデックス `i (0-based)` に対し、ファイル名は `i+1` 行目として `NNN.wav` を割り当てる。
- **空行・コメント行の扱い (推奨)**
  - 将来の実装では明示的なコメント記号 (`#` など) を導入する余地はあるが、
    現状は **CSV ローダーの解釈に依存** するため、簡易ルールを推奨します:
  - 「行が CSV ローダーによってセグメントとして解釈される限り、対応する WAV を生成する」
  - テキストが空の場合でも、**短い無音 (例: 0.2 秒)** の WAV を生成しておくと、
    行数ズレやエラーを防ぎやすい。

### 3.3 1000 行以上の拡張 (将来検討)

- 現状テストや運用想定では 3 桁 (`001.wav`〜`999.wav`) で十分と想定。
- 1000 行以上を扱うケースが増えた場合、下記いずれかのポリシーが必要:
  - `NNNN.wav` 形式に拡張する
  - 複数フォルダに分割する (`part01/001.wav` など)
- 当面は **3 桁固定** とし、拡張時は本ドキュメントを更新して SSOT とする。

---

## 4. TTS バッチスクリプトの仕様案

ここでは、将来的に追加する想定の TTS バッチスクリプト (例: `scripts/tts_batch_softalk_aquestalk.py`) の仕様を定義します。

### 4.1 コマンドラインインターフェイス案

```bash
python scripts/tts_batch_softalk_aquestalk.py \
  --engine softalk \
  --csv data/timeline.csv \
  --out-dir data/audio/timeline01 \
  [--voice-preset "female01"] \
  [--text-encoding utf-8] \
  [--dry-run]
```

- `--engine`
  - 使用する TTS エンジンを指定: `softalk` | `aquestalk` など。
- `--csv`
  - タイムライン CSV のパス (A 列=話者, B 列=テキスト)。
- `--out-dir`
  - 生成した WAV を保存するディレクトリ。存在しない場合は作成。
  - このディレクトリを、そのまま `run_csv_pipeline.py --audio-dir` に渡すことを想定。
- `--voice-preset`
  - SofTalk / AquesTalk 側での話者や声質、スピード等のプリセット名。
  - 実際のプリセット内容は別途設定ファイルで管理する想定。
- `--text-encoding`
  - TTS エンジンに渡すテキストファイルの文字コード (例: `shift_jis`, `utf-8`)。
  - SofTalk は Shift-JIS を前提とするケースが多いため、内部で変換が必要になる場合がある。
- `--dry-run`
  - 実際には TTS を実行せず、生成予定ファイル名やコマンドラインをログ出力のみ行う。

### 4.2 処理フロー (擬似コード)

```python
rows = load_timeline_csv(csv_path)  # ヘッダ除去済みのデータ行

for index, row in enumerate(rows, start=1):
    speaker = row.speaker
    text = row.text

    # 空行も含めて連番を維持する
    file_name = f"{index:03d}.wav"
    output_path = out_dir / file_name

    if dry_run:
        log_command(engine, text, output_path)
        continue

    # エンジンごとの呼び出し
    if engine == "softalk":
        run_softalk(text=text, output_path=output_path, voice_preset=voice_preset)
    elif engine == "aquestalk":
        run_aquestalk(text=text, output_path=output_path, voice_preset=voice_preset)
    else:
        raise ValueError(f"Unsupported engine: {engine}")
```

> ポイント: **行番号とファイル名の対応を一切崩さない** ことが最重要。
>
> - 途中で特定行だけをスキップすると、CSV ローダーとの対応が崩れる可能性があります。

### 4.3 SofTalk / AquesTalk 呼び出しイメージ

実際のコマンドラインは環境ごとに異なるため、ここではあくまでイメージのみ記載します。

- **SofTalk (例)**

  ```bash
  "C:/Program Files/Softalk/SofTalk.exe" \
    /T:voice_preset \
    /R:"C:/out/001.wav" \
    /W:"こんにちは"
  ```

- **AquesTalk (例)**

  ```bash
  "C:/Program Files/AquesTalk/AquesTalkPlayer.exe" /t "こんにちは" /o "C:/out/001.wav" /s speed /v voice
  ```

実装時には、これらのコマンドライン引数を **設定ファイルや環境変数で外部化** し、
スクリプト内では「エンジン名 + パラメータ」レベルまでに抽象化することを推奨します。

---

## 5. CSV パイプラインとの連携

### 5.1 CLI 連携

1. 先に TTS バッチスクリプトを実行

   ```bash
   python scripts/tts_batch_softalk_aquestalk.py \
     --engine softalk \
     --csv data/timeline.csv \
     --out-dir data/audio/timeline01
   ```

2. 生成された `data/audio/timeline01` を `run_csv_pipeline.py` に指定

   ```bash
   python scripts/run_csv_pipeline.py \
     --csv data/timeline.csv \
     --audio-dir data/audio/timeline01 \
     --export-ymm4
   ```

- これにより、
  - CSV → 行ごと WAV → CSV パイプライン → YMM4 プロジェクト
  という一連のフローがスクリプト 2 ステップで再現可能になります。

### 5.2 API 連携 (メモレベル)

- `/api/v1/pipeline/csv` 自体は **既に行ごと WAV が存在する前提** のエンドポイントです。
- ローカル環境から API ベースで操作する場合の一例:
  1. ローカルスクリプトで SofTalk/AquesTalk バッチを実行し、`audio_dir` を生成
  2. そのパスを API リクエストボディの `audio_dir` として指定

現時点では、API 内に SofTalk/AquesTalk を直接呼び出す機能は組み込まない想定です。

---

## 6. テスト戦略

### 6.1 バッチスクリプト単体テスト

- **目的**: TTS エンジンを実際に呼び出さなくても、以下を検証できるようにする。
  - CSV 行 → ファイル名 (`NNN.wav`) のマッピングが正しいこと
  - コマンドライン生成ロジックが想定どおりであること

- アプローチ案:
  - SofTalk / AquesTalk の実行部分 (`run_softalk`, `run_aquestalk`) をモックまたはテストダブルに置き換える。
  - テスト用の小さな CSV (2〜3 行) を用意し、`--dry-run` またはモック実行で、
    - 生成されるはずのファイル名一覧
    - ログに出力されるコマンドライン
    を検証する。

### 6.2 CSV パイプラインとの統合テスト (軽量)

- 手順例:
  1. テスト用ディレクトリに短い CSV (`timeline.csv`) を生成
  2. ダミー TTS 実装で、所定のディレクトリに `001.wav`, `002.wav`, ... を生成
     - 実際には `_create_silent_wav` のようなユーティリティで **無音 WAV** を生成すればよい
  3. `run_csv_pipeline.py` または `ModularVideoPipeline.run_csv_timeline` を、
     - `csv_path=timeline.csv`
     - `audio_dir=<上記ディレクトリ>`
     で実行
  4. 正常終了し、`slides_payload` / YMM4 エクスポートが成功することを確認

既存の `tests/test_csv_pipeline_mode.py` は、2)〜4) の統合テストに相当する部分を既に持っているため、
TTS バッチは主に **前段の補助ツール** として、別テストファイルでカバーする方針が自然です。

---

## 7. 今後の拡張アイデア (メモ)

- **話者ごとの声質切り替え**
  - A 列の話者名 (`Speaker1`, `Narrator` など) に応じて、
    SofTalk / AquesTalk のプリセットをマッピングするテーブルを導入。
- **読み仮名カラムの追加**
  - CSV に `Reading` カラムを追加し、
    - 画面表示用テキスト (難しい漢字を含む) と
    - 音声合成用の読み仮名テキスト
    を分離する運用。
- **エラー時のリトライ・スキップ戦略**
  - 特定行の合成に失敗した場合の扱い (再試行 / 無音で代替 / 例外で停止 など) をポリシー化。

これらの詳細は、実装時に必要に応じて本ドキュメントを拡張していきます。
