# YMM4 連携アーキテクチャ（現行サマリ）

最終更新: 2026-03-09

> この文書は **現行運用（Path A 単一）** の要点のみを記載します。
> 旧Path B（MoviePy + Pythonレンダリング）と `run_csv_pipeline.py` は 2026-03-08 に削除済みです。
> 実装・方針の一次情報は `docs/PROJECT_ALIGNMENT_SSOT.md` を参照してください。

---

## 1. 現行アーキテクチャ

現行は以下の一本化構成です。

1. Python側で前工程（調査、台本整形、CSV準備）
2. Web UI（CSV Pipeline）で YMM4 向け出力一式を生成（この段階では最終動画は未出力）
3. YMM4 + NLMSlidePlugin で CSV取り込み、YMM内で音声合成し、最終レンダリング（mp4）

補助スクリプト（例: `scripts/inspect_csv_timeline.py`）は入力検証・可視化用途であり、最終動画レンダリングは行いません。

---

## 2. Path A/B の差分（音声まわり）

| 項目 | 現行 Path A | 旧 Path B（削除済み） |
|---|---|---|
| 音声生成主体 | YMM4 内（ゆっくりボイスで音声合成） | 外部音源（WAV）を事前に手動準備 |
| レンダリング主体 | YMM4 | Python（MoviePy） |
| Pythonの役割 | 前工程 + YMM4投入データ準備 | 音声/動画合成まで担当 |
| 主な入口 | Web UI `CSV Pipeline` | `run_csv_pipeline.py`（削除済み） |
| 現在の扱い | 採用 | 廃止 |

重要: `run_csv_timeline` / `run_csv_pipeline.py` を前提にした運用は現行仕様ではありません。

---

## 3. 実行導線（現行）

```powershell
streamlit run src/web/web_app.py
# ブラウザで「CSV Pipeline」を選択
# CSV と必要素材を入力して実行
```

関連仕様:
- `docs/PROJECT_ALIGNMENT_SSOT.md`
- `docs/ymm4_export_spec.md`
- `docs/ymm4_final_workflow.md`
- `docs/spec_csv_input_format.md`

---

## 4. レガシー参照の扱い

以下は履歴・検証のために残る場合がありますが、現行運用には使用しません。

- `run_csv_pipeline.py`
- `csv_pipeline_runner`
- Path B（MoviePy backend）前提の記述

レガシー資料は `docs/archive/` に集約し、現行参照先は SSOT と仕様文書に統一します。