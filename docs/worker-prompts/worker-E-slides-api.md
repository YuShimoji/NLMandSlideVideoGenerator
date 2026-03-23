# Worker E: Google Slides API統合

## 担当範囲
- スライド生成のGoogle Slides API移行 (PIL生成からの置換)
- src/slides/ の新規実装
- テンプレートベースのスライド自動生成

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator
- DECISION LOG (2026-03-22): スライド生成をGoogle Slides APIに決定。PIL生成はフォールバックのみ
- PIL (text_slide_generator.py) は削除済み/レガシースタブ化済み
- スライドはセグメントごとに1枚生成し、PNG化してYMM4に渡す
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状
- src/slides/ ディレクトリは存在するが実装薄い
- PIL系テスト (test_text_slide_generator.py) は削除済み
- Google Slides APIの認証基盤: src/gapi/ に存在
- スライドテンプレート設計は未着手

## 技術仕様
### 入力
- ScriptInfo (台本構造化結果): title, segments (speaker/text/key_points)
- スタイルプリセット: config/script_presets/ (news/educational/summary/default)

### 出力
- セグメントごとのPNG画像 (1920x1080)
- 画像パスリスト (CSV 3列目に挿入)

### Google Slides API の使い方
1. テンプレートスライドを複製
2. プレースホルダーにテキスト挿入 (タイトル、本文、話者名、キーポイント)
3. スライドをPNG/JPEG化してダウンロード
4. CSVの image_path 列に反映

### レイアウトパターン (提案)
- **TwoColumn**: 左テキスト + 右画像
- **FullText**: 全面テキスト (キーポイント強調)
- **Stats**: 数値・統計強調
- **Emphasis**: 引用・重要テキスト強調
- **Title**: セクション区切り

## 作業手順
1. docs/DESIGN_FOUNDATIONS.md を読む
2. Google Slides API ドキュメントを確認
3. src/gapi/ の認証基盤を確認
4. テンプレートスライドをGoogle Driveに作成
5. slides API連携モジュール実装 (src/slides/)
6. CSVアセンブラーとの接続 (src/core/csv_assembler.py の image_path)
7. テスト実装

## 成果物
- src/slides/google_slides_generator.py: Slides API連携
- src/slides/slide_templates.py: テンプレート管理
- Google Drive上のテンプレートスライド (複数パターン)
- テスト追加
- 仕様書更新

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/visual_resource_pipeline_spec.md
- src/slides/ (既存)
- src/gapi/ (Google認証)
- src/core/csv_assembler.py (統合先)
- src/core/visual/ (画像パイプライン)
- config/script_presets/ (スタイル定義)
