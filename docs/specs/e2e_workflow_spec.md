# E2E 一気通貫ワークフロー仕様

SP-050 | Status: partial | Updated: 2026-03-22

---

## 目的

トピック選定から YouTube 公開までの一気通貫ワークフローを定義する。
DESIGN_FOUNDATIONS.md Section 0（根本ワークフロー）に準拠する。

### 根本ワークフロー（DESIGN_FOUNDATIONS.md Section 0 より）

```
NotebookLM       NotebookLM         Gemini          Python          YMM4
ソース投入 →     Audio Overview →   構造化 →        CSV組立 →       音声+動画
                 音声生成            (speaker/text)   素材調達         レンダリング
                    ↓                                スライド生成
              NotebookLM に                          (Google Slides)
              音声を再投入                            バリデーション
                    ↓
              テキスト化
```

---

## Phase 0: トピック選定 + ソース準備

**実行者**: 人間
**所要時間目標**: ?分

### 入力
- ニュース、テーマ、関心事項

### 成果物

| 成果物 | 形式 | 説明 |
|---|---|---|
| ソース群 | URL / テキスト / PDF | NotebookLM に投入する素材 |

### 確定事項

- **Q0-1 確定**: トピック選定は InoReader/RSS + NotebookLM 探索の2系統。
  - パターン1: 人間が RSS を見ながら面白そうな記事を発見 → NotebookLM Research → 台本生成
  - パターン2: パターン1の一部を自動化（将来）
- **Q0-2 確定**: Python の Brave Search リサーチは **廃止**。ソース投入は全て人間が NotebookLM に直接行う。
- **制作フロー確定**: リサーチ + 台本選定は数本分を一気に行い、GUI で AI 評価しつつ制作者が最終決定。Go したラインのみ YMM4 に投入。

---

## Phase 1: NotebookLM Audio Overview 生成

**実行者**: NotebookLM (人間操作)
**所要時間目標**: ?分

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| ソース群 | URL / テキスト / PDF | Phase 0 |

### 操作手順

1. NotebookLM にソースをアップロード
2. Audio Overview を生成
3. 音声ファイルをダウンロード

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| Audio Overview 音声ファイル | MP3 or WAV | ? |

### 確定事項

- **Q1-2 確定**: 音声ファイルはトピック別ディレクトリ (`data/topics/{topic_id}/audio/`) に保存。

### 未決定事項（実際に制作して確認）

> **Q1-1**: Audio Overview の生成パラメータ（尺・話者数・スタイル）は調整可能か？
> NotebookLM の Audio Overview の設定オプションを実際に確認する必要がある。

---

## Phase 2: NotebookLM テキスト化

**実行者**: NotebookLM (人間操作)
**所要時間目標**: ?分

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| Audio Overview 音声ファイル | MP3 or WAV | Phase 1 |

### 操作手順

1. NotebookLM に音声ファイルを再投入
2. NotebookLM がテキスト化（文字起こし）
3. テキストをコピーしてファイルとして保存

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| 台本テキスト | テキストファイル (.txt) | ? |

### 確定事項

- **Q2-1 確定**: テキスト化の出力形式は **プレーンテキスト**（話者区別なし）。Gemini が話者推定 + セグメント分割を行う。

---

## Phase 3: 台本構造化 (Gemini)

**実行者**: Python (自動 — Gemini API)
**所要時間目標**: 1-2分

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| 台本テキスト | テキストファイル (.txt) | Phase 2 |

### 処理内容

1. NotebookLM テキストを Gemini API に送信
2. Gemini が speaker / text / key_points を分離・構造化
3. セグメント粒度を 15-25秒/セグメントに分割

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| 構造化台本 | JSON (segments[{speaker, text, key_points, ...}]) | `output_csv/script.json` |

### 品質ゲート

| チェック項目 | 基準 | 自動/手動 |
|---|---|---|
| セグメント数 | > 0 | 自動 |
| セグメント粒度 | 平均 15-25 秒/セグメント | 自動 |
| speaker 名 | 2名以上 | 自動 |
| text 非空 | 全セグメント | 自動 |

### Gemini の責務境界（重要）

Gemini は NotebookLM テキストの「構造化」のみを行う。
台本の内容・品質・対話構造を Gemini が「改善」「書き換え」してはならない。
NotebookLM テキストが得られない場合のみ、Gemini が台本を「生成」する（フォールバック、品質劣化を前提）。

---

## Phase 4: スライド生成 + 素材調達

**実行者**: Python (自動 — Google Slides API + 画像API)
**所要時間目標**: 2-5分

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| 構造化台本 | JSON | Phase 3 |
| スタイル設定 | style_template.json | config/ |

### 処理内容

1. Google Slides API でスライド画像を生成（テンプレートベース）
2. 著作権クリア画像を外部 API で調達 (Pexels → Pixabay → Wikimedia)
3. アニメーションタイプを自動割り当て

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| スライド画像 | PNG | `data/slides/` |
| 補助画像 | PNG/JPG | `data/images/` |

### 画像調達フォールバックチェーン

1. Google Slides API（スライド）
2. Pexels API（ストック画像）
3. Pixabay API（ストック画像）
4. Wikimedia Commons（著作権クリア画像）
5. PIL テキストスライド（最終フォールバック）

### 確定事項

- **Q4-1 確定**: Google Slides API テンプレートは **汎用1種** からスタート。必要に応じて増やす。

---

## Phase 5: CSV 組立 + バリデーション

**実行者**: Python (自動)
**所要時間目標**: 1分以内

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| 構造化台本 | JSON | Phase 3 |
| スライド画像 | PNG | Phase 4 |
| 補助画像 | PNG/JPG | Phase 4 |
| スタイル設定 | style_template.json | config/ |

### 処理内容

1. 構造化台本 + 画像 → 4列 CSV (speaker, text, image_path, animation_type)
2. メタデータ JSON 生成 (title, description, tags, chapters)
3. Pre-Export バリデーション実行

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| タイムライン CSV | 4列 CSV (UTF-8) | `output_csv/timeline.csv` |
| メタデータ | JSON | `output_csv/metadata.json` |
| バリデーションレポート | テキスト | stdout |

### Pre-Export バリデーション

| チェック項目 | 基準 | 自動/手動 |
|---|---|---|
| CSV フォーマット | 4列、UTF-8、speaker/text 非空 | 自動 |
| 画像パス存在 | 全 image_path が実在するファイル | 自動 |
| セグメント粒度 | 平均 15-25 秒/セグメント | 自動 |
| animation_type | 8種のいずれか | 自動 |
| speaker 名 | YMM4 ボイスにマッピング可能 | 自動 |

---

## Phase 6: YMM4 インポート + 制作

**実行者**: YMM4 + 人間
**所要時間目標**: 5分（ほぼノータッチ）+ レンダリング時間

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| タイムライン CSV | 4列 CSV | Phase 5 |
| 画像セット | PNG/JPG | Phase 4-5 |

### 操作手順

1. YMM4 起動
2. NLMSlidePlugin → CSV インポート
3. ボイス自動生成（VoiceSpeakerDiscovery）
4. プレビュー再生で最初30秒を確認
5. 動画出力 → MP4

### 成果物

| 成果物 | 形式 | 保存先 |
|---|---|---|
| 最終動画 | MP4 (H.264 + AAC, 1920x1080) | ユーザー指定 |

### 確定事項

- **Q6-1 確定**: YMM4 プロジェクトテンプレートは **既存のものがある**。

### 未決定事項

> **Q6-2**: レンダリング時間の実測値は？ 実際に制作して計測する。

---

## Phase 7: 後処理 + YouTube 公開

**実行者**: Python + 人間
**所要時間目標**: 5-10分

### 入力

| 入力 | 形式 | 提供元 |
|---|---|---|
| MP4 | H.264 + AAC | Phase 6 |
| metadata.json | JSON | Phase 5 |

### 処理内容

1. MP4 品質検証 (FFprobe: 解像度・コーデック・再生時間)
2. サムネイル準備
3. YouTube アップロード (private → 確認後 public)
4. YouTube Studio で最終確認

### 成果物

| 成果物 | 形式 |
|---|---|
| 検証済み MP4 | MP4 |
| サムネイル | PNG/JPG (1280x720, < 2MB) |
| YouTube URL | URL |

### 確定事項

- **Q7-1 確定**: サムネイルは **人間作成テンプレート → AI 自動生成**。完全手動ではない。テンプレートベースの自動化。
- **Q7-2 確定**: メタデータは AI が台本生成時に生成 → Python が抽出・整形 → 人間が最終編集・確定。

---

## 横断的な確定事項

### 制作フロー（確定 2026-03-22）

制作は以下の2段階に分離する:

**選定フェーズ（バッチ）**:
- リサーチ + 台本選定を数本分一気に実施
- GUI で AI 評価しつつ制作者が最終決定
- Go / No-Go を判定

**制作フェーズ（個別）**:
- Go したラインのみ Phase 3-7 を実行
- YMM4 レンダリング中に次のラインの Phase 3-5 を進めることは可能

### 制作ペース（見直し 2026-03-22）

「一晩3本」を強い SSOT として扱わない。制作ペースは結果指標であり、品質を優先する。

> **Q-X1**: 各フェーズの目標時間は参考値として設定するか、それとも時間目標自体を設けないか？

### 成果物管理（確定 2026-03-22）

**トピック別ディレクトリ方式**を採用。

```
data/topics/{topic_id}/
  ├── sources/          # NotebookLM に投入したソース（参考保存）
  ├── audio/            # Audio Overview 音声ファイル
  ├── transcript/       # テキスト化された台本
  ├── script.json       # Gemini 構造化台本
  ├── slides/           # Google Slides 画像
  ├── images/           # 素材画像
  ├── output_csv/       # timeline.csv + metadata.json
  └── final/            # MP4 + サムネイル
```

---

## 現行コードとのギャップ

| 項目 | 現行コード | この仕様 |
|---|---|---|
| 台本入力 | Gemini が「生成」 | NotebookLM テキストを受入 → Gemini が「構造化」 |
| NotebookLM テキスト投入 | 経路なし | テキストファイル指定 or テキスト貼り付け |
| Brave Search リサーチ | 実装済み (source_collector.py) | 廃止。NotebookLM に人間が直接ソース投入 |
| スライド | PIL 自動生成 (708行) | Google Slides API |
| YMM4 手動調整 | 未定義 | ほぼノータッチ (5分目標) |
| 成果物管理 | output_csv/ に一括出力 | トピック別ディレクトリ |
| 制作フロー | 1本ずつ直列 | 選定バッチ + 個別制作の2段階 |
| 制作ペース | 「一晩3本」が SSOT | 品質優先。ペースは結果指標 |
| メタデータ | Python 自動生成のみ | AI台本時生成 → Python抽出 → 人間編集 |

---

## SP-045 との関係

SP-045 (初回公開チェックリスト) は本仕様の確定後に更新する。
SP-050 = 仕様定義（何をするか）、SP-045 = 実行チェックリスト（どう実行するか）。
