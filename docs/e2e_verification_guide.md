# E2E 手動検証ガイド (SP-027)

最終更新: 2026-03-16

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
| 1 | ken_burns | 緩やかなズームイン (fitZoom→fitZoom*1.05) | |
| 2 | ken_burns | 同上 | |
| 3 | zoom_in | 明確なズームイン (fitZoom→fitZoom*1.15) | |
| 4 | zoom_out | 明確なズームアウト (fitZoom*1.15→fitZoom) | |
| 5 | pan_left | 画像が右→左へパン (X: +5%→0) | |
| 6 | pan_right | 画像が左→右へパン (X: -5%→0) | |
| 7 | pan_up | 画像が下→上へパン (Y: +5%→0) | |
| 8 | static | 完全に静止 (Zoom.From=fitZoom のみ) | |
| 9 | (空=default) | ken_burnsと同じ動作 | |
| 10 | (画像なし) | テキスト+Voiceのみ | |
| 11 | ken_burns | 緩やかなズームイン | |

追加確認:
- [ ] 全画像行で画像が表示される (不透明度100%, EnsureOpacity100)
- [ ] 画像がcontainフィット (黒帯あり or 全画面)
- [ ] アニメーションが滑らか (フレーム落ちなし)
- [ ] FadeIn/FadeOut (crossfadeFrames) が動作する

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
| アニメーション | 7種が視覚的に区別可能 | 視聴確認 |
| 総尺 | 11セグメント分 (約30-60秒) | 再生時間確認 |

## Step 6: ベースライン記録

テスト結果を以下の形式で記録:

```
テスト日時: YYYY-MM-DD HH:MM
プラグインバージョン: (commit hash)
YMM4バージョン: v4.XX
テストCSV: e2e_baseline_test.csv (11行)

合否: PASS / FAIL
画像表示: OK / NG
アニメーション: OK / NG (種別ごとの結果)
Voice生成: OK / NG
音声同期: OK / NG
レンダリング: OK / NG

品質メモ:
- (改善が必要な点)
- (次に対応すべき項目)
```

## 既知の制限事項

- Voice Speaker未検出時は手動での音声割り当てが必要
- `Animation.From/To` は YMM4 の旧API (CS0618) — 将来のYMM4更新で非互換の可能性
- crossfadeFrames のフェード効果は YMM4 バージョンに依存
- YMM4のレンダリング設定はユーザー環境に依存

## 関連ドキュメント

- 運用ワークフロー: `docs/user_guide_manual_workflow.md`
- YMM4エクスポート仕様: `docs/ymm4_export_spec.md`
- アニメーション仕様: `docs/visual_resource_pipeline_spec.md`
- 品質パイプライン仕様: `docs/video_quality_pipeline_spec.md`
