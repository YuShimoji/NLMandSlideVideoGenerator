# YMM4 テンプレート差分適用ガイド

最終更新: 2025-12-01

---

## 概要

YMM4プロジェクト生成時に、テンプレートファイルに対して差分設定を適用することで、
字幕スタイル・背景色・話者ごとの色分けなどをカスタマイズできます。

---

## 設定ファイル

### 設定ファイルの場所

差分設定は以下の優先順位で読み込まれます:

1. **環境変数 `YMM4_TEMPLATE_DIFF`** - JSON文字列を直接指定
2. **環境変数 `YMM4_TEMPLATE_DIFF_FILE`** - 設定ファイルのパスを指定
3. **`config/ymm4_template_diff.json`** - デフォルト設定ファイル

### 設定ファイルの例

```json
{
  "subtitle_style": {
    "font_family": "Meiryo UI",
    "font_size": 48,
    "font_color": "#FFFFFF",
    "outline_color": "#000000",
    "outline_width": 2,
    "position": "bottom",
    "margin_bottom": 50
  },
  
  "background": {
    "type": "solid",
    "color": "#1a1a2e"
  },
  
  "speaker_colors": {
    "Speaker1": "#4a90d9",
    "Speaker2": "#e94560",
    "ナレーター1": "#4a90d9",
    "ナレーター2": "#e94560",
    "default": "#FFFFFF"
  },
  
  "timing": {
    "fade_in_ms": 200,
    "fade_out_ms": 200,
    "slide_transition_ms": 300
  },
  
  "audio": {
    "normalize": true,
    "target_loudness": -16
  }
}
```

---

## 設定項目

### `subtitle_style` - 字幕スタイル

| キー | 型 | 説明 |
|------|-----|------|
| `font_family` | string | フォント名 |
| `font_size` | number | フォントサイズ（ピクセル） |
| `font_color` | string | フォント色（#RRGGBB） |
| `outline_color` | string | アウトライン色 |
| `outline_width` | number | アウトライン幅 |
| `position` | string | 位置（`top`, `center`, `bottom`） |
| `margin_bottom` | number | 下マージン（ピクセル） |

### `background` - 背景設定

| キー | 型 | 説明 |
|------|-----|------|
| `type` | string | `solid` / `gradient` / `image` |
| `color` | string | 背景色（#RRGGBB） |

### `speaker_colors` - 話者ごとの色

CSVの話者名をキーとして、対応する色を指定します。

```json
{
  "Speaker1": "#4a90d9",
  "Speaker2": "#e94560",
  "default": "#FFFFFF"
}
```

`default` は未定義の話者に適用されます。

### `timing` - タイミング設定

| キー | 型 | 説明 |
|------|-----|------|
| `fade_in_ms` | number | フェードイン時間（ミリ秒） |
| `fade_out_ms` | number | フェードアウト時間（ミリ秒） |
| `slide_transition_ms` | number | スライド切り替え時間 |

### `audio` - 音声設定

| キー | 型 | 説明 |
|------|-----|------|
| `normalize` | boolean | 音量正規化 |
| `target_loudness` | number | 目標ラウドネス（LUFS） |

---

## 使用方法

### 方法1: デフォルト設定ファイルを編集

`config/ymm4_template_diff.json` を直接編集します。

### 方法2: 環境変数でファイルを指定

```bash
export YMM4_TEMPLATE_DIFF_FILE=/path/to/my_custom_diff.json
python scripts/run_csv_pipeline.py --csv ... --audio-dir ... --export-ymm4
```

### 方法3: 環境変数でJSON直接指定

```bash
export YMM4_TEMPLATE_DIFF='{"subtitle_style": {"font_size": 36}}'
python scripts/run_csv_pipeline.py --csv ... --audio-dir ... --export-ymm4
```

---

## 出力

差分適用後の設定は、YMM4プロジェクトディレクトリ内に
`template_diff_applied.json` として保存されます。

```
ymm4_project_YYYYMMDD_HHMMSS/
├── project.y4mmp           # YMM4プロジェクトファイル
├── template_diff_applied.json  # 適用された差分設定
├── timeline_plan.json      # タイムライン情報
├── slides_payload.json     # スライドデータ
├── audio/
│   ├── segments/           # 行ごとの音声
│   └── combined.wav        # 結合音声
└── text/
    └── timeline.csv        # 元CSV
```

---

## 関連ドキュメント

- [YMM4エクスポート仕様](ymm4_export_spec.md)
- [CSV入力フォーマット仕様](spec_csv_input_format.md)
- [手動素材ワークフローガイド](user_guide_manual_workflow.md)
