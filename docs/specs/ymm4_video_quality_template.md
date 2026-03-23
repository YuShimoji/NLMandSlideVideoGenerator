# SP-052: YMM4 動画内容クオリティテンプレート設計

SP-052 | Status: partial | pct: 55 | Created: 2026-03-22 | Updated: 2026-03-23

---

## 目的

YouTube公開水準の動画クオリティを実現するために、YMM4側のテンプレート設計・レイヤー構成・人間/Python/YMM4の責務境界を定義する。

### 背景

- パイプライン基盤（CSV→YMM4→MP4）は確立済み（50仕様、1273テスト）
- しかし出力動画の内容クオリティがYouTube公開水準に未達
- SP-047で品質ギャップは検出済みだが、YMM4側のテンプレート設計が未定義
- DESIGN_FOUNDATIONS.md: 「出力層(YMM4)が最終的な視聴覚品質を決定する」

### この仕様が解決する問題

| 問題 | 現状 | あるべき姿 |
|------|------|-----------|
| 画面が単調 | 1セグメント=1画像+字幕のみ | 背景+テキストオーバーレイ+キャラ+字幕の多層構成 |
| テキスト情報が不足 | 字幕（話者セリフ）のみ | キーポイント表示、章タイトル、統計数値のオーバーレイ |
| キャラクターが不在 | 画像+音声のみ | ゆっくりキャラが画面に常駐（立ち絵+リップシンク） |
| 視覚変化が乏しい | 画像切替のみ | 画像+テキスト+アニメーションの複合変化 |
| テンプレートがない | 毎回手動構成 | 事前作成テンプレートに自動注入 |

---

## 1. 三層責務モデル（DESIGN_FOUNDATIONS準拠）

### 1.1 責務の明確な分担

```
[Python 変換層]                    [YMM4 出力層]                [人間 制作者]
─────────────────                ────────────────             ─────────────
CSV生成 (4列)                    音声合成                      テンプレート作成
  speaker, text,                 リップシンク                  キャラ素材配置
  image_path, animation_type     動画レンダリング              配色・フォント選定
スライド画像生成                  字幕配置                      最終レビュー
  (Google Slides API)            クロスフェード                品質判定
素材調達                         多層レイヤー管理
  (Pexels/Pixabay/Wikimedia)
メタデータJSON生成               テンプレートからの
  (overlay指示を含む)            アイテム自動配置
```

### 1.2 新規: Python→YMM4 オーバーレイ指示

現行の4列CSV (speaker, text, image_path, animation_type) に加え、
テキストオーバーレイ指示をメタデータJSONで渡す。

**CSVは変更しない**（後方互換維持）。オーバーレイ情報は別ファイルで渡す。

```
output_csv/
├── timeline.csv              # 既存4列CSV（変更なし）
├── metadata.json             # 既存メタデータ（変更なし）
└── overlay_plan.json         # 新規: テキストオーバーレイ指示
```

---

## 2. YMM4 プロジェクトテンプレート設計

### 2.1 レイヤー構成（下から上へ）

```
Layer 7: テキストオーバーレイ（キーポイント、章タイトル、統計数値）  ← 新規
Layer 6: 字幕（話者セリフ）                                        ← 既存
Layer 5: キャラクタースプライト（立ち絵）                          ← 新規
Layer 4: 画像B（クロスフェード用偶数）                             ← 既存
Layer 3: 画像A（クロスフェード用奇数）                             ← 既存
Layer 2: 背景ベース（単色 or グラデーション、画像なし時の下地）     ← 新規
Layer 1: BGM                                                       ← 既存
```

### 2.2 テンプレートファイル構成

```
config/video_templates/
├── default/
│   ├── template.y4mmp           # YMM4プロジェクトテンプレート
│   ├── characters/              # キャラクター素材
│   │   ├── reimu/               # れいむ立ち絵セット
│   │   └── marisa/              # まりさ立ち絵セット
│   └── assets/                  # 共通素材
│       ├── lower_third.png      # ローワーサード背景
│       └── title_bg.png         # 章タイトル背景
├── news/                        # ニュース風テンプレート
│   ├── template.y4mmp
│   ├── characters/
│   └── assets/
└── educational/                 # 教育風テンプレート
    ├── template.y4mmp
    ├── characters/
    └── assets/
```

### 2.3 テンプレートの事前設定項目（人間が作成）

| 項目 | 設定場所 | 内容 |
|------|---------|------|
| キャラクター配置 | template.y4mmp | 立ち絵の位置・サイズ・レイヤー。リップシンク設定 |
| 字幕スタイル | template.y4mmp + style_template.json | フォント・色・位置・アウトライン |
| 背景ベース | template.y4mmp | 単色/グラデーション。画像なし時に見える下地 |
| ローワーサード | assets/ | テキストオーバーレイの背景帯画像 |
| 配色テーマ | style_template.json | テンプレート種別ごとのカラーパレット |

### 2.4 テンプレート作成手順（人間向けガイド）

1. YMM4で新規プロジェクトを作成（1920x1080, 30fps）
2. Layer 2 に背景ベースの色/画像を配置
3. Layer 5 にキャラクター立ち絵を配置
   - れいむ: 画面右下、Zoom適切に調整
   - まりさ: 画面左下、Zoom適切に調整
   - リップシンク設定を有効化
4. Layer 6 の字幕位置・フォント・アウトラインを設定
5. Layer 7 にテキストオーバーレイのプレースホルダーを配置（任意）
6. `config/video_templates/{name}/template.y4mmp` として保存
7. キャラ素材を `characters/` に配置

**所要時間目標**: 初回30分、2回目以降は既存テンプレートの微調整で5-10分

---

## 3. テキストオーバーレイ仕様

### 3.1 オーバーレイの種類

| 種類 | 表示タイミング | 表示位置 | 内容例 | 視覚効果 |
|------|--------------|---------|--------|---------|
| 章タイトル | セグメントグループの切り替わり時 | 画面上部中央 | 「第2章: AIの歴史」 | FadeIn 0.5s → 3s表示 → FadeOut 0.5s |
| キーポイント | 台本のkey_pointsに対応 | 画面左上 (ローワーサード) | 「GPT-4は2023年3月に公開」 | スライドイン → 5-10s表示 → スライドアウト |
| 統計数値 | 台本に数値データがある場合 | 画面中央やや上 | 「利用者数: 1億人突破」 | スケールアップ → 3s表示 → FadeOut |
| ソース引用 | 引用元を示す場合 | 画面下部（字幕の上） | 「出典: 〇〇報告書 2025」 | FadeIn → 表示 → FadeOut |

### 3.2 overlay_plan.json フォーマット

```json
{
  "version": "1.0",
  "overlays": [
    {
      "type": "chapter_title",
      "text": "第1章: AIの基礎",
      "segment_index": 0,
      "duration_sec": 4.0,
      "position": "top_center",
      "style": "default"
    },
    {
      "type": "key_point",
      "text": "GPT-4は2023年3月に公開",
      "segment_index": 5,
      "duration_sec": 7.0,
      "position": "lower_third",
      "style": "default"
    },
    {
      "type": "statistic",
      "text": "利用者数: 1億人突破",
      "value": "100000000",
      "segment_index": 12,
      "duration_sec": 4.0,
      "position": "center_upper",
      "style": "emphasis"
    },
    {
      "type": "source_citation",
      "text": "出典: OpenAI Technical Report 2023",
      "segment_index": 5,
      "duration_sec": 5.0,
      "position": "above_subtitle",
      "style": "small"
    }
  ]
}
```

### 3.3 Python側の責務: overlay_plan.json 生成

Gemini構造化の出力JSONに含まれる `key_points` フィールドから自動抽出する。

```
構造化台本JSON (Phase 3)
  └── segments[].key_points[]   → key_point オーバーレイ
  └── segments[].text (数値検出) → statistic オーバーレイ
  └── セグメントグループ境界     → chapter_title オーバーレイ
  └── segments[].source_ref      → source_citation オーバーレイ
```

**生成ロジック**: `src/core/overlay/overlay_planner.py` (新規)

### 3.4 YMM4側の責務: TextItem として配置

NLMSlidePlugin が `overlay_plan.json` を読み込み、TextItem として Layer 7 に配置する。

| overlay type | YMM4 TextItem設定 |
|-------------|-------------------|
| chapter_title | FontSize=64, Bold, CenterTop, FadeIn=0.5s, FadeOut=0.5s |
| key_point | FontSize=40, Border, LeftTop Y=70%, ローワーサード背景画像と連動 |
| statistic | FontSize=72, Bold, Center, Scale animation |
| source_citation | FontSize=28, Italic, CenterBottom Y=字幕の上 |

---

## 4. キャラクタースプライト仕様

### 4.1 設計方針

- キャラクターはYMM4テンプレートに事前配置（人間が設定）
- Pythonはキャラクターの配置・アニメーションに一切関与しない
- CSVの speaker 列でどのキャラが話しているかをYMM4が判定
- リップシンクはYMM4の内蔵機能を利用

### 4.2 キャラクター配置パターン

| パターン | 配置 | 用途 |
|---------|------|------|
| 2人対話 (標準) | れいむ右下 + まりさ左下 | ゆっくり解説の定番 |
| 1人解説 | れいむ右下のみ | ナレーション主体 |
| 3人以上 | テンプレートで事前定義 | 特殊企画 |

### 4.3 話者→キャラ対応

CSV speaker 列の名前と YMM4 テンプレートのキャラクター名を対応付ける。

| CSV speaker | YMM4 キャラクター | 立ち絵位置 |
|-------------|-----------------|-----------|
| れいむ | 博麗霊夢 | 画面右下 |
| まりさ | 霧雨魔理沙 | 画面左下 |
| ナレーター | (字幕のみ、立ち絵なし) | - |

この対応は `style_template.json` の `speaker_characters` セクションで定義する（新規）。

### 4.4 表情切替（将来拡張、現フェーズではスコープ外）

CSV 5列目で表情指定する案はあるが、現フェーズではスコープ外とする。
YMM4のデフォルト表情+リップシンクで十分な品質を確保する。

---

## 5. 背景画像の配置ルール

### 5.1 現行の制約と改善

| 項目 | 現行 | 改善後 |
|------|------|--------|
| 画像/セグメント | 1:1固定 | N:1（複数セグメントで同一画像を継続利用可能） |
| 画像なしセグメント | 黒画面 | 背景ベース（テンプレートのLayer 2）が表示 |
| 切替頻度 | セグメントごと | 5-15秒ごとの視覚変化を目標 |

### 5.2 画像継続ルール

```
セグメント 1 (15秒): slide_01.png  ← 新しいトピック → 新画像
セグメント 2 (12秒): slide_01.png  ← 同トピック継続 → 同画像
セグメント 3 (18秒): slide_02.png  ← トピック変更 → 新画像
セグメント 4 (10秒): (なし)        ← 対話区間 → 背景ベース+キャラのみ
```

Python側 (CsvAssembler) が画像の継続/切替を判定し、CSV 3列目に反映する。
判定基準: 台本構造化JSONのセグメントグループ（章/トピック単位）。

### 5.3 視覚変化の確保

画像が同一でも、以下で視覚変化を確保する:
- アニメーション（ken_burns/zoom_in等）が常時動作
- テキストオーバーレイの出現/消失
- キャラクターのリップシンク

---

## 6. アニメーション使い分けガイドライン

### 6.1 場面別推奨アニメーション

| 場面 | 推奨アニメーション | 理由 |
|------|-------------------|------|
| 写真・風景画像 | ken_burns | 自然な動き、汎用性高い |
| スライド（テキスト主体） | static or zoom_in (微弱) | テキスト可読性優先 |
| タイトル画面 | zoom_in | 注目を集める |
| 統計データ表示 | static | 数値の可読性優先 |
| トピック切替 | pan_left / pan_right | 場面転換の感覚 |
| 俯瞰・全体像 | zoom_out | 広がりの表現 |
| 強調・インパクト | zoom_in (強) | 視聴者の注意を引く |

### 6.2 Python側の自動判定

`AnimationAssigner` を拡張し、セグメントの性質に基づいてアニメーションを選択する。

```python
def assign_animation(segment, image_source):
    if image_source == "slide":       # スライド画像
        return "static"
    if segment.has_statistics:         # 統計データあり
        return "static"
    if segment.is_topic_change:        # トピック変更
        return random.choice(["pan_left", "pan_right"])
    if segment.is_chapter_start:       # 章の開始
        return "zoom_in"
    return "ken_burns"                 # デフォルト
```

---

## 7. style_template.json 拡張

### 7.1 新規セクション

既存の style_template.json に以下のセクションを追加する。

```json
{
  "video": { ... },
  "subtitle": { ... },
  "speaker_colors": [...],
  "animation": { ... },
  "crossfade": { ... },
  "timing": { ... },
  "validation": { ... },
  "bgm": { ... },
  "thumbnail": { ... },

  "overlay": {
    "chapter_title": {
      "font_size": 64,
      "font_color": "#FFFFFF",
      "bold": true,
      "position": "top_center",
      "y_offset_ratio": 0.08,
      "fade_in_sec": 0.5,
      "fade_out_sec": 0.5,
      "duration_sec": 4.0,
      "background_opacity": 0.6
    },
    "key_point": {
      "font_size": 40,
      "font_color": "#FFFFFF",
      "bold": true,
      "style": "border",
      "position": "lower_third",
      "y_offset_ratio": 0.70,
      "duration_sec": 7.0,
      "background_image": "lower_third.png"
    },
    "statistic": {
      "font_size": 72,
      "font_color": "#FFD700",
      "bold": true,
      "position": "center_upper",
      "y_offset_ratio": 0.30,
      "duration_sec": 4.0
    },
    "source_citation": {
      "font_size": 28,
      "font_color": "#CCCCCC",
      "italic": true,
      "position": "above_subtitle",
      "y_offset_ratio": 0.55,
      "duration_sec": 5.0
    }
  },

  "characters": {
    "speaker_map": {
      "れいむ": { "character_name": "博麗霊夢", "position": "right" },
      "まりさ": { "character_name": "霧雨魔理沙", "position": "left" },
      "ナレーター": { "character_name": null, "position": null }
    },
    "layout": "two_speaker_bottom"
  },

  "background": {
    "base_color": [26, 26, 46],
    "base_gradient": true,
    "gradient_end_color": [10, 10, 30]
  }
}
```

---

## 8. 実装フェーズ

### Phase 1: テンプレート基盤（人間+AI並行） -- AI側完了 (2026-03-23)

| 担当 | 作業 | 成果物 | 状態 |
|------|------|--------|------|
| 人間 | YMM4でdefaultテンプレート作成（キャラ配置+背景+字幕位置） | `config/video_templates/default/template.y4mmp` | 未実施 |
| 人間 | キャラクター素材の入手・配置 | `config/video_templates/default/characters/` | 未実施 |
| AI | style_template.json の overlay/characters/background セクション追加 | `config/style_template.json` 拡張 | 完了 |
| AI | overlay_plan.json 生成ロジック実装 | `src/core/overlay/overlay_planner.py` | 完了 (18テスト) |
| AI | config/video_templates/ ディレクトリ構成 + README | `config/video_templates/` | 完了 |

### Phase 2: NLMSlidePlugin拡張（AI） -- 完了 (2026-03-23)

| 作業 | 成果物 | 状態 |
|------|--------|------|
| overlay_plan.json 読み込み機能追加 | `Core/OverlayImporter.cs` (新規) | 完了 |
| TextItem配置ロジック（Layer 7） | 同上 | 完了 |
| style_template.json のoverlay設定読み込み | `Core/StyleTemplateLoader.cs` 拡張 | 完了 |
| テスト | `Tests/OverlayImporterTests.cs` (8テスト) | 完了 (.NET 10 SDK未インストールでローカルビルド不可) |

### Phase 3: パイプライン統合（AI） -- 完了 (2026-03-23)

| 作業 | 成果物 | 状態 |
|------|--------|------|
| CsvAssembler で overlay_plan.json を同時出力 | `src/core/csv_assembler.py` 拡張 | 完了 (4テスト) |
| Ymm4TimelineImporter で overlay自動読込+TextItem配置 | `TimelinePlugin/Ymm4TimelineImporter.cs` 拡張 | 完了 |
| AnimationAssigner の場面別判定拡張 | `src/core/visual/animation_assigner.py` 拡張 | 保留: 動画デザイン方向性未定。ユースケース確定後に再検討 |
| Pre-Export Validation にオーバーレイ検証追加 | バリデーション拡張 | 未着手 (Phase 4で必要性判断) |

### Phase 3 設計保留事項 (2026-03-23)

AnimationAssigner の場面別判定拡張は、**具体的な動画デザイン方向性が未確定**のため保留。

**懸念**: アニメーション（パン・ズーム等）を機械的に割り当てても、全体的な動画デザインと合わなければ逆効果。スライド動画では「動かさない (STATIC)」方が適切なケースが多い。

**再開条件**:

- Phase 4 で実際に1本通し制作を完了し、動画デザインの方向性を確定する
- 「どのような画像に対して、どのアニメーションが有効か」の具体的ユースケースを定義する
- ユースケースに基づいて AnimationAssigner を拡張する

なお `_assign_context_aware()` メソッドは実装済みだが `context_aware=True` を明示しない限り呼ばれないため、既存動作に影響しない。

### Phase 4: 実検証+品質調整（人間+AI）

| 作業 | 内容 |
|------|------|
| 通し制作テスト | SP-045チェックリストに従い1本完成 |
| 品質レビュー | SP-047のビジュアルチェックリスト検証 |
| テンプレート調整 | レビュー結果に基づくキャラ位置・フォントサイズ等の調整 |

---

## 9. 競合回避

台本生成Pipeline（research_cli.py, gemini_provider.py, gemini_integration.py）は別作業で進行中。

| ファイル/モジュール | 本仕様で触る | 台本Pipelineで触る | 競合 |
|-------------------|------------|-------------------|------|
| src/core/overlay/ | 新規作成 | 触らない | なし |
| src/core/csv_assembler.py | overlay_plan出力追加 | 触らない | なし |
| src/core/visual/animation_assigner.py | 判定ロジック拡張 | 触らない | なし |
| ymm4-plugin/ | OverlayImporter追加 | 触らない | なし |
| config/style_template.json | セクション追加 | 触らない | なし |
| scripts/research_cli.py | 触らない | 変更中 | 回避 |
| src/notebook_lm/gemini_integration.py | 触らない | 変更中 | 回避 |
| src/core/providers/script/gemini_provider.py | 触らない | 変更中 | 回避 |

---

## 10. YMM4側で人間が判断すべきこと（作者パートの明確化）

### 10.1 テンプレート作成時（初回のみ）

- キャラクター立ち絵の選定・配置・サイズ調整
- 配色テーマの決定（背景色、アクセントカラー）
- フォントの選定（ゴシック系/明朝系、装飾の度合い）
- ローワーサード等のオーバーレイ背景デザイン
- BGMの選定と音量バランス

### 10.2 動画ごとの制作時（毎回、目標5分以内）

- CSVインポート後のプレビュー確認
- キャラクター表情が不自然でないかの確認
- テキストオーバーレイの可読性確認
- BGMと音声のバランス確認
- 最終書き出し+品質チェック

### 10.3 Python/AIが自動化する範囲

- CSV生成（台本→speaker, text, image_path, animation_type）
- overlay_plan.json 生成（キーポイント抽出、章タイトル検出、統計数値検出）
- 画像素材の自動調達（Wikimedia → Pexels → Pixabay → AI → TextSlide）
- アニメーション種別の自動選択（場面に応じた判定）
- メタデータ生成（YouTube用タイトル、説明、タグ）
- Pre-Export バリデーション

---

## 11. 品質基準（SP-047と接続）

### 11.1 本仕様が満たすSP-047項目

| SP-047項目 | 本仕様での対応 |
|-----------|--------------|
| テキストスライド: NotebookLMスライド生成活用 | Google Slides APIスライド生成 (Phase 4別途) |
| 視覚変化: 5-15秒ごとに何らかの変化 | アニメーション + テキストオーバーレイ + 画像切替 |
| 1セグメント1画像の制約を解除 | 画像継続ルール（Section 5.2） |
| キャラクタースプライト表示 | テンプレートに事前配置（Section 4） |
| テキストオーバーレイ | overlay_plan.json + NLMSlidePlugin拡張（Section 3） |

---

## 12. 関連仕様

| ID | タイトル | 関係 |
|----|---------|------|
| SP-004 | YMM4 Export Specification | CSVインポート・アイテム配置の基盤仕様 |
| SP-031 | Style Template & Pre-Export | style_template.json の拡張元 |
| SP-033 | Visual Resource Pipeline | 画像調達・アニメーション割当の基盤 |
| SP-037 | Thumbnail Pipeline | YMM4テンプレートパターンの先行事例 |
| SP-047 | Video Output Quality Standard | 品質基準の親仕様 |
| SP-049 | Design Foundations | 三層モデル・責務境界の公理 |
| SP-050 | E2E Workflow Specification | ワークフロー全体定義 |
