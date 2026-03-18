# パイプライン品質トラッキング (SP-042)

**最終更新**: 2026-03-18
**ステータス**: draft

---

## 1. 目的

パイプライン実行結果の統計を自動収集し、制作品質の改善サイクルを回す基盤を構築する。
「作って終わり」から「作って学ぶ」への転換。

### 1.1 現状 (As-Is)

- パイプライン実行後のログ出力のみ (console print)
- batch_result.json に success/failed の結果のみ記録
- 画像ヒット率、alignment 成功率、所要時間の追跡なし
- 品質改善の定量的根拠がない

### 1.2 目標 (To-Be)

- 各パイプライン実行の統計を pipeline_stats.json に自動記録
- バッチ実行時は batch_result.json に統計を統合
- CLI で過去の統計を閲覧・比較可能
- 品質4軸 (制作スピード / 情報密度 / 視覚完成度 / 一貫性) の定量指標

---

## 2. 収集指標

### 2.1 制作スピード

| 指標 | 単位 | 取得元 |
|------|------|--------|
| total_duration | 秒 | パイプライン全体の実行時間 |
| step_durations | dict[step, 秒] | 各ステップ (collect/script/align/review/orchestrate/assemble) の個別時間 |
| bottleneck_step | str | 最も時間がかかったステップ |

### 2.2 情報密度

| 指標 | 単位 | 取得元 |
|------|------|--------|
| source_count | int | SourceCollector が取得したソース数 |
| alignment_supported | int | AlignmentReport の supported 数 |
| alignment_orphaned | int | AlignmentReport の orphaned 数 |
| alignment_conflict | int | AlignmentReport の conflict 数 |
| alignment_rate | float | supported / total |
| segment_count | int | 生成されたセグメント数 |

### 2.3 視覚完成度

| 指標 | 単位 | 取得元 |
|------|------|--------|
| stock_image_count | int | ストック画像取得成功数 |
| ai_image_count | int | AI画像生成成功数 |
| text_slide_count | int | TextSlide フォールバック数 |
| image_hit_rate | float | (stock + ai) / total_visual_segments |
| visual_ratio | float | 画像付きセグメント / 全セグメント |

### 2.4 一貫性

| 指標 | 単位 | 取得元 |
|------|------|--------|
| pre_export_errors | int | ExportValidator のエラー数 |
| pre_export_warnings | int | ExportValidator の警告数 |
| speaker_mapping_applied | bool | speaker_mapping が適用されたか |
| style_preset | str | 使用した台本スタイル |

---

## 3. データ構造

### 3.1 pipeline_stats.json

各パイプライン実行の work_dir に保存。

```json
{
  "pipeline_id": "rp_20260318_123456",
  "topic": "量子コンピュータの最新動向",
  "style": "news",
  "target_duration": 1800,
  "timestamp": "2026-03-18T12:34:56",
  "speed": {
    "total_duration": 338.5,
    "step_durations": {
      "collect": 0.5,
      "script": 30.7,
      "align": 253.2,
      "review": 0.1,
      "orchestrate": 35.9,
      "assemble": 0.3
    },
    "bottleneck_step": "align"
  },
  "density": {
    "source_count": 5,
    "segment_count": 29,
    "alignment_supported": 24,
    "alignment_orphaned": 4,
    "alignment_conflict": 1,
    "alignment_rate": 0.83
  },
  "visual": {
    "stock_image_count": 11,
    "ai_image_count": 0,
    "text_slide_count": 18,
    "image_hit_rate": 0.38,
    "visual_ratio": 1.0
  },
  "consistency": {
    "pre_export_errors": 0,
    "pre_export_warnings": 0,
    "speaker_mapping_applied": true,
    "style_preset": "news"
  }
}
```

### 3.2 batch_result.json 統合

バッチ実行時、各トピックの stats を results 配列内に埋め込む。

---

## 4. 実装方針

### Phase 1: 統計収集基盤

- `src/core/pipeline_stats.py` — PipelineStats dataclass + 収集ロジック
- `run_pipeline()` の各ステップ前後でタイマー計測
- orchestrate 結果から visual 統計を抽出
- alignment レポートから density 統計を抽出
- work_dir に pipeline_stats.json を自動保存

### Phase 2: CLI 閲覧コマンド

- `research_cli.py` に `stats` サブコマンド追加
- `stats <work_dir>` — 単一実行の統計表示
- `stats --batch <batch_dir>` — バッチ全体のサマリー表示
- `stats --compare <dir1> <dir2>` — 2実行の比較

### Phase 3: batch_result.json 統合

- バッチ実行時に各トピックの stats を自動収集
- batch_result.json に `"stats"` フィールドを追加
- バッチ全体の集約統計 (平均/最大/最小) を計算

---

## 5. 影響範囲

- `src/core/pipeline_stats.py` — 新規
- `scripts/research_cli.py` — run_pipeline() 内にタイマー追加 + stats サブコマンド
- `tests/test_pipeline_stats.py` — 新規
- `config/settings.py` — 変更なし

---

## 6. 受け入れ条件

- [ ] pipeline 実行後に pipeline_stats.json が自動生成される
- [ ] stats CLI で統計を閲覧できる
- [ ] batch_result.json に各トピックの統計が含まれる
- [ ] 既存テスト全 PASS + 新規テスト追加
