# 動画クオリティ安定化パイプライン仕様

**最終更新**: 2026-03-17
**ステータス**: Phase 0 完了 (E2E全PASS 2026-03-16)、Phase 1 (SP-028) 次ステップ

---

## 1. 目的

CSV入稿から最終mp4書き出しまでの全工程で、動画品質を「偶然」ではなく「構造」で安定させるパイプラインを構築する。

### 1.1 逆算の起点

| 要素 | 現状 | 目標 |
|------|------|------|
| 画像表示 | contain全画面フィット | 安定して全画面表示 |
| 画像遷移 | 即時切替（ハードカット） | フェード/ワイプ等のトランジション |
| 画面の動き | 完全静止 | Ken Burns（パン・ズーム）|
| 字幕 | TextItem基本配置 | 位置・フォント・装飾の安定制御 |
| 音声タイミング | Voice自動生成 | 画像切替とVoice終了の同期 |
| BGM | なし（手動追加） | テンプレートBGMの自動配置 |
| 品質検証 | 手動目視 | チェックリスト自動化 |

---

## 2. フェーズ構成

### Phase 0: 実機検証ベースライン確立 (SP-027)

**狙い**: 現時点の出力品質を正確に把握し、以降の改善が測定可能な状態にする

- 目的: 全画面フィット + Voice生成の実機E2E完走、ベースライン動画の書き出し
- 作業: プラグインデプロイ → CSVインポート → YMM4書き出し → 出力mp4を視聴評価
- 成功条件: 1本の動画がCSV→mp4で完走し、画像が全画面表示され、音声が再生される
- 成果物: ベースライン動画ファイル、品質評価メモ（何が足りないかのリスト）

### Phase 1: タイミング安定化 (SP-028)

**狙い**: 音声長に基づく正確なタイムライン同期

- 目的: Voice生成後の実音声長をImageItem/TextItemのLengthに反映
- 課題: 現在はCSVのDuration（デフォルト3秒）で配置 → Voice生成後の実尺と乖離
- 作業:
  - (a) Voice生成後にWAV長を取得しImageItem/TextItemのLengthを再計算
  - (b) ギャップ/オーバーラップ検出ロジック
- 成功条件: 音声終了と同時に次スライドへ遷移、無音区間が1秒以内

### Phase 2: Ken Burns アニメーション (SP-029)

**狙い**: 静止画に動きを加え、視聴維持率を改善

- 目的: ImageItemにZoom/X/Yのアニメーションを自動付与
- 設計: AnimationValue.AnimationType を「直線」に設定、Values配列に開始値/終了値を設定
- パターン:
  - (a) Slow Zoom In（100%→110%、5秒間）
  - (b) Slow Pan Left→Right
  - (c) ランダム選択 or CSV4列目で指定
- 成功条件: 全画像にゆるやかなZoom/Panが付き、視覚的に静止していないこと

### Phase 3: トランジション + 字幕装飾 (SP-030)

**狙い**: スライド間の遷移と字幕の視認性を安定化

**実装状況** (2026-03-17):
- トランジション: FadeIn/FadeOut 0.5秒クロスフェード **実装済み** (交互レイヤー方式)
- 字幕テンプレート: `ApplySubtitleStyle` **実装済み** — 以下を直接プロパティアクセスで設定
  - FontSize 48 (Values in-place)
  - Y位置: 画面下部 (videoHeight * 0.35)
  - BasePoint: CenterBottom
  - Bold: true
  - Style: Border (黒アウトライン)
  - MaxWidth: videoWidth * 0.9
  - WordWrap: Character (日本語対応)
- 話者別色分け: `GetSpeakerColor` **実装済み** — 出現順に白/黄/シアン/緑/橙/ラベンダーの6色サイクル
- PlaybackRate: 100.0に修正 (旧: 1.0 — バグ)
- 成功条件: 全スライド間でスムーズなフェード遷移、字幕が画面下部で統一表示、話者ごとに色分け
- 残: 実機テスト未実施

### Phase 4: テンプレート化 + 品質チェック自動化 (SP-031)

**狙い**: 品質を「偶然」ではなく「構造」で安定させる

**実装状況** (2026-03-17):
- テンプレート: `config/style_template.json` v1.1 で統一管理 **実装済み**
  - `video` (width/height/fps)、`subtitle`、`animation`、`crossfade`、`timing`、`validation` セクション
  - Python `StyleTemplateManager` + C# `StyleTemplateLoader` で読み込み
  - テンプレート未検出時はビルトインデフォルトにフォールバック
- 品質チェック: `ValidateImportItems` **実装済み**
  - ファイル存在確認 (audio/image)
  - Duration妥当性
  - 空行検出
  - ギャップ/オーバーラップ検出 (テンプレート閾値ベース)
  - 総尺超過チェック
  - 連続同一画像検出
  - テキストのみインポート検出
- 成功条件: テンプレート選択だけで一貫した品質の動画が生成可能
- 残: BGMテンプレート自動配置、テンプレートバリアント実運用

---

## 3. フェーズ依存関係

```
Phase 0 (ベースライン)
   ↓
Phase 1 (タイミング安定化) ← Phase 2と並行可能
   ↓
Phase 2 (Ken Burns)
   ↓
Phase 3 (トランジション + 字幕)
   ↓
Phase 4 (テンプレート + 品質チェック)
```

---

## 4. 設計判断

| 判断 | 内容 | 理由 |
|------|------|------|
| contain > cover | 画像フィットはcontain（黒帯許容）を採用 | coverだと重要部分がトリミングされるリスク |
| Ken Burns優先 | トランジションよりKen Burnsを先に実装 | 「動きがある」の最小実装 |
| CSV列拡張方式 | アニメーション指定はCSV 4列目 | 既存3列目方式の自然な拡張 |
| Direct API移行 | Animation.From/To (CS0618旧形式) を使用 | リフレクション版はOpacity破壊・効果未確認の問題あり |
| Values in-place方式 | Animation.Values[0].Value直接変更 + ImmutableList.Add | From/Toもレンダリング破壊。Values in-placeが唯一の安定手法 |

---

## 5. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-14 | 初版作成。Phase 0-4定義 |
| 2026-03-14 | Phase 1-4 実装完了。Ken Burns 5%ズーム適用、WAV実尺同期、字幕スタイル(画面下部配置+フォントサイズ48)、画像フェードイン(opacity 0→100)、品質チェック(ファイル存在/ギャップ/オーバーラップ/総尺検証) |
| 2026-03-16 | Phase 0 テスト準備: E2Eテスト用CSV作成、検証ガイド更新(SP-033 Direct API対応)、設計判断にDirect API移行を反映 |
| 2026-03-17 | **Phase 0完了**: SP-027 Baseline E2E全PASS。CSV→YMM4→mp4完走、7種アニメ+Voice+レンダリング正常動作確認 |
| 2026-03-17 | **Phase 4実装**: SP-031 style_template.json v1.1 (video/crossfadeセクション追加)、ValidateImportItems拡張 |
