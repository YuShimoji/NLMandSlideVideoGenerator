# サムネイルパイプライン統合仕様 (SP-037)

**最終更新**: 2026-03-17
**ステータス**: draft

---

## 1. 目的

既存の `src/core/thumbnails/` をメインパイプラインに接続し、動画制作時にサムネイルを自動生成する。

### 1.1 現状 (As-Is)

- `src/core/thumbnails/template_generator.py` — テンプレートベースのサムネイル生成（実装済み）
- `src/core/thumbnails/ai_generator.py` — AI生成サムネイル（実装済み）
- どちらもパイプライン (`research_cli.py pipeline`) から呼び出されていない
- YouTube公開時にサムネイルを毎回手動作成する必要がある

### 1.2 目標 (To-Be)

```
research_cli.py pipeline --topic "..." --auto-images
    ↓ (既存フロー)
output_csv/timeline.csv + images/
    ↓ (新規)
output_csv/thumbnail.png  ← 自動生成
```

---

## 2. 実装計画

### Phase 1: パイプライン接続

| 項目 | 内容 |
|------|------|
| 対象 | `scripts/research_cli.py` の `run_pipeline()` |
| 変更 | CSV生成後にサムネイル生成ステップを追加 |
| 入力 | ScriptBundle (トピック + キーワード) |
| 出力 | `output_csv/thumbnail.png` (1280x720) |
| フォールバック | 生成失敗時はスキップ（サムネイルなしは致命的でない） |

### Phase 2: スタイル連携

| 項目 | 内容 |
|------|------|
| SP-036連携 | プリセットごとのサムネイルスタイル（色/レイアウト） |
| SP-031連携 | style_template.json に `thumbnail` セクション追加 |

---

## 3. 品質軸との対応

| 品質軸 | SP-037の貢献 |
|--------|-------------|
| 制作スピード | 手動サムネイル作成を排除 |
| 視覚的完成度 | テンプレートベースで一貫したデザイン |
| 一貫性/再現性 | 同一テンプレートなら同一品質 |
