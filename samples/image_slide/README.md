# image_slide サンプル

CSV 3列目に画像パスを指定するスライド動画サンプル。
同梱の `slides/` ディレクトリに1920x1080のテスト用スライド画像3枚を含む。

## ファイル構成

- `timeline.csv` — 8行、れいむ/まりさの対話、3枚のスライドに均等配分
- `timeline_animated.csv` — 同内容+4列目アニメーション種別指定 (SP-033)
- `test_with_images.csv` — 6行の短縮版
- `slides/slide_0001.png` 〜 `slide_0003.png` — テスト用スライド画像

## CSVフォーマット

```
話者名,テキスト,画像パス（省略可）,アニメーション種別（省略可、SP-033）
```

4列目のアニメーション種別: `ken_burns`(デフォルト), `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `static`

## 使い方

1. CSVの画像パスを絶対パスに変換（YMM4は相対パスを解決できない場合がある）
2. YMM4起動 → NLMSlidePlugin → CSVインポート
3. ImageItem + TextItem + AudioItem がタイムラインに配置される

詳細は `samples/README.md` のStep 1〜6を参照。
