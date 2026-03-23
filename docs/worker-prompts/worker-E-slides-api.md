# Worker E: Google Slides API統合

## 担当範囲
- スライド生成のGoogle Slides API移行 (PIL生成からの置換)
- src/slides/ のテンプレート統合・テキスト挿入実装
- テンプレートベースのスライド自動生成

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator
- DECISION LOG (2026-03-22): スライド生成をGoogle Slides APIに決定。PIL生成はフォールバックのみ
- PIL (text_slide_generator.py) は削除済み/レガシースタブ化済み
- スライドはセグメントごとに1枚生成し、PNG化してYMM4に渡す
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状 (2026-03-23 更新)
- src/slides/ に4ファイル: slide_generator.py, google_slides_client.py, slide_templates.py, content_splitter.py
- 三段フォールバック実装済み:
  1. テンプレート複製方式 (SLIDES_TEMPLATE_PRESENTATION_ID 設定時)
  2. プログラマティック方式 (API認証済み、テンプレートID未設定)
  3. python-pptx モック (API未認証時)
- テキスト挿入: add_slides_with_content() でプレースホルダー検出 + insertText 実装済み
- テンプレート複製: copy_presentation() + replace_template_placeholders() 実装済み
- レイアウトパターン: LayoutType enum (7種) + from_content_hint() 変換
- テスト: 44件 (test_slide_templates.py) + 既存93件互換確認済み = 137 passed
- Google Drive上のテンプレートスライドは未作成 (環境依存のため手動対応)

## 技術仕様
### 入力
- TranscriptInfo (台本構造化結果): title, segments (speaker/text/key_points)
- スタイルプリセット: config/script_presets/ (news/educational/summary/default)

### 出力
- セグメントごとのPNG画像 (1920x1080, export_thumbnails で取得)
- 画像パスリスト (CSV 3列目に挿入)
- PPTX (export_pptx で取得)

### Google Slides API の使い方
**テンプレート複製方式 (推奨)**:
1. Drive API files().copy() でテンプレートプレゼンを複製
2. replaceAllText でプレースホルダータグを一括置換 ({{TITLE_N}}, {{BODY_N}}, {{SPEAKER_N}}, {{KEYPOINTS_N}})
3. 余剰スライドは deleteObject で削除
4. 不足スライドは add_slides_with_content で追加
5. export_thumbnails でPNG化してダウンロード

**プログラマティック方式 (フォールバック)**:
1. create_presentation() で空プレゼン作成
2. createSlide でレイアウト指定 (predefinedLayout) + objectId 指定
3. presentations().get() でプレースホルダー objectId を取得
4. insertText でテキスト挿入
5. export_thumbnails でPNG化

### レイアウトパターン (LayoutType enum)
| LayoutType | predefinedLayout | 用途 |
|---|---|---|
| TITLE | TITLE | タイトルスライド |
| TITLE_AND_BODY | TITLE_AND_BODY | 標準テキスト (デフォルト) |
| TITLE_AND_TWO_COLUMNS | TITLE_AND_TWO_COLUMNS | 左テキスト + 右テキスト |
| TITLE_ONLY | TITLE_ONLY | タイトルのみ |
| SECTION_HEADER | SECTION_HEADER | セクション区切り / 強調 |
| ONE_COLUMN_TEXT | ONE_COLUMN_TEXT | 一列テキスト |
| BLANK | BLANK | 空白 |

**コンテンツヒント → LayoutType 変換** (from_content_hint):
- two_column → TITLE_AND_TWO_COLUMNS
- full_text, title_and_content, title_and_body, stats → TITLE_AND_BODY
- emphasis, section_header → SECTION_HEADER
- title, title_slide → TITLE

### 環境変数
| 変数 | デフォルト | 説明 |
|---|---|---|
| SLIDES_TEMPLATE_PRESENTATION_ID | (空) | テンプレートプレゼンID。設定するとテンプレート複製方式を優先使用 |
| SLIDES_DEFAULT_LAYOUT | TITLE_AND_BODY | レイアウト指定なしスライドのデフォルト |
| SLIDES_USE_GEMINI_CONTENT | false | Gemini由来スライド情報を優先するか |

## 残作業
1. Google Drive上にテンプレートスライドを作成 (5レイアウトパターン)
   - 各スライドに {{TITLE_1}}, {{BODY_1}}, {{SPEAKER_1}}, {{KEYPOINTS_1}} プレースホルダーを配置
2. CSVアセンブラーとの接続確認 (csv_assembler.py の image_path — 既にPNG glob 対応済み)
3. 実際のGoogle Slides APIでの統合テスト (認証環境が必要)

## 成果物
- src/slides/google_slides_client.py: Slides API連携 (テンプレート複製 + プログラマティック + テキスト挿入)
- src/slides/slide_templates.py: テンプレート管理 (LayoutType, SlideContent, SlideTemplateConfig)
- src/slides/slide_generator.py: 三段フォールバックオーケストレーター
- src/slides/content_splitter.py: 台本→スライド分割 (既存)
- tests/test_slide_templates.py: 44件のテスト
- config/settings.py: テンプレート設定 (SLIDES_SETTINGS に追加)

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/visual_resource_pipeline_spec.md
- src/slides/ (実装)
- src/gapi/ (Google認証)
- src/core/csv_assembler.py (統合先)
- src/core/visual/ (画像パイプライン)
- config/script_presets/ (スタイル定義)
