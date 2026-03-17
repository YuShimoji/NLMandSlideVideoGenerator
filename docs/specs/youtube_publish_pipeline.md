# YouTube公開パイプライン仕様 (SP-038)

**最終更新**: 2026-03-17
**ステータス**: draft

---

## 1. 目的

MetadataGenerator と YouTubeUploader をメインパイプラインに統合し、MP4完成後のYouTube公開を半自動化する。

### 1.1 現状 (As-Is)

| モジュール | 状態 | 課題 |
|-----------|------|------|
| `src/youtube/metadata_generator.py` | 実装済み (機能完備) | パイプライン未統合。TranscriptInfo入力だがパイプラインはScriptBundle |
| `src/youtube/uploader.py` | 全てモック実装 | YouTube Data API v3の実API呼び出しなし |
| ストック画像クレジット | StockImageClientで取得済み | 説明欄への自動挿入なし |

### 1.2 目標 (To-Be)

```
[既存] CSV生成完了
    ↓
[新規] MetadataGenerator: ScriptBundle → タイトル/概要/タグ/チャプター自動生成
    ↓
[新規] クレジット自動挿入: Pexels/Pixabayクレジットを概要欄に追記
    ↓
[手動] YMM4 → MP4レンダリング
    ↓
[新規] YouTubeUploader: MP4 + メタデータ → YouTube公開 (private/unlisted/public)
```

---

## 2. 実装計画

### Phase 1: メタデータ自動生成の統合

| 項目 | 内容 |
|------|------|
| 対象 | MetadataGenerator + research_cli.py |
| 変更 | ScriptBundle → TranscriptInfo変換アダプタ追加。pipeline完了時にメタデータJSON出力 |
| 出力 | `output_csv/metadata.json` (title, description, tags, chapters) |
| CLI | `research_cli.py pipeline --topic "..." --generate-metadata` |

### Phase 2: クレジット自動挿入

| 項目 | 内容 |
|------|------|
| 対象 | MetadataGenerator.description |
| 変更 | VisualResourcePackageからcredit情報を収集し、概要欄末尾に追記 |
| 形式 | `\n\n【画像クレジット】\nPhoto by X on Pexels\n...` |

### Phase 3: YouTubeUploader本番API実装

| 項目 | 内容 |
|------|------|
| 対象 | `src/youtube/uploader.py` |
| 変更 | モック→YouTube Data API v3実装 |
| 認証 | OAuth 2.0 (既存 `src/gapi/google_auth.py` 活用) |
| CLI | `research_cli.py upload --video path/to/mp4 --metadata output_csv/metadata.json` |
| デフォルト | `--privacy private` (安全側) |

---

## 3. 設計判断

| 判断 | 内容 | 理由 |
|------|------|------|
| Phase分離 | メタデータ生成を先行、アップロードは後 | メタデータ生成だけでも手動アップロード時に有用 |
| private デフォルト | 初回アップロードは非公開 | 誤公開防止 |
| クレジット自動化 | Pexels/Pixabayは帰属不要だが推奨 | グッドプラクティスとして |

---

## 4. 品質軸との対応

| 品質軸 | SP-038の貢献 |
|--------|-------------|
| 制作スピード | 手動メタデータ入力・手動アップロードを排除 |
| 一貫性/再現性 | テンプレート駆動のメタデータで統一フォーマット |
