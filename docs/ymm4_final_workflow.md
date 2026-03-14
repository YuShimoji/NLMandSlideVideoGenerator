# YMM4 最終ワークフロー

**最終更新**: 2026-03-14
**ステータス**: 要更新（スライド画像配置の方針未決定）

> Path A (YMM4一本化) が唯一の制作経路。MoviePy/Path Bは2026-03-08に完全削除済み。

---

## 1. ワークフロー概要

### 現行フロー（音声+字幕のみ）

```
[Python] CSV作成 (Web UI)
    ↓
[YMM4] NLMSlidePlugin CSVインポート + Voice生成
    ↓
[YMM4] プレビュー確認 → 動画出力 (Ctrl+Shift+E)
    ↓
最終 mp4
```

### スライド画像配置（SP-026 実装済み）

CSV 3列目に画像ファイルパス（絶対パス）を指定すると、ImageItemとしてタイムラインに自動配置される。
CSVフォーマット: `話者,テキスト,画像パス（省略可）`
詳細: `docs/ymm4_export_spec.md` セクション11参照。

---

## 2. 標準オペレーション手順 (SOP)

### Step 1: CSV作成

Web UIでCSVを作成し、YMM4投入データを生成する。

```powershell
streamlit run src/web/web_app.py
# ブラウザで「CSV Pipeline」を選択 → CSV入力 → 実行
```

出力先: `data/ymm4/ymm4_project_YYYYMMDD_HHMMSS/`

| ファイル | 内容 |
|---------|------|
| project.y4mmp | YMM4プロジェクト |
| timeline_plan.json | タイムライン計画 |
| slides_payload.json | スライド情報 |
| text/timeline.csv | 元CSVコピー |

### Step 2: YMM4でCSVインポート + Voice生成

**方法A: NLMSlidePlugin（推奨）**

1. YMM4を起動
2. メニュー「NLMSlidePlugin」>「CSVタイムラインをインポート」
3. `text/timeline.csv` を選択
4. 「音声を自動生成（ゆっくりボイス）」チェックボックスON
5. 「プレビュー」でCSV内容確認
6. 「インポート」で一括実行

**方法B: YMM4台本機能（手動）**

1. YMM4を起動
2. YMM4の台本機能でCSVを読み込み
3. 各セグメントにゆっくりボイスを手動割り当て

> 方法Aと方法Bは同等の結果を得られる。方法AはCSVインポートとVoice生成を一括処理する利便性がある。

### Step 3: 動画出力

1. タイムラインでプレビュー再生 → 音声とテキストの同期を確認
2. `ファイル > 動画出力`（Ctrl+Shift+E）でMP4生成

---

## 3. 音声生成の選択肢

| 手段 | 操作 | 自動化度 | 推奨場面 |
|------|------|----------|----------|
| NLMSlidePlugin Voice生成 | CSVインポート時にチェックボックスON | 半自動 | 大量セグメント |
| YMM4 台本機能 | YMM4 GUIで手動操作 | 手動 | 少量 or 細かい調整 |

---

## 4. AutoHotkey（PoC — 参考）

`ymm4_automation.ahk` がプロジェクトディレクトリに生成される。
YMM4起動→プロジェクト読み込み→書き出しダイアログまでを自動化するPoCだが、
NLMSlidePluginのCSVインポート機能が実装された現在、AHKの主要な用途は縮小している。

---

## 5. エラー時リカバリ

| 事象 | 対処 |
|------|------|
| Voice Speaker未検出 | NLMSlidePluginが自動フォールバック（Voiceなしインポート）。手動でYMM4台本機能を使用 |
| CSVインポートエラー | ダイアログ内ログタブ + `%LOCALAPPDATA%\NLMSlidePlugin\logs\csv_import_runtime.log` を確認 |
| 音声とテロップのずれ | YMM4 GUI上で調整、またはCSVのテキスト長を調整して再インポート |
| 動画出力フリーズ | YMM4再起動 → プロジェクト再読み込み → 出力のみ再実行 |

---

## 6. 関連ドキュメント

- `docs/ymm4_export_spec.md` — エクスポート仕様（セクション11: スライド配置ギャップ）
- `docs/e2e_verification_guide.md` — E2E手動検証ガイド
- `docs/PROJECT_ALIGNMENT_SSOT.md` — プロジェクト方針SSOT
- `docs/workflow_boundary.md` — Python/YMM4責務境界
