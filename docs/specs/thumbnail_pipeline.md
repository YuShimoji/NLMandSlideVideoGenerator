# サムネイルパイプライン統合仕様 (SP-037)

**最終更新**: 2026-03-21
**ステータス**: partial (Phase 1-2 done, Phase 3 設計中)

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

## 4. テスト

- `tests/test_thumbnail_generators.py`: 40件 (Phase 1: 23件 + Phase 2: 12件 + 視覚品質: 5件)
  - `TestThumbnailStyleMapping`: マッピング正当性 7件
  - `TestStyleTemplateThumbnailSection`: style_template thumbnail セクション 5件
  - `TestThumbnailVisualQuality`: PILサムネイルの視覚的品質検証 5件
- `tests/test_ymm4_thumbnail_generator.py`: 20件
  - `TestYmm4ThumbnailGenerator`: 基本機能 12件
  - `TestYmm4ThumbnailGeneratorFromScript`: 台本連携 3件
  - `TestYmm4ThumbnailAssetCopy`: 素材コピー 2件
  - `TestYmm4ThumbnailWithRealTemplate`: 実テンプレート 3件
