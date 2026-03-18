# サムネイルパイプライン統合仕様 (SP-037)

**最終更新**: 2026-03-18
**ステータス**: done (Phase 1 + Phase 2)

---

## 1. 目的

既存の `src/core/thumbnails/` をメインパイプラインに接続し、動画制作時にサムネイルを自動生成する。

### 1.1 現状 (As-Is → 解消済み)

- `src/core/thumbnails/template_generator.py` — テンプレートベースのサムネイル生成（実装済み）
- `src/core/thumbnails/ai_generator.py` — AI生成サムネイル（実装済み、CJKフォント対応）
- パイプライン (`research_cli.py pipeline`) から自動呼び出し（Phase 1 で接続済み）
- `--style` プリセットに連動したサムネイルスタイル選択（Phase 2 で実装）

### 1.2 目標 (To-Be)

```
research_cli.py pipeline --topic "..." --auto-images --style news
    ↓ (既存フロー)
output_csv/timeline.csv + images/
    ↓ (Phase 1: 自動生成)
output_csv/thumbnail.png  ← style に連動したスタイルで生成
```

---

## 2. 実装計画

### Phase 1: パイプライン接続 (done)

| 項目 | 内容 |
|------|------|
| 対象 | `scripts/research_cli.py` の `run_pipeline()` |
| 変更 | CSV生成後にサムネイル生成ステップを追加 |
| 入力 | ScriptBundle (トピック + キーワード) |
| 出力 | `output_csv/thumbnail.png` (1280x720) |
| フォールバック | 生成失敗時はスキップ（サムネイルなしは致命的でない） |
| CJKフォント | 6候補のフォールバックチェーン (`ai_generator.py`) |

### Phase 2: スタイル連携 (done)

| 項目 | 内容 |
|------|------|
| SP-036連携 | `resolve_thumbnail_style()` でプリセット→スタイルマッピング |
| SP-031連携 | style_template.json に `thumbnail` セクション追加 (3テンプレート) |
| CLIフラグ | `--generate-thumbnail` / `--no-generate-thumbnail` |

#### スタイルマッピング

| Script Preset (SP-036) | Thumbnail Style | 概要 |
|-------------------------|-----------------|------|
| `default` (汎用解説) | `modern` | ダークブルー + シアン、72pt |
| `news` (ニュース) | `classic` | 白背景 + オレンジ、64pt |
| `educational` (教育) | `educational` | ミッドナイトブルー + ライム、60pt |
| `summary` (まとめ) | `gaming` | ダークレッド + イエロー、68pt |

#### style_template.json thumbnail セクション

各テンプレート (default / cinematic / minimal) に以下のフィールドを追加:

```json
{
  "thumbnail": {
    "style": "modern",
    "bg_color": [26, 26, 46],
    "text_color": [255, 255, 255],
    "accent_color": [0, 255, 157],
    "font_size_title": 72,
    "font_size_subtitle": 36,
    "gradient": true
  }
}
```

---

## 3. 品質軸との対応

| 品質軸 | SP-037の貢献 |
|--------|-------------|
| 制作スピード | 手動サムネイル作成を排除 |
| 視覚的完成度 | テンプレートベースで一貫したデザイン |
| 一貫性/再現性 | 同一テンプレートなら同一品質 |

---

## 4. テスト

- `tests/test_thumbnail_generators.py`: 35件 (Phase 1: 23件 + Phase 2: 12件)
  - `TestThumbnailStyleMapping`: マッピング正当性 7件
  - `TestStyleTemplateThumbnailSection`: style_template thumbnail セクション 5件
