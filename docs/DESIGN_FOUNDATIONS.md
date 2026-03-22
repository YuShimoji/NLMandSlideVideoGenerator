# DESIGN FOUNDATIONS

Updated: 2026-03-22
Status: Active
Authority: 全仕様・全ワークフロー文書の上位に位置する設計公理

---

## 目的

この文書は、NLMandSlideVideoGenerator の制作プロセスにおける設計前提を明文化する。

**重要**: 本文書の Section 0 は、プロジェクト開始時から存在する根本仕様である。
他の全仕様・全コードは、この根本仕様に準拠しなければならない。

---

## 0. 根本ワークフロー（プロジェクト開始時からの前提）

このプロジェクトの制作プロセスは、以下の一気通貫フローである:

```
NotebookLM       NotebookLM         Gemini          Python          YMM4
ソース投入 →     Audio Overview →   構造化 →        CSV組立 →       音声+動画
                 音声生成            (speaker/text)   素材調達         レンダリング
                    ↓                                画像取得
              NotebookLM に                          バリデーション
              音声を再投入
                    ↓
              テキスト化
              (文字起こし)
```

### ステップ詳細

| # | ステップ | 実行者 | 入力 | 出力 |
|---|---|---|---|---|
| 1 | ソース投入 | 人間 | URL、テキスト、PDF等 | NotebookLM ノートブック |
| 2 | Audio Overview 生成 | NotebookLM | ノートブック内のソース群 | 音声ファイル（ポッドキャスト形式の対話） |
| 3 | 音声の再投入 + テキスト化 | NotebookLM | Step 2 の音声ファイル | テキストファイル（対話の文字起こし） |
| 4 | 台本構造化 | Gemini API | Step 3 のテキスト | 構造化 JSON (speaker, text, ...) |
| 5 | スライド生成 | Google Slides API | Step 4 の台本内容 | スライド画像 (PNG) |
| 6 | 素材調達 | Python + 外部API | Step 4 の台本内容 | 著作権クリア画像群 |
| 7 | CSV 組立 | Python | Step 4 + Step 5 + Step 6 | 4列 CSV + metadata.json |
| 8 | YMM4 インポート + 制作 | YMM4 + 人間 | Step 7 の CSV + 画像 | 最終 MP4 |
| 9 | 後処理 + 公開 | Python + 人間 | Step 8 の MP4 | YouTube 公開 |

### このワークフローの核心

- **台本品質は NotebookLM が生成する**。Gemini は台本を生成しない。Gemini は NotebookLM のテキスト出力を CSV 用に構造化するだけ。
- **Gemini の台本「生成」は、NotebookLM テキストが得られない場合のフォールバック**であり、品質目標を下げて使う。
- **Python は品質を生成しない。品質を通過させる。** CSV 組立・素材調達・バリデーションが責務。

### 歴史的経緯

この根本ワークフローは `docs/workflow_specification.md` (Step 2.1.2-2.1.3) に記載されていた。
2025-11-26 commit `b78d25e` で Gemini が「NotebookLM の代替」として導入された際、
元のワークフローが暗黙的に放棄された。DECISION LOG にこの放棄は記録されなかった。
2026-03-22 に根本仕様として復元し、本文書に記録する。

---

## 1. 制作プロセスの三層モデル

```
[入力層: NotebookLM]  →  [変換層: Python + Gemini]  →  [出力層: YMM4]
  音声生成 + テキスト化     台本構造化 (Gemini)          音声合成
  台本品質の源泉            CSV組立・素材調達             動画レンダリング
                           スライド生成 (Google Slides)   字幕・キャラ配置
                           バリデーション
                           メタデータ生成
```

### 各層の責務原則

- **入力層 (NotebookLM)**: コンテンツの品質を決定する。Audio Overview → テキスト化により、対話構造・テンポ・個性を持つ高品質台本を生成する。
- **変換層 (Python + Gemini)**: データ変換と橋渡しを行う。Gemini は NotebookLM テキストの構造化（speaker/text 分離）を担う。Python は CSV 組立・素材調達・バリデーションを担う。品質を生成しない。
- **出力層 (YMM4)**: 最終的な視聴覚品質を決定する。音声合成・動画レンダリング・字幕配置はこの層の責務。

### 設計判断の基準

新しい機能や改善を検討する際、まず「どの層の責務か」を判定すること。
Python 変換層に品質生成の責務を持たせてはならない。

---

## 2. NotebookLM が提供するもの（Python が再実装しないもの）

### NotebookLM の能力

| 能力 | NotebookLM の具体的な提供物 | Python が担わないこと |
|---|---|---|
| 音声生成 | Audio Overview（ポッドキャスト形式の自然な対話音声） | 音声の生成・TTS |
| テキスト化 | 音声ファイルの高精度文字起こし | 音声からテキストへの変換 |
| 台本品質 | 対話構造・フック・テンポ・個性・視聴者を引きつける話し方 | 対話品質そのものをプロンプトで生成すること |
| ソース統合 | マルチソース理解・要約・引用の自然な統合 | ソースの品質理解・要約品質の生成 |

### Gemini の正しい役割

Gemini は台本を「生成」するのではなく、NotebookLM のテキスト出力を「構造化」する:
- NotebookLM テキスト → Gemini → 構造化 JSON (speaker, text, key_points, ...)
- フォールバック: NotebookLM テキストが得られない場合のみ、Gemini が台本を「生成」する（品質は劣る前提）

### 現在の API 制約 (2026-03-22時点)

- **Enterprise API**: 存在するが有料ライセンスが必要
- **スライド生成 API**: 公式未提供 (Web UI機能のみ)
- **非公式ライブラリ (notebooklm-py)**: 存在するが安定性未検証

暫定運用:
- Step 1-3 (ソース投入 → Audio Overview → テキスト化) は NotebookLM Web UI で手動実行
- Step 4 (台本構造化) は Gemini API で自動実行
- Step 5 (スライド生成) は Google Slides API で自動実行

### コードの過剰実装マップ

| ファイル | 現状の誤り | あるべき姿 |
|---|---|---|
| `src/notebook_lm/gemini_integration.py` | Gemini で台本を「生成」している | NotebookLM テキストの「構造化」に限定。テキスト未提供時のフォールバック生成 |
| `src/core/visual/text_slide_generator.py` (708行) | PIL でスライドを生成 | Google Slides API に移行。PIL はフォールバックのみ |
| `src/notebook_lm/audio_generator.py` | 無音 WAV プレースホルダー生成 | レガシースタブ。音声は NotebookLM → YMM4 の責務 |
| `src/core/providers/script/notebook_lm_provider.py` | 名前のみ NotebookLM、実態は Gemini | NotebookLM テキスト投入 → Gemini 構造化のパイプラインに変更 |

---

## 3. YMM4 が提供するもの（Python が再実装しないもの）

### YMM4 の能力と Python の関係

| 能力 | YMM4 の提供物 | Python 側の責務 |
|---|---|---|
| 音声合成 | ゆっくりボイス (話者選択・感情・速度) | CSV speaker列で話者名を指定するのみ |
| 動画レンダリング | H.264 MP4 エンコード | 素材 (画像/CSV) の準備まで |
| 字幕配置 | テキストオーバーレイ (位置・色・フォント) | style_template.json で設定を渡すのみ |
| キャラアニメーション | 立ち絵・リップシンク・モーション | 不要 (YMM4内完結) |
| トランジション | フェード・ワイプ・カット等 | CSV animation_type列で種別を指定するのみ |
| 多層構成 | 背景+キャラ+テキスト+画像の多層レイヤー | 不要 (YMM4内完結) |

### ユーザーがYMM4側で設定すべき項目

Python パイプラインは CSV と素材を生成するが、最終品質は YMM4 側の設定で決まる。

1. **プロジェクトテンプレート**: 解像度 1920x1080、FPS 30/60、サンプルレート 48000Hz
2. **話者とボイスの対応付け**: CSV speaker列 → YMM4 ボイスプリセット
3. **キャラクタースプライト** (使用する場合): 立ち絵配置・表情・リップシンク
4. **BGM設定**: style_template.json bgm セクション。最終調整は YMM4 側
5. **エクスポート品質**: ビットレート・エンコーダ設定

### サムネイル

YMM4 テンプレートベースで作成する (DECISION 2026-03-21)。
PIL ベースのサムネイル生成はフォールバックに格下げ。

### YMM4 作業時間目標

CSV インポート後はほぼノータッチ（目標: 5分以内）。
「一晩3本」ペースの実現には、YMM4 手動調整を最小化する必要がある。

---

## 4. Python 変換層の責務境界

### やること (正当な責務)

| 責務 | 内容 | 主要コード |
|---|---|---|
| NotebookLM テキスト受入 | テキストファイル or テキスト貼り付けを受け取る | 新規実装が必要 |
| 台本構造化 (Gemini) | NotebookLM テキスト → 構造化 JSON | `src/notebook_lm/gemini_integration.py` (役割変更) |
| スライド生成 (Google Slides) | 台本内容からスライド画像を自動生成 | `src/slides/google_slides_client.py` (拡張) |
| 素材調達 | 著作権クリア画像の検索・取得 | `src/core/visual/stock_image_client.py` |
| CSV 組立 | speaker, text, image_path, animation_type の4列CSV | `src/core/csv_assembler.py` |
| バリデーション | Pre-Export検証、セグメント粒度チェック | `src/core/validation/` |
| メタデータ | YouTube用タイトル・説明・タグの生成 | `src/youtube/` |
| YMM4 連携 | .y4mmp プロジェクトファイル生成 | `src/core/editing/ymm4_backend.py` |

### やらないこと (他の層の責務)

| やらないこと | 正しい担当 |
|---|---|
| 台本の品質生成 | NotebookLM (Audio Overview → テキスト化) |
| 音声合成 | YMM4 |
| 動画レンダリング | YMM4 |
| スライドの視覚品質生成 (PIL) | Google Slides API に移行 |
| サムネイルの最終品質 | YMM4 テンプレート + 人間レビュー |

---

## 根本原因記録: なぜこの文書が必要になったか

### 問題

プロジェクト開始時の根本ワークフロー（NotebookLM → 音声 → テキスト化 → 整形 → YMM4）が、
AI セッションの蓄積により暗黙的に上書きされた。

### 経緯

1. 根本ワークフローは `docs/workflow_specification.md` (Step 2.1.2-2.1.3) に存在していた
2. 2025-11-26: Gemini が「NotebookLM の代替」として導入 (commit b78d25e)
3. 以降のセッションで Gemini が「台本生成の主手段」に昇格
4. DECISION LOG にはこの移行が「NotebookLM の放棄」として記録されなかった
5. 48仕様が Gemini 前提で積み上がり、根本ワークフローとの乖離が拡大
6. 2026-03-19: ドリフト分析で NotebookLM の消失を検出。ただし具体的なワークフロー（audio→text）は復元されなかった
7. 2026-03-22: ユーザー指摘により根本ワークフローを再発見・復元

### 教訓

- AI セッション間で「根本前提」が継承されない場合、代替手段が本流に昇格するドリフトが発生する
- DECISION LOG は「何を採用したか」だけでなく「何を放棄したか」も記録すべき
- 48仕様の整合性チェックでも、根本前提の喪失は検出できなかった

---

## 参照関係

- `docs/workflow_specification.md` — 元のワークフロー定義（Step 2.1.2-2.1.3）
- `docs/notebooklm_drift_analysis.md` — NotebookLM→Gemini ドリフトの検出と原因分析
- `docs/video_quality_diagnosis.md` — 出力品質問題の根本原因 = 「コードで全てを解決する前提」
- `docs/workflow_boundary.md` — Python内部の責務分離

この文書の変更は HUMAN_AUTHORITY に該当する。
