# Transcript I/O 仕様

最終更新: 2025-11-26
更新者: Cascade AI

---

## データ構造

### TranscriptSegment

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `id` | int | Yes | セグメントID（1-origin） |
| `start_time` | float | Yes | 秒単位の開始時刻 |
| `end_time` | float | Yes | 秒単位の終了時刻 |
| `speaker` | str | Yes | 話者名 |
| `text` | str | Yes | セグメント本文 |
| `key_points` | List[str] | Yes | キーポイント（0件可） |
| `slide_suggestion` | str | Yes | スライド提案文 |
| `confidence_score` | float | Yes | 0.0〜1.0 の信頼度 |

### TranscriptInfo

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `title` | str | Yes | 台本タイトル |
| `total_duration` | float | Yes | 全体時間（秒） |
| `segments` | List[TranscriptSegment] | Yes | セグメント一覧 |
| `accuracy_score` | float | Yes | 精度スコア（0.0〜1.0） |
| `created_at` | datetime | Yes | 生成日時 |
| `source_audio_path` | str | Yes | 元音声ファイルパス |

---

## JSON フォーマット例

```json
{
  "title": "AI技術の最新動向",
  "total_duration": 300.0,
  "accuracy_score": 0.95,
  "created_at": "2025-11-26T13:40:00",
  "source_audio_path": "data/audio/demo.mp3",
  "segments": [
    {
      "id": 1,
      "start_time": 0.0,
      "end_time": 12.5,
      "speaker": "ナレーター1",
      "text": "こんにちは。本日はAI技術の最新動向を解説します。",
      "key_points": ["AI", "最新動向"],
      "slide_suggestion": "【AI, 最新動向】こんにちは。本日は...",
      "confidence_score": 0.96
    }
  ]
}
```

---

## 形式変換と利用箇所

| モジュール | 役割 | 期待するフィールド |
|------------|------|--------------------|
| `notebook_lm.transcript_processor` | NotebookLM/CSV から TranscriptInfo を生成 | 上記すべて |
| `core.pipeline` | スライド生成・字幕生成 | `speaker`, `text`, `key_points`, 時間情報 |
| `slides.content_splitter` | スライド分割 | `key_points`, `text`, `start_time`, `end_time` |
| `video_editor.subtitle_generator` | 字幕生成 | `text`, `start_time`, `end_time` |
| `youtube.metadata_generator` | メタデータ生成 | `segments`, `key_points`, `speaker` |

---

## 今後の課題

- NotebookLM 公式 API 提供時のマッピング検討
- `confidence_score` と `accuracy_score` の定義を NotebookLM/Gemini と揃える
- CSV タイムライン読み込み時の `slide_suggestion` 自動生成ルール拡張
