# テンプレート体系統合仕様 (SP-020 → SP-031)

## 概要

SP-020 (ymm4_template_diff) の機能を SP-031 (style_template) に統合し、テンプレート設定の SSOT を一本化する。

## 現状の重複

| 設定項目 | SP-020 (template_diff) | SP-031 (style_template) |
|---------|----------------------|----------------------|
| 字幕スタイル | subtitle_style (font_family等) | subtitle (font_size, y_position_ratio等) |
| 話者色 | speaker_colors (名前キー) | speaker_colors (インデックス配列) |
| タイミング | timing (fade_in_ms等) | timing (padding_seconds等) + crossfade |
| 音声 | audio (normalize, target_loudness) | なし |
| 背景 | background (type, color) | なし |

## 統合方針

### style_template.json に追加するセクション

```json
{
  "speaker_name_colors": {
    "ナレーター1": "#4a90d9",
    "ナレーター2": "#e94560",
    "default": "#FFFFFF"
  },
  "background": {
    "type": "solid",
    "color": "#1a1a2e"
  },
  "audio": {
    "normalize": true,
    "target_loudness": -16
  }
}
```

### 色割当の優先順位

1. `speaker_name_colors` に話者名が存在 → その色を使用
2. 存在しない → `speaker_colors` (インデックス配列) から循環割当

### 変更対象

| ファイル | 変更内容 |
|---------|---------|
| config/style_template.json | speaker_name_colors, background, audio セクション追加 |
| src/core/style_template.py | StyleTemplate に新フィールド追加 + get_speaker_color 拡張 |
| ymm4-plugin/.../StyleTemplateLoader.cs | 新セクション対応 + GetSpeakerColor に名前マッチ優先 |
| ymm4-plugin/.../CsvImportDialog.cs | GetSpeakerColor を名前優先ロジックに更新 |
| docs/ymm4_template_diff_guide.md | SP-031 への統合を記載、レガシー化 |

### SP-020 のステータス変更

- status: done → superseded
- supersededBy: SP-031
- 理由: style_template.json に全機能を統合

## Phase B 手動操作削減との関係

AHK スクリプト (scripts/generate_ymm4_ahk.py) は既に存在するが、現行の主フローは NLMSlidePlugin の CSV Import。AHK で CSV Import ダイアログの自動操作を追加することで、Phase B の手動操作をさらに削減可能。

## 後方互換

- config/ymm4_template_diff.json は残存 (削除しない)
- 新セクション (speaker_name_colors, background, audio) は全てオプショナル
- 未設定時は現行動作を維持
