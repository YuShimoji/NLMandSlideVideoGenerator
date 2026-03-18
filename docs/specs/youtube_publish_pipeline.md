# YouTube公開パイプライン仕様 (SP-038)

**最終更新**: 2026-03-18
**ステータス**: partial (Phase 1-3 実装完了, 本番OAuth未テスト)

---

## 1. 目的

MetadataGenerator と YouTubeUploader をメインパイプラインに統合し、MP4完成後のYouTube公開を半自動化する。

### 1.1 現状 (As-Is → Was)

| モジュール | 状態 | 課題 |
|-----------|------|------|
| `src/youtube/metadata_generator.py` | 実装済み (機能完備) | ~~パイプライン未統合~~ → Phase 1 で統合済み |
| `src/youtube/uploader.py` | 実API実装済み (モックフォールバック付き) | ~~YouTube Data API v3の実API呼び出しなし~~ → Phase 3 で実装済み |
| ストック画像クレジット | StockImageClientで取得済み | ~~説明欄への自動挿入なし~~ → Phase 2 で統合済み |

### 1.2 目標 (To-Be)

```text
[既存] CSV生成完了
    ↓
[実装済] MetadataGenerator: ScriptBundle → タイトル/概要/タグ/チャプター自動生成
    ↓
[実装済] クレジット自動挿入: Pexels/Pixabayクレジットを概要欄に追記
    ↓
[手動] YMM4 → MP4レンダリング
    ↓
[実装済] YouTubeUploader: MP4 + メタデータ → YouTube公開 (private/unlisted/public)
    ↓
[実装済] CLI: research_cli.py upload --video ... --metadata ...
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

### Phase 3: YouTubeUploader 本番API実装 ✅

| 項目 | 内容 |
|------|------|
| 対象 | `src/youtube/uploader.py` |
| 変更 | モック→YouTube Data API v3 実装 (resumable upload) |
| 認証 | OAuth 2.0 (`GoogleAuthHelper` 経由、認証情報なしでモックフォールバック) |
| CLI | `research_cli.py upload --video path/to/mp4 --metadata output_csv/metadata.json` |
| デフォルト | `--privacy private` (安全側) |

#### 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/youtube/uploader.py` | 全面書き換え: 実API + モックフォールバック二重構成 |
| `config/settings.py` | `GOOGLE_SCOPES` に `youtube.upload` + `youtube.readonly` 追加 |
| `scripts/research_cli.py` | `upload` サブコマンド + `run_upload()` 追加 |

#### アーキテクチャ

```
YouTubeUploader.authenticate()
  ├── GoogleAuthHelper.get_credentials()
  │     ├── token.json 読み込み → 有効な Credentials → 実APIモード
  │     └── token なし / 失敗 → None → モックモード
  ├── 実APIモード: googleapiclient.discovery.build("youtube", "v3")
  └── モックモード: _mock_upload() (sleep + 仮ID生成)

YouTubeUploader.upload_video()
  ├── _normalize_video_path() + _normalize_metadata()
  ├── _validate_metadata() (タイトル100文字, 説明5000文字, タグ500文字, privacy)
  ├── 実APIモード: _api_upload() — MediaFileUpload resumable, 50MB chunks
  └── モックモード: _mock_upload()
```

#### CLI 使用方法

```bash
# 基本使用
python scripts/research_cli.py upload \
  --video output_mp4/video.mp4 \
  --metadata output_csv/metadata.json

# オプション指定
python scripts/research_cli.py upload \
  --video output_mp4/video.mp4 \
  --metadata output_csv/metadata.json \
  --privacy unlisted \
  --thumbnail output_csv/thumbnail.jpg \
  --credentials path/to/client_secrets.json
```

**備考**: 本番OAuthトークンの取得には `python scripts/google_auth_setup.py` を事前実行する必要がある。YouTube スコープが追加されたため、既存トークンの再取得が必要。

---

## 3. 設計判断

| 判断 | 内容 | 理由 |
|------|------|------|
| Phase分離 | メタデータ生成を先行、アップロードは後 | メタデータ生成だけでも手動アップロード時に有用 |
| private デフォルト | 初回アップロードは非公開 | 誤公開防止 |
| クレジット自動化 | Pexels/Pixabayは帰属不要だが推奨 | グッドプラクティスとして |
| bundle変換アダプタ | TranscriptInfo再利用 | MetadataGeneratorの既存ロジック (チャプター生成等) を活かすため |
| パイプライン統合 | generate_metadata フラグ | upload=False でもメタデータ生成可能にするため |
| モックフォールバック | 認証情報なしでもCLI/テストが動作 | OAuth未整備環境でもCI/ローカル開発に支障なし |
| resumable upload | 50MB チャンクで分割アップロード | 大容量MP4 (長尺動画20-30分+) のネットワーク耐障害性 |
| progress_callback | アップロード進捗のコールバック対応 | CLI/GUIの両方から進捗表示可能 |

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
| `tests/test_sp038_youtube_publish.py` | 41 | Phase 1-3 全体 (変換アダプタ、メタデータ生成、クレジット挿入、抽出、アップロード、バリデーション、バッチ、CLI ヘルパー) |
| `tests/test_metadata_generator.py` | 64 | MetadataGenerator 既存テスト |

---

## 6. 残作業

- [ ] 本番 OAuth トークン取得・接続テスト (google_auth_setup.py で YouTube スコープ再取得)
- [ ] 実 YouTube チャンネルへのテストアップロード (private)
- [ ] SP-039 との統合 (MP4品質検証 → アップロード連携)
