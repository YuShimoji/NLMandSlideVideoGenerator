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

### Phase 2: 自動調整 (実装済み)

検証結果に基づいてセグメントを自動的に追加/統合する。

- too_short / too_few: `_expand_segments()` — LLM (ILLMProvider) に追加セグメント生成を依頼
  - 不足秒数から追加セグメント数を概算 (1セグメント≒15秒)
  - JSON形式のプロンプトで話者・内容・セクション・key_pointsを含む追加セグメントを生成
  - LLMプロバイダー取得失敗時は元のセグメントをそのまま返す (graceful degradation)
- too_long / too_many: `_merge_short_segments()` — 短いセグメントを隣接セグメントに統合
  - 推定尺が短い順にソート
  - expected_max を超過する分だけ統合
  - content と key_points を連結して保持

#### パイプライン統合 (Phase 2)

- research_cli.py の Step 2 直後に validate → adjust の2段階を実行
- 調整結果は script_bundle JSON に書き戻し
- PipelineStats に記録

### Phase 3: 手動モード (未着手)

- manual-mode: 警告出力 + 続行/再生成の選択肢
- CLI フラグ `--duration-mode manual|auto` (デフォルト auto)
- HUMAN_AUTHORITY: UX設計判断が必要

## テスト方針

- 推定尺計算の単体テスト (6件)
- セグメント数レンジの境界値テスト (6件)
- 検証ロジックの境界値テスト (9件)
- 統合ロジック (_merge_short_segments) テスト (3件)
- 自動調整 (adjust_segments) テスト (2件+)
- LLMプロバイダー失敗時の graceful degradation テスト

## 実装ファイル

- `src/core/segment_duration_validator.py`
- `scripts/research_cli.py` (統合)
- `tests/test_segment_duration_validator.py` (25+ テスト)
