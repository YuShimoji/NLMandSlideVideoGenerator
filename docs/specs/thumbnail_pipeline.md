# サムネイルパイプライン統合仕様 (SP-037)

**最終更新**: 2026-03-23
**ステータス**: partial (Phase 1-3 done, Phase 4 実装中 — Gemini文言生成+色彩プリセット+バリエーション生成+パイプライン統合 done, テンプレート作成待ち)
**補足資料**: [thumbnail_pattern_analysis.md](thumbnail_pattern_analysis.md) — YouTube解説動画サムネイルの成功パターン分析

---

## 1. 目的

既存の `src/core/thumbnails/` をメインパイプラインに接続し、動画制作時にサムネイルを自動生成する。

### 1.1 現状 (As-Is → 解消済み)

- `src/core/thumbnails/template_generator.py` — 削除済み (Phase 3 でYMM4テンプレートベースに転換)
- `src/core/thumbnails/ai_generator.py` — 削除済み (Phase 3 でYMM4テンプレートベースに転換)
- `src/core/thumbnails/ymm4_thumbnail_generator.py` — 現行のサムネイル生成 (PILフォールバック付き)
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
| CJKフォント | 6候補のフォールバックチェーン |

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

### Phase 3: YMM4テンプレートベースのサムネイル生成 (実装済み)

**方向転換 (2026-03-21)**:
PIL直接描画のサムネイルはYouTube公開水準に達しない。
特にゆっくり解説界隈には「売れるサムネイル」のパターンがあり、
ストック素材+文字程度では視聴者のクリックを得られず、プロジェクト全体が頓挫する。

#### 方針決定事項
- PILベースのサムネイル生成は**プレースホルダー/フォールバック**に格下げ
- 最終品質のサムネイルは**ユーザーがYMM4上で作成したテンプレート**をベースに生成
- テンプレート化しつつバラエティを出すことが重要
- サムネイル上の文字配置は自動生成では品質不足（微細なズレが違和感を生む）
- 動画制作者による最終レビューが必須

#### 確定事項 (2026-03-21)
- **ワークフロー**: YMM4の.y4mmプロジェクトとしてサムネイルテンプレートを作成。パイプラインがテキスト/画像を差し替えた.y4mmpを出力。YMM4で開いて1フレーム書き出し+レビュー
- **可変要素**: 以下の全てが動画ごとに差し替え対象
  1. タイトルテキスト（煽り文句）
  2. 背景画像/素材（テーマに合わせた差し替え）
  3. キャラクター配置（ゆっくりキャラの表情・ポーズ）
  4. 配色/アクセント（動画テーマに合わせた色味）
- **テンプレートバリエーション**: ユーザーが複数パターンを事前作成。パイプラインがテンプレート選択+可変要素差し替えを実行

#### 実装 (2026-03-21)

| 項目 | 内容 |
|------|------|
| モジュール | `src/core/thumbnails/ymm4_thumbnail_generator.py` |
| クラス | `Ymm4ThumbnailGenerator` |
| テンプレート配置先 | `config/thumbnail_templates/*.y4mmp` |
| プレースホルダー形式 | `{{NAME}}` (大文字英字+アンダースコア) |
| パイプライン統合 | `research_cli.py` — YMM4テンプレート優先、PILフォールバック |
| テスト | `tests/test_ymm4_thumbnail_generator.py` (20件) |

#### プレースホルダー規約

| プレースホルダー | 対象 | 自動値 |
|------------------|------|--------|
| `{{TITLE}}` | TextItem.Text | 台本タイトル |
| `{{SUBTITLE}}` | TextItem.Text | 最初のセグメント (40文字切り詰め) |
| `{{BACKGROUND}}` | ImageItem.FilePath | ストック画像パス |
| `{{CHARACTER}}` | ImageItem.FilePath | キャラクター画像パス |

ユーザーが独自のプレースホルダーを追加可能（`{{CUSTOM_NAME}}` 形式）。
`list_placeholders()` でテンプレート内の全プレースホルダーを検出できる。

#### テンプレート素材

テンプレートと同名のディレクトリ (`config/thumbnail_templates/{name}/`) に
素材ファイル（オーバーレイ画像、フレーム等）を配置すると、
生成時に出力先ディレクトリに自動コピーされる。

#### テンプレート作成手順

1. YMM4を開き、1920x1080 / 30fps / 1フレーム のプロジェクトを作成
2. サムネイルのレイアウトをデザイン
   - 背景画像 (ImageItem) → FilePath に `{{BACKGROUND}}` と入力
   - キャラクター (ImageItem) → FilePath に `{{CHARACTER}}` と入力
   - タイトル文字 (TextItem) → Text に `{{TITLE}}` と入力
   - サブタイトル (TextItem) → Text に `{{SUBTITLE}}` と入力
3. プロジェクトを `config/thumbnail_templates/` に保存
4. `python scripts/research_cli.py pipeline --topic "..." --generate-thumbnail` で確認

#### 未確定事項 (HUMAN_AUTHORITY)
- キャラクター素材の管理方法（パス指定 / 事前配置）
- テンプレート選択ロジック（手動/自動/ランダム）
- 配色差し替えの具体的な実装方法

---

## 3. 品質軸との対応

| 品質軸 | SP-037の貢献 |
|--------|-------------|
| 制作スピード | テンプレートベースで手動サムネイル作成を最小化 |
| 視覚的完成度 | YMM4のフルレンダリング品質 + 人間レビュー |
| 一貫性/再現性 | テンプレートによるブランド統一 |
| バラエティ | 複数テンプレートパターンの切り替え |

---

---

## Phase 4: パターンベーステンプレートシステム (設計中)

**背景**: YouTube解説動画ジャンルにはサムネイルの確立された成功パターンが存在する。
視聴者の流入はサムネイルに大きく依存し、同じチャンネルでもサムネイルの品質差で
再生数が100倍以上変動する（実例: 地理解説チャンネルで98万 vs 2975）。

詳細分析: [thumbnail_pattern_analysis.md](thumbnail_pattern_analysis.md)

### 4.1 5つのレイアウトパターン

| パターン | 名前 | テンプレート名 | 主な用途 |
|---------|------|--------------|---------|
| A | 中央テキスト | `center_text` | ミステリー、謎、総集編 |
| B | 左画像+右テキスト | `left_image` | 時事、人物、歴史 |
| C | 地図+矢印 | `map_arrow` | 地理、地政学、インフラ |
| D | 縦分割 (2-4列) | `vertical_split` | 複数テーマ対比、哲学的問い |
| E | 数字+リスト | `number_list` | 総集編、ランキング、まとめ |

各パターンのYMM4テンプレート作成手順は補足資料 Section 5 に記載。

### 4.2 拡張プレースホルダー

Phase 3 の基本プレースホルダー (`{{TITLE}}`, `{{SUBTITLE}}`, `{{BACKGROUND}}`, `{{CHARACTER}}`) に加え、以下を追加:

| プレースホルダー | 対象 | 用途 |
|-----------------|------|------|
| `{{MAIN_TEXT}}` | TextItem.Text | フック文言 (5-12文字) |
| `{{SUB_TEXT}}` | TextItem.Text | 補足説明 (10-25文字) |
| `{{LABEL}}` | TextItem.Text | カテゴリ表示 |
| `{{ACCENT_IMAGE}}` | ImageItem.FilePath | 矢印、人物切り抜き等 |
| `{{OVERLAY}}` | ImageItem.FilePath | グラデーション、枠 |
| `{{IMAGE_1}}` ... `{{IMAGE_4}}` | ImageItem.FilePath | 縦分割用画像 |
| `{{SECTION_1}}` ... `{{SECTION_4}}` | TextItem.Text | 縦分割用見出し |
| `{{DETAIL_1}}` ... `{{DETAIL_4}}` | TextItem.Text | 縦分割用小テキスト |

### 4.3 色彩プリセット

テンプレートとは独立に、色彩をプリセットで制御する。
パイプラインが TextItem.FontColor / OutlineColor を JSON レベルで差し替え。

| プリセット名 | メインテキスト色 | 縁取り色 | 用途 |
|-------------|----------------|---------|------|
| `dark_red` | #FF0000 | #FFFFFF | 時事、衝撃、ミステリー |
| `dark_yellow` | #FFD700 | #CC0000 | 科学、発見、雑学 |
| `map_white` | #FFFFFF | #FF0000 | 地理、インフラ |
| `high_contrast` | #FFFFFF + #FF0000 | #000000 | テクノロジー、AI |
| `warm_alert` | #FFD700 | #FF4500 | 緊急ニュース |

### 4.4 Gemini サムネイル文言生成

台本からサムネイル用フック文言を自動生成する。
`GeminiIntegration` に `generate_thumbnail_copy()` メソッドを追加。

**入力**: 台本タイトル + 最初の3セグメント
**出力**:
```json
{
  "main_text": "なぜXは...",
  "sub_text": "驚きの理由が...",
  "label": "ゆっくり解説",
  "suggested_pattern": "C",
  "suggested_color": "dark_red"
}
```

プロンプトに成功パターンのフック構文を組み込む:
- 「なぜX？」「Xの正体」「Xの謎」「絶対にX」「XX選」

### 4.5 バリエーション生成 (A/Bテスト対応)

同一動画に対して複数のサムネイルバリエーションを生成:

```python
# Ymm4ThumbnailGenerator に追加
def generate_variants(
    self,
    template_name: str,
    output_dir: Path,
    base_replacements: dict[str, str],
    variant_texts: list[dict[str, str]],  # 文言バリエーション
    color_presets: list[str] | None = None,  # 色バリエーション
) -> list[Path]:
    """複数バリエーションの .y4mmp を生成する。"""
```

**CLI**:
```bash
# 3バリエーション生成
python scripts/research_cli.py pipeline --topic "..." --thumbnail-variants 3

# テンプレート一覧表示
python scripts/research_cli.py thumbnail-templates
```

### 4.6 JSON レベル色差し替え

YMM4 の .y4mmp は JSON 形式のため、TextItem のプロパティを直接差し替え可能。
`Ymm4ThumbnailGenerator` に色差し替えメソッドを追加:

```python
def apply_color_preset(
    self,
    project: dict,
    preset_name: str,
) -> dict:
    """色彩プリセットを適用する。
    TextItem の FontColor, OutlineColor, ShadowColor を差し替え。
    """
```

対象プロパティ:
- `TextItem.FontColor` (ARGB int or hex)
- `TextItem.OutlineColor`
- `TextItem.OutlineWidth`
- `TextItem.ShadowColor`
- `TextItem.ShadowOffset`

### 4.7 品質制御の要点

サムネイルの再生数影響が大きい要素と、パイプラインでの制御方法:

| 要素 | 影響度 | 制御方法 | 自動化可否 |
|------|-------|---------|-----------|
| フック文言 | 極大 | Gemini生成 + 人間レビュー | 半自動 |
| テキスト色/コントラスト | 大 | 色彩プリセット | 自動 |
| 背景画像の関連性 | 大 | 台本からの画像検索 | 半自動 |
| テキストサイズ/位置 | 中 | テンプレート固定 | 自動 |
| 縁取り/影 | 中 | 色彩プリセット | 自動 |
| レイアウトパターン | 中 | テンプレート選択 | 半自動 |
| モバイル可読性 | 大 | テンプレート設計時に担保 | テンプレート依存 |

**「半自動」= パイプラインが候補を生成、人間が最終決定**

### 4.8 実装済み (2026-03-23 NIGHTSHIFT)

- [x] Gemini 文言生成 (`GeminiIntegration.generate_thumbnail_copy()`) — 台本から main_text/sub_text/label/suggested_pattern/suggested_color を生成
- [x] 色彩プリセット 5種の ARGB 値定義 (`COLOR_PRESETS`)
- [x] `_apply_color_preset()` による TextItem 色差し替え
- [x] `generate_variants()` によるバリエーション生成 (テキスト x 色 の組み合わせ)
- [x] `generate_from_thumbnail_copy()` — Gemini文言から直接 .y4mmp を生成
- [x] パイプライン統合 — `run_pipeline()` で Gemini文言生成を自動実行、`thumbnail_copy.json` を保存
- [x] CLI統合 — `thumbnail --generate`, `--variants`, `--color-preset`, `--list-presets`
- [x] テスト追加: GeminiIntegration 5件 + YMM4Generator 14件 (色彩プリセット5件+バリエーション4件+FromCopy4件+PresetList1件)

### 4.9 未確定事項 (HUMAN_AUTHORITY)

- [ ] Pattern A-E の YMM4 テンプレート実物の作成 (人間がYMM4で作成)
- [ ] テンプレート選択の自動化ロジック — 現在は suggested_pattern → テンプレート名マッピング。テンプレートが存在しない場合は最初のテンプレートにフォールバック
- [ ] A/Bテストの運用フロー（YouTube Studio 連携）

---

## 5. テスト

- `tests/test_thumbnail_generators.py`: 削除済み (template_generator.py / ai_generator.py の削除に伴い不要)
- `tests/test_ymm4_thumbnail_generator.py`: 20件
  - `TestYmm4ThumbnailGenerator`: 基本機能 12件
  - `TestYmm4ThumbnailGeneratorFromScript`: 台本連携 3件
  - `TestYmm4ThumbnailAssetCopy`: 素材コピー 2件
  - `TestYmm4ThumbnailWithRealTemplate`: 実テンプレート 3件
