# MP4出力品質自動検証仕様 (SP-039)

**最終更新**: 2026-03-18
**ステータス**: done (Phase 1-2 完了)

---

## 1. 目的

YMM4レンダリング後のMP4ファイルをFFprobeで自動検証し、出力品質を構造的に担保する。

### 1.1 現状 (As-Is → Was)

- ~~MP4の品質確認は手動目視のみ~~ → Phase 1 で FFprobe 自動検証を実装
- ~~エンコード破損、音声欠落、解像度不一致などを事前検出する仕組みがない~~ → 10項目自動チェック
- ~~SP-038との連携なし~~ → Phase 2 で YouTube アップロード前の自動品質ゲート実装
- SP-031 (Pre-Export Validation) はCSV段階の検証のみで、最終MP4の検証は対象外

### 1.2 目標 (To-Be)

```text
[YMM4] レンダリング → output.mp4
    ↓
[Python] MP4QualityChecker: FFprobeで自動検証
    ↓
PASS → アップロード可能
FAIL (CRITICAL) → アップロード阻止 + 問題箇所レポート
```

---

## 2. 検証項目

| カテゴリ | チェック項目 | 期待値 | 重要度 |
|---------|------------|--------|--------|
| コーデック | 映像コーデック | H.264 or H.265 | CRITICAL |
| コーデック | 音声コーデック | AAC | CRITICAL |
| 解像度 | 映像サイズ | 1920x1080 | CRITICAL |
| 解像度 | アスペクト比 | 16:9 | CRITICAL |
| 尺 | 総再生時間 | CSVセグメント総尺と一致 (+-10%) | HIGH |
| 音声 | 音声ストリーム存在 | 1本以上 | CRITICAL |
| 音声 | サンプルレート | 44100 or 48000 Hz | MEDIUM |
| ファイル | ファイルサイズ | > 1MB (空ファイル検出) | CRITICAL |
| ファイル | ファイルサイズ | < 256GB (YouTube制限) | LOW |
| フレーム | FPS | 60 or 30 | MEDIUM |

---

## 3. 実装計画

### Phase 1: FFprobeチェッカー ✅

| 項目 | 内容 |
|------|------|
| 新規ファイル | `src/core/utils/mp4_checker.py` |
| 依存 | FFprobe (FFmpegに同梱) |
| 出力 | `MP4CheckResult` (pass/fail, 各項目の結果, 警告) |
| CLI | `research_cli.py verify mp4_path [--expected-duration] [--resolution]` |

#### 実装ファイル

| ファイル | 内容 |
|---------|------|
| `src/core/utils/mp4_checker.py` | CheckItem, MP4CheckResult, check_mp4() |
| `scripts/research_cli.py` | verify サブコマンド (単一ファイル/ディレクトリ再帰) |

### Phase 2: SP-038 パイプライン統合 ✅

| 項目 | 内容 |
|------|------|
| SP-038連携 | YouTube公開前に自動チェック。CRITICAL失敗時はアップロード阻止 |
| パラメータ | `upload_video(verify_quality=True)` (デフォルトON) |
| CLI | `research_cli.py upload --no-verify` でスキップ可能 |
| FFprobe不在 | 検証スキップ (アップロードは続行) |

#### 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/youtube/uploader.py` | `_verify_mp4_quality()` + `verify_quality` パラメータ |
| `scripts/research_cli.py` | `--no-verify` オプション |

#### アーキテクチャ

```text
upload_video(verify_quality=True)
  ├── _verify_mp4_quality(video_path)
  │     ├── FFprobe あり: check_mp4() → MP4CheckResult
  │     │     ├── PASS → アップロード続行
  │     │     └── FAIL (CRITICAL) → UploadError 送出、アップロード阻止
  │     └── FFprobe なし: None → 検証スキップ、アップロード続行
  └── _api_upload() or _mock_upload()
```

---

## 4. 品質軸との対応

| 品質軸 | SP-039の貢献 |
|--------|-------------|
| 一貫性/再現性 | 出力品質のゲートキーパー。不良品の公開を防止 |
| 視覚的完成度 | 解像度・コーデック不整合を検出 |

---

## 5. テスト

| テストファイル | 件数 | 対象 |
|---------------|------|------|
| `tests/test_mp4_checker.py` | 17 | Phase 1: FFprobeモック + 各検証項目 |
| `tests/test_sp038_youtube_publish.py` | 4 (内SP-039) | Phase 2: verify_quality統合 (スキップ/ブロック/パス/FFprobeなし) |
