# YouTube公開パイプライン仕様 (SP-038)

**最終更新**: 2026-03-18
**ステータス**: partial (Phase 1-2 完了, Phase 3 未着手)

---

## 1. 目的

MetadataGenerator と YouTubeUploader をメインパイプラインに統合し、MP4完成後のYouTube公開を半自動化する。

### 1.1 現状 (As-Is → Was)

| モジュール | 状態 | 課題 |
|-----------|------|------|
| `src/youtube/metadata_generator.py` | 実装済み (機能完備) | ~~パイプライン未統合~~ → Phase 1 で統合済み |
| `src/youtube/uploader.py` | 全てモック実装 | YouTube Data API v3の実API呼び出しなし (Phase 3) |
| ストック画像クレジット | StockImageClientで取得済み | ~~説明欄への自動挿入なし~~ → Phase 2 で統合済み |

### 1.2 目標 (To-Be)

```
[既存] CSV生成完了
    ↓
[実装済] MetadataGenerator: ScriptBundle → タイトル/概要/タグ/チャプター自動生成
    ↓
[実装済] クレジット自動挿入: Pexels/Pixabayクレジットを概要欄に追記
    ↓
[手動] YMM4 → MP4レンダリング
    ↓
[未実装] YouTubeUploader: MP4 + メタデータ → YouTube公開 (private/unlisted/public)
```

---

## 2. 実装計画

### Phase 1: メタデータ自動生成の統合 ✅

| 項目 | 内容 |
|------|------|
| 対象 | MetadataGenerator + ModularVideoPipeline |
| 変更 | ScriptBundle → TranscriptInfo変換アダプタ追加。pipeline完了時にメタデータJSON出力 |
| 出力 | `output_csv/metadata.json` (title, description, tags, chapters) |
| パイプライン | `ModularVideoPipeline.run(generate_metadata=True)` |

#### 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/youtube/script_to_transcript.py` | **新規**: ScriptBundle → TranscriptInfo 変換アダプタ |
| `src/youtube/metadata_generator.py` | `generate_metadata_from_bundle()` 追加 |
| `src/youtube/__init__.py` | `script_bundle_to_transcript` エクスポート追加 |
| `src/core/pipeline.py` | `generate_metadata` パラメータ + `_generate_and_save_metadata()` |

### Phase 2: クレジット自動挿入 ✅

| 項目 | 内容 |
|------|------|
| 対象 | MetadataGenerator.description + pipeline |
| 変更 | editing_outputsからcredit情報を収集し、概要欄末尾に追記 |
| 形式 | `\n\n【画像クレジット】\nPhoto by X on Pexels\n...` |

#### 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/youtube/metadata_generator.py` | `append_credits()` 静的メソッド追加 |
| `src/core/pipeline.py` | `_extract_credits()` — editing_outputsからクレジット抽出 |

### Phase 3: YouTubeUploader本番API実装 ⬜ (HUMAN_AUTHORITY)

| 項目 | 内容 |
|------|------|
| 対象 | `src/youtube/uploader.py` |
| 変更 | モック→YouTube Data API v3実装 |
| 認証 | OAuth 2.0 (既存 `src/gapi/google_auth.py` 活用) |
| CLI | `research_cli.py upload --video path/to/mp4 --metadata output_csv/metadata.json` |
| デフォルト | `--privacy private` (安全側) |

**備考**: Phase 3 は本番OAuth認証・外部API実装を含むため HUMAN_AUTHORITY 判断が必要。

---

## 3. 設計判断

| 判断 | 内容 | 理由 |
|------|------|------|
| Phase分離 | メタデータ生成を先行、アップロードは後 | メタデータ生成だけでも手動アップロード時に有用 |
| private デフォルト | 初回アップロードは非公開 | 誤公開防止 |
| クレジット自動化 | Pexels/Pixabayは帰属不要だが推奨 | グッドプラクティスとして |
| bundle変換アダプタ | TranscriptInfo再利用 | MetadataGeneratorの既存ロジック (チャプター生成等) を活かすため |
| パイプライン統合 | generate_metadata フラグ | upload=False でもメタデータ生成可能にするため |

---

## 4. 品質軸との対応

| 品質軸 | SP-038の貢献 |
|--------|-------------|
| 制作スピード | 手動メタデータ入力・手動アップロードを排除 |
| 一貫性/再現性 | テンプレート駆動のメタデータで統一フォーマット |

---

## 5. テスト

| テストファイル | 件数 | 対象 |
|---------------|------|------|
| `tests/test_sp038_youtube_publish.py` | 19 | 変換アダプタ、メタデータ生成、クレジット挿入、クレジット抽出 |
| `tests/test_metadata_generator.py` | 47 | MetadataGenerator 既存テスト |
