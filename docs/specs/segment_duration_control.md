# SP-044: セグメント粒度制御

## 概要

target_duration指定時のセグメント数・推定尺を検証し、過不足がある場合に自動調整する仕組み。
再実行コストを削減し、「一晩3本」の安定制作を支える基盤能力。

## 背景

- target_duration=1800 (30分) 指定時、Geminiプロンプトにセグメント数ヒント (20-30) を含めているが、
  実際のセグメント数は台本品質次第で大幅に変動する
- セグメント不足 → スカスカの動画、過多 → 早口/圧縮が必要
- 現状は再実行するしかなく、API呼び出し回数を浪費する

## 仕様

### Phase 1: 検証 + 警告

台本生成後にセグメント数と推定尺を検証し、問題があれば警告を出す。

#### セグメント数の目安テーブル

| target_duration | 最小セグメント数 | 推奨セグメント数 | 最大セグメント数 |
|----------------|-----------------|-----------------|-----------------|
| ~300秒 (5分)   | 3               | 5-7             | 10              |
| ~900秒 (15分)  | 7               | 10-15           | 20              |
| ~1800秒 (30分) | 15              | 20-30           | 40              |
| ~3600秒 (60分) | 25              | 30-45           | 60              |

#### 推定尺の計算

各セグメントの推定読み上げ時間を算出:
- 日本語テキスト: 約4文字/秒 (ゆっくりボイス想定)
- 英語テキスト: 約2.5単語/秒

```python
def estimate_duration(segment: dict) -> float:
    text = segment.get("content", "")
    # 日本語文字数
    ja_chars = len([c for c in text if '\u3000' <= c <= '\u9fff' or '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff'])
    # 英語単語数
    en_words = len(text.split()) - ja_chars // 2  # 概算
    return ja_chars / 4.0 + max(en_words, 0) / 2.5
```

#### 検証ロジック

```python
class SegmentDurationValidator:
    def validate(self, segments, target_duration) -> ValidationResult:
        estimated_total = sum(estimate_duration(s) for s in segments)
        ratio = estimated_total / target_duration

        if ratio < 0.5:
            return ValidationResult(status="too_short", ratio=ratio, suggestion="add_segments")
        elif ratio > 1.5:
            return ValidationResult(status="too_long", ratio=ratio, suggestion="trim_segments")
        elif len(segments) < min_segments:
            return ValidationResult(status="too_few", count=len(segments), suggestion="add_segments")
        elif len(segments) > max_segments:
            return ValidationResult(status="too_many", count=len(segments), suggestion="merge_segments")
        else:
            return ValidationResult(status="ok", ratio=ratio)
```

#### パイプライン統合

- research_cli.py の Step 2 (script generation) 直後に検証を実行
- 警告レベル: PipelineStatsに記録 + コンソール出力
- auto-mode: 警告のみ出力し続行
- manual-mode: 警告出力 + 続行/再生成の選択肢

### Phase 2: 自動調整 (将来)

検証結果に基づいてセグメントを自動的に追加/統合する。

- too_short: LLMに追加セグメント生成を依頼
- too_long: 類似セグメントを統合
- too_few: セグメント分割を依頼
- too_many: 短いセグメントを統合

## テスト方針

- 推定尺計算の単体テスト
- 検証ロジックの境界値テスト
- パイプライン統合テスト (モックLLM)

## 実装ファイル

- `src/core/segment_duration_validator.py` (新規)
- `scripts/research_cli.py` (統合)
- `tests/test_segment_duration_validator.py` (新規)
