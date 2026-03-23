# 統合検証チェックリスト

最終更新: 2026-03-18

全SP完了後の統合実機テスト項目。
基本E2Eは `e2e_verification_guide.md` (Step 1-6) を先に実施すること。

---

## 前提条件

- [ ] Python 3.11 + venv 環境構築済み
- [ ] YMM4 インストール済み + NLMSlidePlugin デプロイ済み
- [ ] Gemini API キー設定済み (.env GEMINI_API_KEY)
- [ ] Pexels API キー設定済み (.env PEXELS_API_KEY) ※任意
- [ ] `config/style_template.json` が存在する

---

## Pre-Flight チェック (自動)

実機テストの前に、Python 側の前提条件を自動検証する。

```bash
.\venv\Scripts\python.exe scripts/preflight_sp035.py
```

全項目 PASS であれば、YMM4 実機テストに進む。
WARN は画像パス不在（サンプルCSVの相対パス参照先が未配置）が主因で既知事項。

---

## A. 字幕テンプレート検証 (SP-030)

### テスト用CSV

```csv
れいむ,字幕テンプレート検証: 話者1の色です
まりさ,話者2は別の色で表示されるはずです
れいむ,再び話者1: 同じ色に戻ること
さとり,話者3は新しい色です
```

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| A1 | 字幕の表示位置 | 画面下部中央 (CenterBottom) | |
| A2 | フォントスタイル | ボールド + Border (縁取り) | |
| A3 | 話者色分け | 話者ごとに異なる色 (6色サイクル) | |
| A4 | 同一話者の色一貫性 | 同じ話者は同じ色 | |
| A5 | MaxWidth/WordWrap | 長文が画面幅内で折り返される | |

---

## B. BGMテンプレート検証 (SP-031)

### 準備

1. `config/style_template.json` の `bgm` セクションを確認:
   - `volume_percent`: 0〜100 (整数)
   - `fade_in_seconds` / `fade_out_seconds`: フェード秒数
   - `layer`: BGM配置レイヤー

2. CsvImportDialog の BGM 選択 UI でファイルを指定すること
   (テンプレートに file_path フィールドはない。UI で個別選択する設計)

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| B1 | BGMがタイムラインに配置される | AudioItem として先頭に配置 | |
| B2 | BGM音量 | style_template の volume_percent 値と一致 | |
| B3 | FadeIn | 開始時に指定秒数でフェードイン | |
| B4 | FadeOut | 終了時に指定秒数でフェードアウト | |
| B5 | BGMと音声の同時再生 | BGMが音声の背景として再生される | |

---

## C. ストック画像パイプライン検証 (SP-033 Phase 2)

### CLI でストック画像付きCSV生成

```bash
.\venv\Scripts\python.exe scripts/research_cli.py pipeline \
  --topic "量子コンピュータの基礎" \
  --auto-images \
  --duration 3
```

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| C1 | CLI が正常完了 | CSV ファイルが output_csv/ に生成 | |
| C2 | CSV の3列目に画像パス | `images/` 配下のファイル名 | |
| C3 | 画像ファイルが実在 | images/ に .jpg/.png が存在 | |
| C4 | Pexels/Pixabay ヒット率 | 50%以上のセグメントに画像あり | |
| C5 | 画像なし行のフォールバック | `source=none` → テキストスライド生成 | |

---

## D. AI画像生成検証 (SP-033 Phase 3)

> Gemini Imagen は無料枠に制限あり。クォータリセット後に実施。

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| D1 | ストック失敗 → AI画像フォールバック | `source=ai_generated` の行が存在 | |
| D2 | AI生成画像の品質 | 1024x1024 以上、テーマに関連 | |
| D3 | AI失敗 → テキストスライド | `source=text_slide` の行が存在 | |
| D4 | テキストスライドの品質 | タイトル + キーワード表示 | |

---

## E. Post-Voice Timeline Resync 検証 (SP-028)

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| E1 | Voice生成後のタイムライン | 各セグメントがWAV実尺に同期 | |
| E2 | VoiceItem.VoiceLength | WAVのサンプル長と一致 | |
| E3 | 後続アイテムのオフセット | 前セグメント終了+gap分ずれる | |
| E4 | 画像のLength | 対応する音声と同じ長さ | |

---

## F. Pre-Export 検証 (SP-031)

### CLI 実行

```bash
.\venv\Scripts\python.exe scripts/research_cli.py validate output_csv/latest.csv
```

オプション: `--template cinematic` (テンプレート指定), `--no-image-check` (画像存在チェック省略)

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| F1 | validate コマンド正常終了 | エラー0件 | |
| F2 | 画像パス存在チェック | 全参照パスが実在 | |
| F3 | アニメーション種別チェック | 許可リストのみ | |
| F4 | CSV形式チェック | 列数・エンコーディング正常 | |

---

## G. テキストオーバーレイ検証 (SP-052)

### 準備

1. Python でサンプル台本から overlay_plan.json を生成:

```python
from core.overlay.overlay_planner import OverlayPlanner
import json

script = json.load(open("output_csv/script.json", encoding="utf-8"))
planner = OverlayPlanner()
plan = planner.plan(script)
plan.save("output_csv/overlay_plan.json")
```

2. overlay_plan.json を CSV と同じディレクトリに配置

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| G1 | overlay_plan.json 生成 | セクション変更時に chapter_title エントリが生成される | |
| G2 | key_point 抽出 | key_points 配列から key_point エントリが生成される | |
| G3 | statistic 検出 | 数値表現を含むセグメントで statistic エントリが生成される | |
| G4 | source_citation 検出 | 「出典:」等の表現で citation エントリが生成される | |
| G5 | YMM4 TextItem 配置 | OverlayImporter が TextItem を Layer 7 に正しく配置 | |
| G6 | オーバーレイの視認性 | 章タイトル/キーポイントが字幕と重ならず可読 | |

---

## H. 全統合E2E (最終レンダリング)

上記 A〜G を含むCSVで YMM4 インポート → レンダリング → mp4 出力。

### 検証項目

| # | 確認項目 | 期待値 | 結果 |
|---|----------|--------|------|
| H1 | mp4ファイル生成 | 指定先に出力 | |
| H2 | 動画再生 | エラーなく最後まで再生 | |
| H3 | 字幕の色分け | 話者ごとに色が異なる | |
| H4 | BGM | 背景に BGM が再生される | |
| H5 | ストック画像 | セグメントに対応する画像が表示 | |
| H6 | アニメーション | 各種アニメが視覚的に確認可能 | |
| H7 | 音声同期 | テキストとボイスが一致 | |
| H8 | 総尺 | セグメント数に応じた適切な長さ | |
| H9 | テキストオーバーレイ | 章タイトル/キーポイントが表示される (SP-052) | |

---

## テスト画像の準備

e2e_baseline_test.csv は `slides/slide_0001.png` 等の相対パスで画像を参照する。
`samples/image_slide/slides/` に 1920x1080 の PNG 画像を配置すること。

プレースホルダー画像は以下で自動生成可能:

```bash
.\venv\Scripts\python.exe -c "
from PIL import Image, ImageDraw
colors = [(60,80,120),(80,120,60),(120,60,80)]
for i,c in enumerate(colors,1):
    img = Image.new('RGB',(1920,1080),c)
    d = ImageDraw.Draw(img)
    d.text((860,530),f'slide_{i:04d}',fill=(255,255,255))
    img.save(f'samples/image_slide/slides/slide_{i:04d}.png')
"
```

CSV バリデーションは `samples/image_slide/` をカレントディレクトリにして実行:

```bash
cd samples\image_slide
..\..\venv\Scripts\python.exe ..\..\scripts\research_cli.py validate e2e_baseline_test.csv
```

---

## テスト結果記録

```
実施日時: _______________
YMM4バージョン: _______________
NLMSlidePluginバージョン: _______________
style_template: default / cinematic / minimal

Pass: ___/___
Fail: ___
Skip: ___

備考:
```

---

## ブロッカー / 既知の制限

- Gemini Imagen: 無料枠 (日次制限あり)。クォータリセット後にセクション D を実施
- YMM4 DLL: ローカル YMM4 インストールが必要。CI 環境ではスキップ
- Pexels/Pixabay: API キーがない場合、ストック画像は全てフォールバック
