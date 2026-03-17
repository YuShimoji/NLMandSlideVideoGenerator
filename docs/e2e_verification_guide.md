# E2E 手動検証ガイド (SP-027)

最終更新: 2026-03-17

CSV入力からYMM4での最終動画出力までのE2Eフローを手動で検証する手順書。
SP-027 Baseline Video E2E + SP-033 Phase 1 アニメーション検証を統合。

---

## 前提条件

- Python 3.11 + venv 環境構築済み
- YMM4 インストール済み（NLMSlidePlugin デプロイ済み）
- テスト用画像: `samples/image_slide/slides/` に slide_0001.png ~ slide_0003.png

## Step 1: テスト用CSV準備

### 1a. 基本テスト (2列: Speaker,Text)

```csv
れいむ,本日のテーマはAI技術の進化です
まりさ,2026年のAI市場は急成長しています
れいむ,では具体的なデータを見てみましょう
```

### 1b. 画像+アニメーション テスト (4列: Speaker,Text,ImagePath,AnimationType)

`samples/image_slide/e2e_baseline_test.csv` を使用:

```csv
れいむ,テスト開始,slides/slide_0001.png,ken_burns
まりさ,ズームイン検証,slides/slide_0002.png,zoom_in
れいむ,ズームアウト検証,slides/slide_0002.png,zoom_out
まりさ,パン左検証,slides/slide_0003.png,pan_left
れいむ,パン右検証,slides/slide_0003.png,pan_right
まりさ,パン上検証,slides/slide_0001.png,pan_up
れいむ,スタティック検証,slides/slide_0002.png,static
まりさ,アニメ列なし(デフォルト),slides/slide_0003.png,
れいむ,画像なし行,,
```

## Step 2: プラグインデプロイ

1. `ymm4-plugin/` を Visual Studio でビルド (Release)
2. 出力DLLを YMM4 プラグインフォルダへコピー
3. YMM4 を再起動し、「NLMSlidePlugin」メニューが表示されることを確認

## Step 3: YMM4 でCSVインポート

1. YMM4を起動、新規プロジェクト作成
2. メニュー「NLMSlidePlugin」 > 「CSVタイムラインをインポート」
3. CSVインポートダイアログで `e2e_baseline_test.csv` を選択
4. 「音声を自動生成（ゆっくりボイス）」ON
5. 「字幕を追加」ON
6. 「プレビュー」でCSV内容を確認
7. 「インポート」を実行

### 検証ポイント

| 確認項目 | 期待値 | 確認方法 |
|----------|--------|----------|
| プレビュー表示 | 11行、話者・テキスト・画像パス・アニメ種別が正しい | DataGrid |
| Voice Speaker検出 | 「Found 2 voice speaker(s)」ログ | ログタブ |
| Voice生成進捗 | 全セグメント完了 | 進捗バー |
| 完了メッセージ | 「Import Complete!」 | ダイアログ |
| タイムライン | 11セグメント | YMM4目視 |
| ランタイムログ | `ApplyAnimationByType(Direct):` ログが各行に出力 | csv_import_runtime.log |
| ランタイムログ | `EnsureOpacity100:` ログが画像行に出力 | csv_import_runtime.log |

## Step 4: アニメーション検証 (SP-033 Phase 1)

YMM4タイムライン上でプレビュー再生し、以下を確認:

| 行 | アニメ種別 | 期待される視覚効果 | 結果 |
|----|-----------|-------------------|------|
| 1 | ken_burns | 緩やかなズームイン (fitZoom→fitZoom*1.05) | PASS |
| 2 | ken_burns | 同上 | PASS |
| 3 | zoom_in | 明確なズームイン (fitZoom→fitZoom*1.15) | PASS |
| 4 | zoom_out | 明確なズームアウト (fitZoom*1.15→fitZoom) | PASS |
| 5 | pan_left | 画像が右→左へパン (X: +5%→0) | PASS |
| 6 | pan_right | 画像が左→右へパン (X: -5%→0) | PASS |
| 7 | pan_up | 画像が下→上へパン (Y: +5%→0) | PASS |
| 8 | static | 完全に静止 (Zoom.From=fitZoom のみ) | PASS |
| 9 | (空=default) | ken_burnsと同じ動作 | PASS |
| 10 | (画像なし) | テキスト+Voiceのみ | PASS |
| 11 | ken_burns | 緩やかなズームイン | PASS |

追加確認:
- [x] 全画像行で画像が表示される (不透明度100%)
- [x] 画像がcontainフィット (黒帯あり or 全画面)
- [x] アニメーションが滑らか (フレーム落ちなし)
- [x] FadeIn/FadeOut (crossfadeFrames) が動作する

## Step 5: 最終レンダリング

1. YMM4タイムラインで全体プレビュー
2. 「ファイル」>「動画出力」（Ctrl+Shift+E）
3. 出力設定:
   - 解像度: 1920x1080
   - フレームレート: 30fps
   - コーデック: H.264
4. レンダリング実行

### 検証ポイント

| 確認項目 | 期待値 | 確認方法 |
|----------|--------|----------|
| mp4ファイル | 指定先に生成 | エクスプローラ |
| 動画再生 | 正常に再生可能 | メディアプレイヤー |
| 解像度 | 1920x1080 (16:9) | プロパティ |
| 音声同期 | テキストと音声が同期 | 視聴確認 |
| 画像遷移 | 各行で画像が正しく切り替わる | 視聴確認 |
| アニメーション | 8種が視覚的に区別可能 | 視聴確認 |
| 総尺 | 11セグメント分 (約30-60秒) | 再生時間確認 |

## Step 6: ベースライン記録

テスト結果を以下の形式で記録:

### ベースライン記録 #1 (2026-03-16)

```
テスト日時: 2026-03-16
プラグインバージョン: Values in-place方式 (dcfcba9以降)
YMM4バージョン: v4.50
テストCSV: e2e_baseline_test.csv (11行)

合否: PASS
画像表示: OK (全画像containフィット、不透明度100%)
アニメーション: OK (全8種 + デフォルト + 画像なし行 全PASS)
Voice生成: OK (ゆっくりボイス自動生成)
音声同期: OK
レンダリング: OK (1920x1080 mp4出力完走)

品質メモ:
- Zoom (ken_burns/zoom_in/zoom_out) は Values in-place方式で正常動作
- Pan (pan_left/pan_right/pan_up) は動作確認済み
- FadeIn/FadeOut クロスフェード正常動作 (0.5秒)
- 次の改善項目: SP-028 (Post-Voice Timeline Resync)
```

## 既知の制限事項

- Voice Speaker未検出時は手動での音声割り当てが必要
- `Animation.From/To` は使用禁止 (レンダリング破壊)。Values in-place方式を使用すること
- `new ImageItem(path)` コンストラクタ必須。`new ImageItem { FilePath = path }` はレンダリングされない
- `PlaybackRate = 100.0` (ImageItem固有。AudioItem/TextItemは1.0)
- `FadeIn`/`FadeOut` の単位は秒 (フレーム数ではない)
- YMM4のレンダリング設定はユーザー環境に依存

## 関連ドキュメント

- 運用ワークフロー: `docs/user_guide_manual_workflow.md`
- YMM4エクスポート仕様: `docs/ymm4_export_spec.md`
- アニメーション仕様: `docs/visual_resource_pipeline_spec.md`
- 品質パイプライン仕様: `docs/video_quality_pipeline_spec.md`
